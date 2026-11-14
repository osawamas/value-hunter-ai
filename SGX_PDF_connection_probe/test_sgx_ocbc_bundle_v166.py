import copy,unittest
from sgx_ocbc_bundle_v166 import combine,INPUTS
def fixture():
 sha="a"*64
 obj={}
 for key,(schema,status) in INPUTS.items():
  row={"schema_version":schema,"symbol":"O39","ranking_eligible":False}
  obj[key]={"status":status,"record":row}
 obj["originals"]["record"].update(original_attachment_count=3,
   records=[{"filename":"OCBC_3Q26_Results_Press_Release.pdf","sha256":sha,
     "official_sgx_original_url":"https://links.sgx.com/original.pdf"}])
 for k,field in {"rounded":"original_sgx_pdf_sha256","ratios":"sgx_primary_pdf_sha256",
  "exact":"official_press_sha256","income":"original_pdf_sha256",
  "allowances":"original_sgx_sha256","balance":"official_source_pdf_sha256"}.items():
  obj[k]["record"][field]=sha
 obj["rounded"]["record"].update(group_net_profit_3q26_sgd_billion_reported="2.04",
                                  group_net_profit_9m26_sgd_billion_reported="6.24")
 obj["exact"]["record"].update(group_profit_3q26_sgd_millions=2042,group_profit_9m26_sgd_millions=6237)
 obj["income"]["record"]["bank_statements"]={
 "3Q26":{"net_interest_income":2313,"non_interest_income":1420,
  "combined_interest_and_noninterest_income":3733,"allowances_charged":52},
 "9M26":{"net_interest_income":6798,"non_interest_income":4933,
  "combined_interest_and_noninterest_income":11731,"allowances_charged":424}}
 obj["allowances"]["record"].update(impaired_asset_allowances_9m26=190,
  non_impaired_asset_allowances_9m26=234,total_allowances_9m26=424)
 obj["balance"]["record"].update(attributable_equity_less_ordinary_equity=2448,
  difference_is_not_identified_as_noncontrolling_interest=True,
  selected_bank_items={
  "ordinary_equity":{"sgd_millions":60899},
  "equity_attributable_to_bank_equity_holders":{"sgd_millions":63347},
  "total_assets":{"sgd_millions":731689},
  "net_customer_loans":{"sgd_millions":366929},
  "deposits_nonbank_customers":{"sgd_millions":461462}})
 obj["ratios"]["record"].update(net_interest_margin_3q26_pct_issuer_reported="1.66",
  nonperforming_loan_ratio_pct_issuer_reported="0.8",
  cet1_capital_adequacy_ratio_pct_reported="15.5",
  return_on_equity_3q26_annualised_pct_reported="13.1")
 return obj
class Tests(unittest.TestCase):
 def test_bundle_same_issuer_not_independent(self):
  x=combine(fixture())
  self.assertFalse(x["independent_third_party_financial_reperformance"])
  self.assertFalse(x["per_pbr_and_ranking_permitted"])
  self.assertEqual(x["income_statement_sgd_millions"]["9M26"]["allowances_charged"],424)
 def test_wrong_origins_or_ranking_rejected(self):
  for change in [
   lambda x:x["exact"]["record"].update(official_press_sha256="b"*64),
   lambda x:x["allowances"]["record"].update(non_impaired_asset_allowances_9m26=235),
   lambda x:x["balance"]["record"].update(difference_is_not_identified_as_noncontrolling_interest=False),
   lambda x:x["income"]["record"]["bank_statements"]["3Q26"].update(net_interest_income=99),
   lambda x:x["ratios"]["record"].update(independent_numerical_verification=True),
   lambda x:x["rounded"]["record"].update(ranking_eligible=True)
  ]:
   f=fixture();change(f)
   with self.assertRaises(ValueError):combine(f)
if __name__=="__main__":unittest.main()
