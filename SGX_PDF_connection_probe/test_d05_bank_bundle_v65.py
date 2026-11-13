"""v65 strict bank-bundle publishing to a generic SGX feed."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import d05_bank_bundle_v65 as source
from d05_bank_publish_v65 import attach_bank_evidence


def income():
    pairs={
        "net_interest_income":(14500,14424),
        "non_interest_income":(8400,7873),
        "total_income":(22900,22297),
        "total_expenses":(9349,9018),
        "allowances_for_credit_losses":(791,622),
        "net_profit":(10934,11290),
        "profit_attributable_to_parent":(10933,11289),
        "non_controlling_profit":(1,1),
    }
    return {"fiscal_year":2025,"unit":"SGD_millions",
            "industry_metric_schema":"BANKING_INCOME_V63_NOT_INDUSTRIAL",
            "ranking_eligible":False,"pdf_page_number":58,
            "metrics":{k:{"2025":a,"2024":b} for k,(a,b) in pairs.items()}}

def balance():
    pairs={"total_assets":(897488,827219),"total_liabilities":(828572,758386),
           "net_assets":(68916,68833),"parent_shareholders_funds":(68867,68786),
           "non_controlling_interests":(49,47),"total_equity":(68916,68833),
           "customer_loans":(445011,430594)}
    return {"fiscal_year":2025,"unit":"SGD_millions",
            "metric_schema":"BANKING_BALANCE_V64_NOT_INDUSTRIAL",
            "ranking_eligible":False,"pdf_page_number":60,
            "metrics":{k:{"2025":a,"2024":b} for k,(a,b) in pairs.items()}}

def shares():
    return {"as_of_date":"2026-02-10","shares_outstanding":2837558046,
            "treasury_shares":113424,"issued_shares_including_treasury_derived":2837671470,
            "page_pdf_number":195}


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.raw=b"%PDF-issuer-example"
        with patch.object(source.shares,"parse_pdf",return_value=shares()), \
             patch.object(source.income,"parse_pdf",return_value=income()), \
             patch.object(source.balance,"parse_pdf",return_value=balance()):
            evidence=source.combine(self.raw)
        self.bundle={"symbol":"D05","status":evidence["status"],"evidence":evidence}
        self.feed={"schema_version":"value_hunter_web_v29",
                   "records":[{"symbol":"D05","ranking_eligible":False,
                               "financial_source_kind":"REGISTERED_SOURCE_NOT_PARSED",
                               "financial_source_url":source.shares.SOURCE,
                               "price_sgd":None,"market_cap_sgd":None,
                               "per_reference":None,"pbr_reference_unverified":None},
                              {"symbol":"S68","ranking_eligible":False,"price_sgd":12}]}

    def test_one_pdf_three_extractors_and_preserves_generic_fields(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(source.shares,"fetch",side_effect=lambda:(calls.append(1),self.raw)[1]), \
                 patch.object(source.shares,"parse_pdf",return_value=shares()), \
                 patch.object(source.income,"parse_pdf",return_value=income()), \
                 patch.object(source.balance,"parse_pdf",return_value=balance()):
                rec=source.run(Path(tmp)/"bundle.json")
        self.assertEqual(len(calls),1)
        self.assertEqual(rec["status"],"DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED")
        new=attach_bank_evidence(self.feed,self.bundle)
        d05=new["records"][0]
        self.assertEqual(d05["banking_evidence"]["income"]["2025"]["total_income"],22900)
        self.assertEqual(d05["banking_evidence"]["balance"]["2025"]["parent_shareholders_funds"],68867)
        self.assertIsNone(d05["per_reference"])
        self.assertFalse(d05["ranking_eligible"])
        self.assertEqual(new["records"][1],self.feed["records"][1])
        self.assertNotIn("banking_evidence",self.feed["records"][0])

    def test_unverified_pdf_rejected(self):
        b=copy.deepcopy(self.bundle);b["status"]="NOT_VERIFIED"
        with self.assertRaises(ValueError):attach_bank_evidence(self.feed,b)

    def test_incomplete_bank_metrics_rejected(self):
        b=copy.deepcopy(self.bundle);del b["evidence"]["income"]["2025"]["total_income"]
        with self.assertRaises(ValueError):attach_bank_evidence(self.feed,b)

    def test_wrong_equity_rejected(self):
        b=copy.deepcopy(self.bundle);b["evidence"]["balance"]["2025"]["total_equity"]+=1
        with self.assertRaises(ValueError):attach_bank_evidence(self.feed,b)

    def test_unverified_quote_does_not_get_exposed(self):
        feed=copy.deepcopy(self.feed);feed["records"][0]["price_sgd"]=10
        with self.assertRaises(ValueError):attach_bank_evidence(feed,self.bundle)

    def test_negative_treasury_rejected(self):
        b=copy.deepcopy(self.bundle)
        b["evidence"]["shares"]["treasury_shares"]=-1
        with self.assertRaises(ValueError):attach_bank_evidence(self.feed,b)

    def test_bad_report_scope_rejected(self):
        b=copy.deepcopy(self.bundle);b["evidence"]["shares_as_of_date"]="2025-02-10"
        with self.assertRaises(ValueError):attach_bank_evidence(self.feed,b)

if __name__=="__main__":unittest.main()
