"""Historical issuer shareholding publication must not create current shares."""
import copy,unittest
from bank_historical_share_publish_v76 import attach
from bank_historical_shares_v75 import CONFIG
from bank_statements_probe_v66 import SOURCES

def make(symbol):
 s=CONFIG[symbol]
 url=SOURCES[symbol]["url"]
 row={"symbol":symbol,"ranking_eligible":False,
      "shares_outstanding":None,"gross_issued_shares":None,"treasury_shares":None,
      "price_sgd":None,"market_cap_sgd":None,"per_reference":None,
      "pbr_reference_unverified":None,
      "banking_audited":{"status":"ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS",
                          "source_url":url,"pdf_sha256":"a"*64}}
 feed={"schema_version":"value_hunter_web_v29","records":[row]}
 proof={"symbol":symbol,"status":"ISSUER_HISTORICAL_TREASURY_ARITHMETIC_RECONCILED",
        "source_url":url,"pdf_sha256":"a"*64,
        "record":{"symbol":symbol,"as_of_date":s["date"],
                  "historical_only":True,"market_cap_or_ranking_eligible":False,
                  "shares_count_basis":"issued_excluding_treasury",
                  "source_pdf_page":s["page"],"subsidiary_holdings":0,
                  "gross_issued_shares":s["gross"],
                  "treasury_shares":s["treasury"],
                  "issued_excluding_treasury":s["net"]}}
 return feed,proof

class HistoricalPublishTests(unittest.TestCase):
 def test_both_issuers_have_only_historical_nested_shares(self):
  for sym in ("O39","U11"):
   feed,proof=make(sym)
   result=attach(feed,proof)
   row=result["records"][0]
   self.assertEqual(row["bank_historical_shares"]["as_of_date"],CONFIG[sym]["date"])
   self.assertFalse(row["bank_historical_shares"]["current_market_cap_usable"])
   self.assertIsNone(row["shares_outstanding"])
   self.assertIsNone(row["per_reference"])
   self.assertFalse(row["ranking_eligible"])
   self.assertNotIn("bank_historical_shares",feed["records"][0])
 def test_pdf_identity_mismatch_rejected(self):
  f,p=make("O39");p["pdf_sha256"]="b"*64
  with self.assertRaises(ValueError):attach(f,p)
 def test_wrong_date_rejected(self):
  f,p=make("U11");p["record"]["as_of_date"]="2026-11-14"
  with self.assertRaises(ValueError):attach(f,p)
 def test_changed_treasury_rejected(self):
  f,p=make("O39");p["record"]["treasury_shares"]+=1
  with self.assertRaises(ValueError):attach(f,p)
 def test_current_share_data_does_not_get_overwritten(self):
  f,p=make("U11");f["records"][0]["shares_outstanding"]=123
  with self.assertRaises(ValueError):attach(f,p)
 def test_missing_audited_source_rejected(self):
  f,p=make("O39");f["records"][0]["banking_audited"]={}
  with self.assertRaises(ValueError):attach(f,p)
 def test_status_unverified_rejected(self):
  f,p=make("O39");p["status"]="NOT_VERIFIED"
  with self.assertRaises(ValueError):attach(f,p)

if __name__=="__main__":unittest.main()
