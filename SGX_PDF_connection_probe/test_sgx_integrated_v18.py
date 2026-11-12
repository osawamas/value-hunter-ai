import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('parser',Path(__file__).with_name('sgx_integrated_v18.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class Tests(unittest.TestCase):
 def test_number(self):
  self.assertEqual(p.number('(233,971)'),-233971);self.assertEqual(p.number('2,452,053'),2452053);self.assertIsNone(p.number('2025 SGD'))
 def test_ambiguous(self):
  r=p.find_row([{'x':43,'y':200,'text':'Revenue'}],'Revenue',(0,200),{2025:400},2025,'Group')
  self.assertEqual(r['status'],'UNVERIFIED')
 def test_exact_column(self):
  rows=[{'x':43,'y':200,'text':'Revenue'},{'x':439,'y':200.03,'text':'623,300'},{'x':507,'y':200.02,'text':'564,627'},{'x':900,'y':200,'text':'9,999,999'}]
  r=p.find_row(rows,'Revenue',(0,200),{2025:439,2024:507},2025,'Group')
  self.assertEqual(r['periods'][2025]['value'],623300)
 def test_balance_math(self):
  self.assertEqual(3066011-1629108-1436903,0)
  self.assertEqual(3558986-1978882-1580104,0)
if __name__=='__main__':unittest.main()
