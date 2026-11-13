import unittest
from value_hunter_v22 import parse_s20_ir,owner_equity

class Tests(unittest.TestCase):
 def test_parse(self):
  s='<td>Issued &amp; Paid-up Shares</td><td>484,822,826</td><p>Updated on 17/08/2026</p>'
  d=parse_s20_ir(s)
  self.assertEqual(d['shares_outstanding'],484822826)
  self.assertEqual(d['as_of_date'],'2026-08-17')
 def test_missing_date_rejected(self):
  with self.assertRaises(ValueError):parse_s20_ir('Issued &amp; Paid-up Shares 484,822,826')
 def test_missing_count_rejected(self):
  with self.assertRaises(ValueError):parse_s20_ir('Updated on 17/08/2026')
 def test_owner_equity(self):
  self.assertEqual(owner_equity({'symbol':'S20','fiscal_year':2025,'metrics':{}})[0],1248331)
 def test_nonparent_suppressed(self):
  self.assertIsNone(owner_equity({'symbol':'G13','fiscal_year':2025,'metrics':{'equity':{'2025':{'value':8205416}}}})[0])
if __name__=='__main__':unittest.main()
