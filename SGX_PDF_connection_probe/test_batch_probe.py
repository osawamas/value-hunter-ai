import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from batch_probe import validate_manifest, candidates, run

class BatchTests(unittest.TestCase):
    def test_manifest_rejects_duplicate_ids(self):
        x={'documents':[{'ticker':'S68','document_id':'one','url':'https://example.com/a.pdf'}]*2}
        with self.assertRaises(ValueError):validate_manifest(x)
    def test_manifest_rejects_http(self):
        with self.assertRaises(ValueError):validate_manifest({'documents':[{'ticker':'S68','document_id':'one','url':'http://example.com/a.pdf'}]})
    def test_candidates_are_unverified(self):
        c=candidates(['Operating profit 887,190 742,843'])
        self.assertEqual(c[0]['status'],'unverified_candidate')
        self.assertEqual(c[0]['number_tokens'],['887,190','742,843'])
    def test_batch_report_failure_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);manifest=p/'manifest.json'
            manifest.write_text(json.dumps({'documents':[{'ticker':'X','document_id':'x','url':'https://example.com/x.pdf'}]}))
            def fail(url):raise RuntimeError('offline')
            r=run(manifest,p/'results',fail)
            self.assertEqual(r['pdf_failure_count'],1)
            self.assertTrue((p/'results'/'batch_summary.csv').exists())
            self.assertEqual(r['generic_financial_verification'],'NOT_IMPLEMENTED')

if __name__=='__main__':unittest.main()
