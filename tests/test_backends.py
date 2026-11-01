import json
import unittest
from roboidf.core import Dataset, MockRobot, Parameters
from roboidf.backends import FitConfig, fit_bounded, select_excitation, simulate_continuous

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.train = MockRobot().collect(seed=4, split='train', samples=250)
        self.val = MockRobot().collect(seed=5, split='validation', samples=250)

    def test_fit_recovers_without_truth_and_reports_hashes(self):
        result = fit_bounded(self.train, self.val)
        self.assertEqual(result['status'], 'VALIDATED')
        self.assertAlmostEqual(result['model']['mass'], 2., places=5)
        self.assertAlmostEqual(result['model']['damping'], .4, places=5)
        self.assertEqual(result['diagnostics']['rank'], 2)
        self.assertEqual(result['data_hashes']['train'], self.train.digest())
        json.dumps(result, allow_nan=False)

    def test_extreme_validation_and_information_are_json_safe(self):
        val=Dataset(.02, (1e308,)*501, (0.,)*500, "validation", 5)
        self.assertEqual(fit_bounded(self.train, val)["failure"], "NUMERICAL_FAILURE")
        result=select_excitation({"large":[1e200,-1e200]*5}, Parameters(), .02, max_effort=1e201,max_slew=1e203)
        json.dumps(result, allow_nan=False)

    def test_zero_excitation_and_budget_reject(self):
        zero = Dataset(.02, (0.,)*31, (0.,)*30, 'train', 1)
        self.assertEqual(fit_bounded(zero, self.val)['failure'], 'UNIDENTIFIABLE')
        result = fit_bounded(self.train, self.val, FitConfig(max_evaluations=1))
        self.assertEqual(result['failure'], 'BUDGET_EXHAUSTED')
        self.assertLessEqual(result['diagnostics']['residual_evaluations'], 1)

    def test_validation_rejects_wrong_plant(self):
        val = MockRobot(Parameters(5, 2)).collect(seed=5, split='validation', samples=250)
        self.assertEqual(fit_bounded(self.train, val)['failure'], 'VALIDATION_FAILED')

    def test_split_and_config_rejected(self):
        with self.assertRaises(ValueError): fit_bounded(self.val, self.train)
        with self.assertRaises(ValueError): FitConfig(lower=(0., 0.))
        with self.assertRaises(ValueError): FitConfig(max_evaluations=True)

    def test_selection_constraints_and_budget(self):
        candidates = {'zero': [0.]*100, 'wave': [1., -1.]*50, 'unsafe': [20.]*100}
        result = select_excitation(candidates, Parameters(), .02, max_effort=2, max_slew=120, max_candidates=3)
        self.assertEqual(result['selected'], 'wave')
        self.assertEqual(result['rejected']['unsafe'], 'EFFORT_LIMIT')
        with self.assertRaises(ValueError):
            select_excitation(candidates, Parameters(), .02, max_candidates=2)

    def test_relabelled_same_data_rejected(self):
        duplicate = Dataset(self.train.dt, self.train.velocity, self.train.effort, 'validation', 999)
        with self.assertRaisesRegex(ValueError, 'identical'):
            fit_bounded(self.train, duplicate)

    def test_extreme_finite_data_structured_rejection(self):
        extreme = Dataset(.02, (1e308, -1e308, 1e308, 1e308), (1e308, -1e308, 1e308), 'train', 9)
        result = fit_bounded(extreme, self.val)
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(result['failure'], 'NUMERICAL_FAILURE')
        json.dumps(result, allow_nan=False)

    def test_continuous_matches_analytic_and_differs_from_euler(self):
        from math import exp
        data = simulate_continuous(Parameters(2., .4), [1.]*20, .1, split='test', seed=8)
        self.assertAlmostEqual(data.velocity[-1], (1-exp(-.4))/ .4, places=7)
        self.assertNotEqual(data.velocity[1], .05)

if __name__ == '__main__': unittest.main()
