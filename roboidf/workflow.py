"""Versioned, resumable offline pipeline; not an agent or hardware executor."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from .core import Dataset, MockRobot, Parameters, fit, rollout_rmse


class WorkflowError(ValueError):
    """Rejected request, state, or concurrent invocation."""


@dataclass(frozen=True)
class WorkflowConfig:
    seed: int = 42
    samples: int = 500
    dt: float = .02
    max_calls: int = 6
    offline_approved: bool = True
    validation_tolerance: float = 1e-8

    def __post_init__(self):
        for name in ('seed', 'samples', 'max_calls'):
            if type(getattr(self, name)) is not int:
                raise ValueError(f'{name} must be an integer')
        if not 3 <= self.samples <= 100000 or not 0 <= self.max_calls <= 1000:
            raise ValueError('samples or call budget out of range')
        if type(self.offline_approved) is not bool:
            raise ValueError('offline approval must be boolean')
        for name in ('dt', 'validation_tolerance'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{name} must be finite')
        if not 0 < self.dt < 10 or self.validation_tolerance < 0:
            raise ValueError('invalid integration step or tolerance')


TOOLS = ('collect', 'fit', 'validate')
TERMINAL = ('succeeded', 'failed', 'terminated', 'budget_exhausted', 'approval_required')


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    arguments: dict

    def __post_init__(self):
        if self.tool not in TOOLS:
            raise WorkflowError('OFFLINE_ONLY: unknown or hardware tool')
        if type(self.arguments) is not dict:
            raise WorkflowError('REQUEST: arguments must be an object')


def _canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def _hash(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _dataset(value):
    return Dataset(**value)


class ToolRegistry:
    """Explicit built-in allowlist. Never imports or evaluates stored tool names."""
    def __init__(self):
        self._tools = {}
        for name in TOOLS:
            self.register(name)

    def register(self, name):
        if name not in TOOLS or name in self._tools:
            raise WorkflowError('REGISTRY: unknown or duplicate tool')
        self._tools[name] = {'collect': self._collect, 'fit': self._fit,
                             'validate': self._validate}[name]

    def execute(self, request: ToolRequest):
        if type(request) is not ToolRequest:
            raise WorkflowError('REQUEST: ToolRequest required')
        try:
            return self._tools[request.tool](**request.arguments)
        except (TypeError, KeyError) as exc:
            raise WorkflowError('REQUEST: invalid tool arguments') from exc

    @staticmethod
    def _collect(config):
        config = WorkflowConfig(**config)
        if not config.offline_approved:
            raise WorkflowError('OFFLINE_APPROVAL_REQUIRED')
        robot = MockRobot()
        train = robot.collect(seed=config.seed, split='train', samples=config.samples, dt=config.dt)
        validation = robot.collect(seed=config.seed + 1, split='validation', samples=config.samples, dt=config.dt)
        return {'train': asdict(train), 'validation': asdict(validation),
                'train_sha256': train.digest(), 'validation_sha256': validation.digest()}

    @staticmethod
    def _fit(train):
        return asdict(fit(_dataset(train)))

    @staticmethod
    def _validate(model, validation, tolerance):
        if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
            raise WorkflowError('REQUEST: tolerance must be finite and nonnegative')
        if (type(model) is not dict or set(model) != {'mass', 'damping'}
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in model.values())):
            raise WorkflowError('REQUEST: invalid model fields')
        if (type(validation) is not dict
                or set(validation) != {'dt', 'velocity', 'effort', 'split', 'seed'}
                or type(validation['seed']) is not int
                or type(validation['dt']) not in (int, float)
                or any(type(validation[k]) not in (list, tuple) for k in ('velocity', 'effort'))
                or any(type(v) not in (int, float) for k in ('velocity', 'effort') for v in validation[k])):
            raise WorkflowError('REQUEST: invalid validation dataset fields')
        data = _dataset(validation)
        if data.split != 'validation':
            raise WorkflowError('VALIDATION: validation split required')
        error = rollout_rmse(Parameters(**model), data)
        if error > tolerance:
            raise WorkflowError('VALIDATION_FAILED: rollout exceeds tolerance')
        return {'rmse': error, 'validation_sha256': data.digest()}


@contextmanager
def directory_lock(output):
    """Linux advisory process lock, released automatically even after process death."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.workflow.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowError('LOCKED: output directory in use') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _save(path, state):
    state['state_sha256'] = _hash({k: v for k, v in state.items() if k != 'state_sha256'})
    contents = _canonical(state)
    fd, temporary = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(contents + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _load(path, config):
    try:
        if path.stat().st_size > 32_000_000:
            raise ValueError('oversized state')
        state = json.loads(path.read_text(), object_pairs_hook=_unique_object, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        expected = {'schema_version', 'config', 'config_sha256', 'hardware_status',
                    'status', 'attempts', 'steps', 'state_sha256'}
        if type(state) is not dict or set(state) != expected:
            raise ValueError('invalid fields')
        if state['state_sha256'] != _hash({k: v for k, v in state.items() if k != 'state_sha256'}):
            raise ValueError('checksum mismatch')
        saved_config = WorkflowConfig(**state['config'])
        if state['config_sha256'] != _hash(asdict(saved_config)):
            raise ValueError('config hash mismatch')
        if asdict(saved_config) != asdict(config):
            raise WorkflowError('CONFIG_MISMATCH: use a new output directory')
        if state['schema_version'] != 'workflow.v1' or state['hardware_status'] != 'pending':
            raise ValueError('unsupported contract')
        if state['status'] not in (*TERMINAL, 'running', 'interrupted'):
            raise ValueError('invalid status')
        steps = state['steps']
        if type(steps) is not list or len(steps) > 3:
            raise ValueError('invalid steps')
        if type(state['attempts']) is not int or not len(steps) <= state['attempts'] <= config.max_calls:
            raise ValueError('invalid budget')
        for i, step in enumerate(steps):
            if set(step) != {'tool', 'status', 'result', 'error', 'input_sha256'} or step['tool'] != TOOLS[i]:
                raise ValueError('invalid step sequence')
            if step['status'] not in ('running', 'completed', 'failed'):
                raise ValueError('invalid step status')
            if i < len(steps) - 1 and step['status'] != 'completed':
                raise ValueError('unfinished dependency')
            request = _request(i, config, steps)
            if step['input_sha256'] != _hash(asdict(request)):
                raise ValueError('input mismatch')
            if step['status'] != 'completed':
                if step['result'] is not None or (step['status'] == 'failed' and type(step['error']) is not str):
                    raise ValueError('invalid incomplete step')
                continue
            if step['error'] is not None:
                raise ValueError('completed step has error')
            result = step['result']
            if i == 0:
                if set(result) != {'train', 'validation', 'train_sha256', 'validation_sha256'}:
                    raise ValueError('invalid collection result')
                for split, seed in (('train', config.seed), ('validation', config.seed + 1)):
                    data = _dataset(result[split])
                    if (data.split != split or data.seed != seed or data.dt != config.dt
                            or len(data.effort) != config.samples or data.digest() != result[split + '_sha256']):
                        raise ValueError('dataset mismatch')
            elif i == 1:
                Parameters(**result)
            else:
                if (set(result) != {'rmse', 'validation_sha256'} or type(result['rmse']) not in (int, float)
                        or not 0 <= result['rmse'] <= config.validation_tolerance
                        or result['validation_sha256'] != steps[0]['result']['validation_sha256']):
                    raise ValueError('invalid validation result')
        if state['status'] == 'budget_exhausted' and state['attempts'] != config.max_calls:
            raise ValueError('budget not exhausted')
        if state['status'] == 'approval_required' and (config.offline_approved or steps or state['attempts']):
            raise ValueError('inconsistent approval state')
        if not config.offline_approved and (steps or state['attempts']):
            raise ValueError('unapproved execution')
        complete = len(steps) == 3 and all(s['status'] == 'completed' for s in steps)
        if (state['status'] == 'succeeded') != complete:
            raise ValueError('inconsistent success')
        if state['status'] == 'failed' and (not steps or steps[-1]['status'] != 'failed'):
            raise ValueError('missing failure')
        if any(s['status'] == 'failed' for s in steps) and state['status'] != 'failed':
            raise ValueError('hidden failure')
        return state
    except WorkflowError:
        raise
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as exc:
        raise WorkflowError(f'STATE_INVALID: {exc}') from exc


def _request(index, config, steps):
    if index == 0:
        return ToolRequest('collect', {'config': asdict(config)})
    if index == 1:
        return ToolRequest('fit', {'train': steps[0]['result']['train']})
    return ToolRequest('validate', {'model': steps[1]['result'],
                                   'validation': steps[0]['result']['validation'],
                                   'tolerance': config.validation_tolerance})


def run(output, config=None, *, stop_after=None, terminate=False):
    """Resume durable checkpoints. Budget counts attempts, including crash retries."""
    if type(terminate) is not bool:
        raise ValueError("terminate must be boolean")
    config = WorkflowConfig() if config is None else config
    if type(config) is not WorkflowConfig:
        raise ValueError('WorkflowConfig required')
    if stop_after is not None and (type(stop_after) is not int or stop_after < 1):
        raise ValueError('stop_after must be a positive integer')
    with directory_lock(output):
        path = Path(output) / 'state.json'
        state = _load(path, config) if path.exists() else {
            'schema_version': 'workflow.v1', 'config': asdict(config),
            'config_sha256': _hash(asdict(config)), 'hardware_status': 'pending',
            'status': 'running', 'attempts': 0, 'steps': []}
        if state['status'] in TERMINAL:
            return state
        if terminate or not config.offline_approved:
            state['status'] = 'terminated' if terminate else 'approval_required'
            _save(path, state)
            return state
        registry = ToolRegistry()
        calls = 0
        for index in range(3):
            if index < len(state['steps']) and state['steps'][index]['status'] == 'completed':
                continue
            if state['attempts'] >= config.max_calls:
                state['status'] = 'budget_exhausted'
                _save(path, state)
                return state
            request = _request(index, config, state['steps'])
            step = {'tool': request.tool, 'status': 'running', 'result': None,
                    'error': None, 'input_sha256': _hash(asdict(request))}
            state['steps'][index:] = [step]
            state['attempts'] += 1
            state['status'] = 'running'
            _save(path, state)
            try:
                # Normalize tuples to JSON arrays before returning or persisting.
                step['result'] = json.loads(_canonical(registry.execute(request)))
                step['status'] = 'completed'
            except Exception as exc:
                step['status'] = 'failed'
                step['error'] = f'{type(exc).__name__}: {exc}'[:2000]
                state['status'] = 'failed'
                _save(path, state)
                return state
            calls += 1
            state['status'] = 'succeeded' if index == 2 else 'running'
            if stop_after is not None and calls >= stop_after and index < 2:
                state['status'] = 'interrupted'
            _save(path, state)
            if state['status'] == 'interrupted':
                return state
        return state


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline resumable synthetic workflow')
    parser.add_argument('--output', default='artifacts/workflow')
    parser.add_argument('--stop-after', type=int)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-calls', type=int, default=6)
    parser.add_argument('--deny-offline', action='store_true')
    parser.add_argument('--terminate', action='store_true')
    args = parser.parse_args(argv)
    try:
        state = run(args.output, WorkflowConfig(seed=args.seed, max_calls=args.max_calls,
                    offline_approved=not args.deny_offline), stop_after=args.stop_after, terminate=args.terminate)
        print(_canonical({'status': state['status'], 'attempts': state['attempts'],
                          'hardware_status': state['hardware_status'], 'state': str(Path(args.output) / 'state.json')}))
        return {'succeeded': 0, 'interrupted': 3, 'approval_required': 4,
                'budget_exhausted': 5, 'terminated': 6, 'failed': 1}[state['status']]
    except (ValueError, OSError) as exc:
        print(_canonical({'status': 'rejected', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
