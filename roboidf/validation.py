"""Offline interface and structural evidence checks. Never drives hardware."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

VERSION = 'interface.v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def source_check(source):
    if not isinstance(source, dict) or any(not isinstance(source.get(k), str) or not source[k].strip() for k in ('uri', 'license', 'provenance')):
        raise ValueError('source requires nonempty uri, license and provenance')


def report(**fields):
    return {'schema_version': VERSION, 'hardware_status': 'pending', 'twin_status': 'pending',
            'execution_authorized': False, **fields}


def example_contract():
    return {'schema_version': VERSION, 'id': 'synthetic-slider', 'mode': 'offline',
            'authorization': 'offline-only', 'clock': {'unit': 's', 'domain': 'monotonic'},
            'source': {'uri': 'synthetic://roboidf/slider', 'license': 'synthetic-test-fixture', 'provenance': 'generated fixture; no device data'},
            'joints': [{'name': 'slider', 'type': 'prismatic', 'position_unit': 'm', 'velocity_unit': 'm/s', 'effort_unit': 'N'}],
            'adapter': {'schema_version': VERSION, 'kind': 'offline-csv', 'dataset_version': 'm0.v1'}}


def validate_contract(contract):
    if not isinstance(contract, dict) or contract.get('schema_version') != VERSION:
        raise ValueError('unsupported interface schema_version')
    if not isinstance(contract.get('id'), str) or not contract['id'].strip():
        raise ValueError('nonempty id required')
    source_check(contract.get('source'))
    mode = contract.get('mode')
    if mode not in ('offline', 'hardware') or contract.get('authorization') != ('offline-only' if mode == 'offline' else 'pending'):
        raise ValueError('authorization must be offline-only or hardware pending')
    clock = contract.get('clock')
    if not isinstance(clock, dict) or clock.get('unit') != 's' or clock.get('domain') != 'monotonic':
        raise ValueError('clock requires seconds and monotonic domain')
    joints = contract.get('joints')
    if not isinstance(joints, list) or not joints:
        raise ValueError('nonempty joints required')
    names = set()
    for joint in joints:
        if not isinstance(joint, dict):
            raise ValueError('joint must be an object')
        name = joint.get('name')
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('unique nonempty joint names required')
        names.add(name)
        expected = {'prismatic': ('m', 'm/s', 'N'), 'revolute': ('rad', 'rad/s', 'N*m')}.get(joint.get('type'))
        if expected is None or tuple(joint.get(k) for k in ('position_unit', 'velocity_unit', 'effort_unit')) != expected:
            raise ValueError('joint type and SI units must agree')
    adapter = contract.get('adapter')
    if not isinstance(adapter, dict) or adapter.get('schema_version') != VERSION or adapter.get('dataset_version') != 'm0.v1' or adapter.get('kind') not in ('offline-csv', 'hardware-pending'):
        raise ValueError('incompatible adapter metadata')
    if adapter['kind'] != ('offline-csv' if mode == 'offline' else 'hardware-pending'):
        raise ValueError('adapter kind must match offline or hardware-pending mode')
    return report(passed=True, scope='metadata-only', input_sha256=digest(contract))


def hardware_precheck(contract):
    # Even complete strings are unverified claims. No SDK import or hardware call exists.
    evidence = contract.get('hardware_evidence', {}) if isinstance(contract, dict) else {}
    missing = [k for k in ('sdk', 'calibration', 'approval', 'stop') if not isinstance(evidence, dict) or not isinstance(evidence.get(k), str) or not evidence[k].strip()]
    return report(passed=False, scope='hardware-precheck-only', missing_evidence=missing,
                  reason='HARDWARE_DISABLED: evidence is not verified; this tool never drives hardware', input_sha256=digest(contract))


def validate_asset(text, kind, source):
    source_check(source)
    if not isinstance(text, str) or not text.strip():
        raise ValueError('nonempty textual asset required')
    if kind == 'mjcf':
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValueError('DTD/entity declarations prohibited')
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError('invalid MJCF XML') from exc
        if root.tag != 'mujoco' or root.find('worldbody') is None:
            raise ValueError('MJCF requires mujoco root and worldbody')
        if root.findall('.//include'):
            raise ValueError('external includes require separate asset review')
    elif kind == 'usd':
        if text.splitlines()[0].strip() != '#usda 1.0':
            raise ValueError('only textual USDA 1.0 header is supported')
    else:
        raise ValueError('unsupported asset kind')
    return report(passed=True, scope='structure-only' if kind == 'mjcf' else 'header-only',
                  kind=kind, input_sha256=hashlib.sha256(text.encode()).hexdigest(), source_sha256=digest(source),
                  limitation='No engine load, dynamics, external asset or cross-engine validation')


def example_trajectory():
    return {'schema_version': VERSION, 'time_unit': 's', 'clock_domain': 'monotonic',
            'time': [0., .1, .2], 'joint_names': ['slider'], 'velocity_units': ['m/s'],
            'velocity': [[0.], [.1], [.2]], 'source': example_contract()['source']}


def _trajectory(value):
    if not isinstance(value, dict) or value.get('schema_version') != VERSION:
        raise ValueError('unsupported trajectory version')
    source_check(value.get('source'))
    if value.get('time_unit') != 's' or value.get('clock_domain') != 'monotonic':
        raise ValueError('trajectory requires monotonic seconds')
    names = value.get('joint_names'); units = value.get('velocity_units')
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n.strip() for n in names) or len(set(names)) != len(names):
        raise ValueError('unique joint names required')
    if not isinstance(units, list) or len(units) != len(names) or any(u not in ('m/s', 'rad/s') for u in units):
        raise ValueError('SI velocity units required')
    times = value.get('time'); rows = value.get('velocity')
    finite = lambda x: type(x) in (int, float) and math.isfinite(x)
    if not isinstance(times, list) or len(times) < 2 or not all(finite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('finite strictly increasing timestamps required')
    if not isinstance(rows, list) or len(rows) != len(times) or any(not isinstance(row, list) or len(row) != len(names) or not all(finite(v) for v in row) for row in rows):
        raise ValueError('finite velocity matrix matching time and joints required')


def compare_replay(reference, replay, *, rmse_limit):
    _trajectory(reference); _trajectory(replay)
    if type(rmse_limit) not in (int, float) or not math.isfinite(rmse_limit) or rmse_limit < 0:
        raise ValueError('finite nonnegative RMSE limit required')
    for key in ('time', 'time_unit', 'clock_domain', 'joint_names', 'velocity_units'):
        if reference[key] != replay[key]:
            raise ValueError('trajectory mismatch: ' + key + '; resampling/conversion must be explicit upstream')
    metrics = []
    for j, name in enumerate(reference['joint_names']):
        errors = [b[j] - a[j] for a, b in zip(reference['velocity'], replay['velocity'])]
        rmse = math.hypot(*errors) / math.sqrt(len(errors))
        if not math.isfinite(rmse):
            raise ValueError('nonfinite replay metric')
        metrics.append({'joint': name, 'unit': reference['velocity_units'][j], 'rmse': rmse, 'max_abs_error': max(map(abs, errors)), 'passed': rmse <= rmse_limit})
    return report(passed=all(m['passed'] for m in metrics), scope='offline-replay-comparison',
                  reference_sha256=digest(reference), replay_sha256=digest(replay),
                  config={'rmse_limit_per_joint_in_declared_unit': rmse_limit, 'alignment': 'exact'}, metrics=metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hardware', action='store_true', help='demonstrate unconditional hardware refusal')
    parser.add_argument('--contract', type=Path, help='validate JSON contract')
    parser.add_argument('--output', type=Path, default=Path('artifacts/validation.json'))
    args = parser.parse_args()
    try:
        contract = json.loads(args.contract.read_text()) if args.contract else example_contract()
        if args.hardware or contract.get('mode') == 'hardware':
            result = hardware_precheck(contract)
        else:
            result = validate_contract(contract)
            if not args.contract:
                result['replay_example'] = compare_replay(example_trajectory(), example_trajectory(), rmse_limit=1e-8)
                result['fixture'] = 'deterministic synthetic three-sample velocity; no randomness'
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        result = report(passed=False, reason=str(exc))
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    except OSError as exc:
        result = report(passed=False, reason='cannot save report: ' + str(exc))
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
