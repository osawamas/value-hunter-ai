"""v93: no bank valuation eligibility from audited historic/pending inputs."""
import unittest
from bank_market_readiness_v93 import annotate

def input_feed():
 rows=[]
 for symbol in ("D05","O39","U11"):
  row={"symbol":symbol,"ranking_eligible":False,
       "bank_financial_state":{"status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"},
       "banking_interim_2026":{"status":"ISSUER_3Q_AND_NINE_MONTH_TRADING_UPDATE_REGRESSION_MATCHED"},
       "shares_outstanding":None,"price_sgd":None,"market_cap_sgd":None,
       "per_reference":None,"pbr_reference_unverified":None,"pbr_verified":None}
  if symbol=="U11":
   row["bank_primary_three_day_chain"]={"status":"ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED"}
   row["bank_pending_buyback_consistency"]={"status":"SECONDARY_NOV13_ARITHMETICALLY_CONSISTENT_PRIMARY_NOT_VERIFIED",
                                             "latest_current_shares_verified":False}
  if symbol=="O39":
   row["bank_share_discovery"]={"status":"SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED",
       "sgx_announcement_reference":"SG261112OTHRXH64","primary_sgx_announcement_url":None}
  rows.append(row)
 rows.append({"symbol":"S68","ranking_eligible":False})
 return {"schema_version":"value_hunter_web_v29","records":rows}

class TestReadiness(unittest.TestCase):
 def test_banks_have_precise_source_specific_blockers(self):
  src=input_feed();out=annotate(src)
  by_symbol={r["symbol"]:r for r in out["records"]}
  for symbol in ("D05","O39","U11"):
   ready=by_symbol[symbol]["bank_market_readiness"]
   self.assertFalse(ready["bank_valuation_eligible"])
   self.assertFalse(ready["investment_ranking_eligible"])
   self.assertFalse(ready["official_current_share_count_verified"])
   self.assertFalse(ready["current_quote_timestamp_verified"])
   self.assertIsNone(by_symbol[symbol]["shares_outstanding"])
  self.assertIn("UOB_NOV13_BUYBACK_PRIMARY_SGX_NOTICE_NOT_VERIFIED",
                by_symbol["U11"]["bank_market_readiness"]["required_checks"])
  self.assertIn("OCBC_NOV12_TREASURY_TRANSFER_PRIMARY_PDF_NOT_VERIFIED",
                by_symbol["O39"]["bank_market_readiness"]["required_checks"])
  self.assertNotIn("bank_market_readiness",by_symbol["S68"])
  self.assertNotIn("bank_market_readiness",src["records"][0])
 def test_unresolved_uob_source_cannot_be_marked_current(self):
  f=input_feed();f["records"][2]["bank_pending_buyback_consistency"]["latest_current_shares_verified"]=True
  with self.assertRaises(ValueError):annotate(f)
 def test_ocbc_must_not_invent_primary_url(self):
  f=input_feed();f["records"][1]["bank_share_discovery"]["primary_sgx_announcement_url"]="https://example.com"
  with self.assertRaises(ValueError):annotate(f)
 def test_missing_quarter_data_rejected(self):
  f=input_feed();f["records"][0].pop("banking_interim_2026")
  with self.assertRaises(ValueError):annotate(f)
 def test_valued_bank_rejected(self):
  f=input_feed();f["records"][1]["pbr_verified"]=1.4
  with self.assertRaises(ValueError):annotate(f)
 def test_duplicate_bank_rejected(self):
  f=input_feed();f["records"].append(f["records"][2].copy())
  with self.assertRaises(ValueError):annotate(f)

if __name__=="__main__":unittest.main()
