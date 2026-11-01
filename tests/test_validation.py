import copy
import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from roboidf.validation import validate_contract, hardware_precheck, validate_asset, compare_replay, example_contract, example_trajectory

class ValidationTests(unittest.TestCase):
    def test_contract_and_hardware_boundary(self):
        c = example_contract()
        self.assertTrue(validate_contract(c)['passed'])
        c['mode'] = 'hardware'
        r = hardware_precheck(c)
        self.assertFalse(r['passed'])
        self.assertEqual(len(r['missing_evidence']), 4)
        c['hardware_evidence'] = dict.fromkeys(['sdk','calibration','approval','stop'], 'claimed')
        self.assertFalse(hardware_precheck(c)['execution_authorized'])

    def test_contract_rejections(self):
        for key, value in [('schema_version','future'),('source',{}),('authorization','approved'),('clock',{'unit':'ms','domain':'monotonic'})]:
            c=example_contract(); c[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_contract(c)
        c=example_contract(); c['joints'][0]['velocity_unit']='rad/s'
        with self.assertRaises(ValueError): validate_contract(c)
        c=example_contract(); c['joints']*=2
        with self.assertRaises(ValueError): validate_contract(c)

    def test_assets_are_only_structure(self):
        s=example_contract()['source']
        r=validate_asset('<mujoco><worldbody><body name="b"/></worldbody></mujoco>','mjcf',s)
        self.assertEqual(r['twin_status'],'pending')
        self.assertTrue(validate_asset('#usda 1.0\ndef Xform "Root" {}','usd',s)['passed'])
        for text,kind in [('<robot/>','mjcf'),('<mujoco/>','mjcf'),('invalid','usd'),('<!DOCTYPE x><mujoco><worldbody/></mujoco>','mjcf')]:
            with self.assertRaises(ValueError): validate_asset(text,kind,s)

    def test_replay_alignment_units_and_threshold(self):
        a=example_trajectory(); b=copy.deepcopy(a)
        self.assertTrue(compare_replay(a,b,rmse_limit=.01)['passed'])
        b['velocity'][1][0] += 1
        self.assertFalse(compare_replay(a,b,rmse_limit=.01)['passed'])
        for key,value in [('time',[0,.2,.3]),('velocity_units',['rad/s']),('joint_names',['wrong']),('clock_domain','other')]:
            b=copy.deepcopy(a); b[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): compare_replay(a,b,rmse_limit=.01)
        with self.assertRaises(ValueError): compare_replay(a,a,rmse_limit=float('nan'))
        a['velocity'][0][0]=float('nan')
        with self.assertRaises(ValueError): compare_replay(a,a,rmse_limit=.01)

    def test_cli_and_hardware_contract(self):
        for arguments, code in [([],0),(['--hardware'],1)]:
            p=subprocess.run([sys.executable,'-m','roboidf.validation',*arguments],capture_output=True,text=True)
            self.assertEqual(p.returncode,code,p.stderr)
            result=json.loads(p.stdout)
            self.assertFalse(result['execution_authorized'])
            self.assertEqual(result['hardware_status'],'pending')
        c=example_contract(); c['mode']='hardware'; c['authorization']='pending'
        with self.assertRaises(ValueError): validate_contract(c)
        c['adapter']['kind']='hardware-pending'
        self.assertTrue(validate_contract(c)['passed'])

    def test_cli_saves_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'validation.json'
            p=subprocess.run([sys.executable,'-m','roboidf.validation','--hardware','--output',str(output)],capture_output=True,text=True)
            self.assertEqual(p.returncode,1,p.stderr)
            self.assertEqual(json.loads(output.read_text()),json.loads(p.stdout))
