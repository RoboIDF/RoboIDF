import unittest
from roboidf import Dataset, MockRobot, Parameters, fit, rollout_rmse, IdentificationError, run_demo

class CoreTests(unittest.TestCase):
    def test_recovers_parameters_and_generalizes(self):
        robot = MockRobot(Parameters(2.3, 0.7))
        model = fit(robot.collect(seed=1, split='train'))
        self.assertAlmostEqual(model.mass, 2.3, places=9)
        self.assertAlmostEqual(model.damping, 0.7, places=9)
        self.assertLess(rollout_rmse(model, robot.collect(seed=2, split='validation')), 1e-10)
    def test_zero_excitation_rejected(self):
        with self.assertRaisesRegex(IdentificationError, 'UNIDENTIFIABLE'):
            fit(Dataset(.02, (0.,)*11, (0.,)*10, 'train', 1))
    def test_bad_data(self):
        for dt,v,u in [(0,[0]*4,[0]*3),(.1,[0]*3,[0]*3),(.1,[0,float('nan'),0,0],[1]*3)]:
            with self.assertRaises(ValueError): Dataset(dt, tuple(v), tuple(u),'train',0)
    def test_holdout_cannot_train(self):
        with self.assertRaises(ValueError): fit(MockRobot().collect(seed=2,split='test'))
    def test_invalid_parameters(self):
        for m,c in [(0,1),(1,-1),(float('inf'),1)]:
            with self.assertRaises(ValueError): Parameters(m,c)
    def test_reproducible(self):
        self.assertEqual(run_demo(4), run_demo(4))
    def test_wrong_model_is_detected(self):
        data=MockRobot().collect(seed=8,split='test')
        self.assertGreater(rollout_rmse(Parameters(8,3),data),.01)

    def test_nonphysical_fit_rejected(self):
        # Negative mass produces velocity response opposite to applied force.
        u=(1.,-2.,3.,-1.,2.)
        v=[0.]
        for force in u: v.append(v[-1]+.02*(-force-.4*v[-1]))
        with self.assertRaisesRegex(IdentificationError, 'INVALID_MODEL'):
            fit(Dataset(.02,tuple(v),u,'train',0))
    def test_report_hashes_keep_splits_distinct(self):
        result=run_demo(0)
        self.assertNotEqual(result['train_sha256'],result['validation_sha256'])

    def test_divergent_rollout_rejected(self):
        with self.assertRaises(IdentificationError):
            rollout_rmse(Parameters(1e-300,1),MockRobot().collect(seed=8,split='test'))
