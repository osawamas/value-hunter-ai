"""S68 parent equity must be same PDF as FY2026 Group financials."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from value_hunter_v19 import merge_s68_parent_equity
from s68_parent_equity_v54 import COMPONENTS, TOTALS


def financial():
    return {
        "symbol":"S68","pdf_sha256":"a"*64,
        "metrics":{"equity":{"2026":{"value":TOTALS["2026"]},
                             "2025":{"value":TOTALS["2025"]}}}
    }


def proof():
    return {
        "symbol":"S68","pdf_sha256":"a"*64,
        "source_url":"https://investorrelations.sgx.com/static-files/official",
        "status":"AUDITED_ISSUER_GROUP_OWNER_COMPONENTS_RECONCILED",
        "record":{
            "statement":"audited Group financial position",
            "attributable_to":"Company equity holders",
            "unit":"SGD_thousands","page_pdf_number":27,
            "reconciliation":"OWNER_COMPONENTS_EQUAL_GROUP_TOTAL_EQUITY",
            "parent_equity":TOTALS,
            "components":{k:{"2026":a,"2025":b} for k,(a,b) in COMPONENTS.items()}
        }
    }


def merge(record, reference):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"proof.json"
        path.write_text(json.dumps(reference),encoding="utf-8")
        return merge_s68_parent_equity(record,path)


class JoinTests(unittest.TestCase):
    def test_matching_document_and_group_owner_components(self):
        result=merge(financial(),proof())
        self.assertEqual(result["metrics"]["parent_equity"]["2026"]["value"],2362982)
        self.assertEqual(result["metrics"]["parent_equity"]["2026"]["page"],27)
    def test_different_document_not_promoted(self):
        p=proof()
        p["pdf_sha256"]="b"*64
        rec=financial()
        with self.assertRaises(ValueError):merge(rec,p)
        self.assertNotIn("parent_equity",rec["metrics"])
    def test_wrong_group_equity_not_promoted(self):
        r=financial()
        r["metrics"]["equity"]["2026"]["value"]=123
        with self.assertRaises(ValueError):merge(r,proof())
        self.assertNotIn("parent_equity",r["metrics"])
    def test_missing_component_rejected(self):
        p=proof()
        p["record"]["components"].pop("Proposed dividends")
        with self.assertRaises(ValueError):merge(financial(),p)
    def test_unverified_status_rejected(self):
        p=proof()
        p["status"]="NOT_VERIFIED"
        with self.assertRaises(ValueError):merge(financial(),p)

if __name__=="__main__":
    unittest.main()
