import json
import tempfile
import unittest
from pathlib import Path
import pymupdf
from layout_probe import inspect_document

class LayoutProbeTests(unittest.TestCase):
    def test_extracts_label_coordinates(self):
        doc=pymupdf.open()
        p=doc.new_page()
        p.insert_text((50,80),'Operating revenue 1,559,469 1,370,625')
        with tempfile.TemporaryDirectory() as td:
            result=inspect_document(doc,td)
            self.assertEqual(len(result),1)
            self.assertTrue((Path(td)/'layout_diagnostics.json').exists())
            self.assertTrue(result[0]['rows'][0]['numeric_near_row'])
        doc.close()
    def test_no_matching_rows(self):
        doc=pymupdf.open();p=doc.new_page();p.insert_text((50,80),'Some other content')
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(inspect_document(doc,td),[])
        doc.close()
if __name__=='__main__':unittest.main()
