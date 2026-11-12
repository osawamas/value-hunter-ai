import unittest
from coordinate_audit_v17 import grouped_lines, analyze_page, VERSION
class FakeRect:
    width=600;height=800
class FakePage:
    rect=FakeRect()
    def get_text(self, mode):
        assert mode=='words'
        return [(10,10,55,20,'Revenue',0,0,0),(220,10,260,20,'2025',0,0,1),(300,10,340,20,'2024',0,0,2), (10,30,80,40,'Group',0,1,0)]
class Tests(unittest.TestCase):
    def test_version(self): self.assertEqual(VERSION,'v17.0.0')
    def test_lines(self): self.assertEqual(len(grouped_lines(FakePage().get_text('words'))),2)
    def test_coordinates(self):
        d=analyze_page(FakePage(),36)
        self.assertEqual(d['page'],36)
        self.assertEqual(d['matches'][0]['x0'],10)
        self.assertEqual(d['status'],'LAYOUT_EVIDENCE_ONLY_NOT_VERIFIED')
    def test_no_verification(self): self.assertNotIn('VERIFIED',analyze_page(FakePage(),36)['status'].split('_')[0])
if __name__=='__main__':unittest.main()
