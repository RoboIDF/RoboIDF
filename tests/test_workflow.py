import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('roboidf.workflow'), 'workflow module required')
        from roboidf import workflow
        self.w = workflow
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def test_interrupt_resume_does_not_repeat_completed_steps(self):
        first = self.w.run(self.path, stop_after=1)
        self.assertEqual(first['status'], 'interrupted')
        self.assertEqual(first['attempts'], 1)
        final = self.w.run(self.path)
        self.assertEqual(final['status'], 'succeeded')
        self.assertEqual(final['attempts'], 3)
        self.assertEqual(final['steps'][0], first['steps'][0])
        self.assertEqual(self.w.run(self.path), final)
        self.assertLess(final['steps'][2]['result']['rmse'], 1e-8)

    def test_invalid_config_and_termination_refused(self):
        for config in (False, {}, 0):
            with self.assertRaises(ValueError):
                self.w.run(self.path, config)
        with self.assertRaises(ValueError):
            self.w.run(self.path, terminate="false")
        self.assertFalse((self.path / "state.json").exists())

    def test_changed_config_refused(self):
        self.w.run(self.path, stop_after=1)
        with self.assertRaisesRegex(self.w.WorkflowError, 'CONFIG'):
            self.w.run(self.path, self.w.WorkflowConfig(seed=43))

    def test_budget_is_persistent_and_terminal(self):
        config = self.w.WorkflowConfig(max_calls=1)
        state = self.w.run(self.path, config)
        self.assertEqual(state['status'], 'budget_exhausted')
        self.assertEqual(state['attempts'], 1)
        self.assertEqual(self.w.run(self.path, config), state)

    def test_offline_approval_is_explicit(self):
        state = self.w.run(self.path, self.w.WorkflowConfig(offline_approved=False))
        self.assertEqual(state['status'], 'approval_required')
        self.assertEqual(state['attempts'], 0)
        self.assertEqual(state['hardware_status'], 'pending')
        with self.assertRaisesRegex(self.w.WorkflowError, 'OFFLINE'):
            self.w.ToolRequest('hardware.move', {})

    def test_tampered_state_refused(self):
        self.w.run(self.path, stop_after=1)
        p = self.path / 'state.json'
        state = json.loads(p.read_text())
        state['steps'][0]['result']['train']['velocity'][1] += 10
        p.write_text(json.dumps(state))
        with self.assertRaisesRegex(self.w.WorkflowError, 'STATE'):
            self.w.run(self.path)

    def test_concurrent_directory_refused(self):
        with self.w.directory_lock(self.path):
            with self.assertRaisesRegex(self.w.WorkflowError, 'LOCKED'):
                self.w.run(self.path)
        self.assertEqual(self.w.run(self.path)['status'], 'succeeded')

    def test_failure_recorded_and_terminal(self):
        config = self.w.WorkflowConfig(validation_tolerance=0)
        state = self.w.run(self.path, config)
        self.assertEqual(state['status'], 'failed')
        self.assertIn('VALIDATION', state['steps'][-1]['error'])
        self.assertEqual(self.w.run(self.path, config), state)

    def test_termination_is_persistent(self):
        self.w.run(self.path, stop_after=1)
        state = self.w.run(self.path, terminate=True)
        self.assertEqual(state['status'], 'terminated')
        self.assertEqual(self.w.run(self.path), state)

    def test_invalid_inputs(self):
        for kwargs in ({'samples': True}, {'max_calls': -1}, {'dt': float('nan')}, {'seed': 'bad'}):
            with self.assertRaises(ValueError):
                self.w.WorkflowConfig(**kwargs)
        with self.assertRaises(ValueError):
            self.w.run(self.path, stop_after=0)

    def test_unknown_tools_and_wrong_request_shapes_refused(self):
        registry = self.w.ToolRegistry()
        with self.assertRaises(self.w.WorkflowError):
            registry.execute(self.w.ToolRequest('fit', {'unexpected': 1}))
        with self.assertRaises(self.w.WorkflowError):
            registry.register('fit')

    def test_malformed_state_refused_without_overwriting(self):
        p = self.path / 'state.json'
        p.write_text('{"status":"succeeded"}')
        original = p.read_text()
        with self.assertRaises(self.w.WorkflowError):
            self.w.run(self.path)
        self.assertEqual(p.read_text(), original)

    def test_inflight_crash_consumes_attempt_then_resumes(self):
        from unittest.mock import patch
        real_execute = self.w.ToolRegistry.execute
        def interrupt(registry, request):
            if request.tool == 'fit':
                raise KeyboardInterrupt()
            return real_execute(registry, request)
        with patch.object(self.w.ToolRegistry, 'execute', interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.w.run(self.path)
        disk = json.loads((self.path / 'state.json').read_text())
        self.assertEqual(disk['attempts'], 2)
        self.assertEqual(disk['steps'][-1]['status'], 'running')
        observed = []
        def observe(registry, request):
            observed.append(request.tool)
            return real_execute(registry, request)
        with patch.object(self.w.ToolRegistry, 'execute', observe):
            result = self.w.run(self.path)
        self.assertEqual(observed, ['fit', 'validate'])
        self.assertEqual(result['attempts'], 4)
        self.assertEqual(result['status'], 'succeeded')

    def test_semantic_state_validation_even_with_updated_checksum(self):
        self.w.run(self.path, stop_after=1)
        p = self.path / 'state.json'
        state = json.loads(p.read_text())
        state['status'] = 'budget_exhausted'
        self.w._save(p, state)
        with self.assertRaisesRegex(self.w.WorkflowError, 'STATE'):
            self.w.run(self.path)

    def test_duplicate_json_keys_rejected(self):
        self.w.run(self.path, stop_after=1)
        p = self.path / 'state.json'
        contents = p.read_text()
        p.write_text('{"attempts":999,' + contents[1:])
        with self.assertRaisesRegex(self.w.WorkflowError, 'STATE'):
            self.w.run(self.path)

    def test_cli_exit_codes(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()):
            self.assertEqual(self.w.main(['--output', str(self.path), '--stop-after', '1']), 3)
            self.assertEqual(self.w.main(['--output', str(self.path)]), 0)
            self.assertEqual(self.w.main(['--output', str(self.path), '--seed', '2']), 2)

    def test_public_validate_request_rejects_nonfinite_tolerance_and_bad_types(self):
        from dataclasses import asdict
        from roboidf.core import MockRobot
        registry = self.w.ToolRegistry()
        base = {'model': {'mass': 2.0, 'damping': .4},
                'validation': asdict(MockRobot().collect(seed=1, split='validation')),
                'tolerance': 1e-8}
        bad = [{'tolerance': v} for v in (float('nan'), float('inf'), -1, True, '1')]
        bad += [{'model': {'mass': True, 'damping': .4}}, {'model': []},
                {'model': {'mass': 2., 'damping': .4, 'extra': 1}}, {'validation': []},
                {'validation': dict(base['validation'], extra=1)}]
        for change in bad:
            with self.subTest(change=change):
                with self.assertRaises(self.w.WorkflowError):
                    registry.execute(self.w.ToolRequest('validate', dict(base, **change)))
