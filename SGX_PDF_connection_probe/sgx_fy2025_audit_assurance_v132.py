"""v132: reconcile actual external auditor opinions with FY2025 feed data.

Audit assurance is real but limited to fiscal-year financial statements.
It is not independently recalculated metric verification, current market data
or approval for scoring.
"""
import argparse,hashlib,json
from pathlib import Path

OPINIONS={
 "G13":{"file_schema":"sgx-g13-fy2025-auditor-probe-v130",
        "verified_status":"INDEPENDENT_FY2025_AUDITOR_OPINION_IN_PRIMARY_PDF_CONFIRMED",
        "proof_schema":"sgx-g13-fy2025-independent-auditor-opinion-v130",
        "hash_field":"source_pdf_sha256","auditor_field":"auditor_issuer",
        "period_field":"audited_annual_group_financials_period_end",
        "independent_field":"auditor_independence_statement_observed",
        "opinion_field":"independent_auditor_opinion_found",
        "revenue_field":"reported_annual_revenue_sgd_thousands"},
 "S63":{"file_schema":"sgx-s63-auditor-probe-v131",
        "verified_status":"SGX_INDEPENDENT_S63_FY2025_AUDITOR_REPORT_CONFIRMED",
        "proof_schema":"sgx-s63-fy2025-independent-audit-proof-v131",
        "hash_field":"auditor_document_sha256","auditor_field":"auditor",
        "period_field":"audit_reporting_period_end",
        "independent_field":"auditor_independence_statement_verified",
        "opinion_field":"audit_opinion_scope_verified",
        "revenue_field":None}
}
def combine(feed, originals):
 if (feed.get("schema_version")!="value_hunter_web_v29" or
     feed.get("ranking_eligible_count")!=0 or feed.get("ranking_enabled") is not False):
  raise ValueError("Published feed not safe for research binding")
 rows=feed.get("records")
 if not isinstance(rows,list) or len(rows)!=7:
  raise ValueError("Expected 7 registered companies")
 mapped={r.get("symbol"):r for r in rows}
 if len(mapped)!=7 or any(s not in mapped for s in OPINIONS):
  raise ValueError("Issuer list not valid")
 result=[]
 for symbol,p in OPINIONS.items():
  doc=originals.get(symbol)
  if not isinstance(doc,dict) or doc.get("schema_version")!=p["file_schema"] or doc.get("status")!=p["verified_status"]:
   raise ValueError("External audit original not actually validated: "+symbol)
  o=doc.get("record");r=mapped[symbol]
  if (not isinstance(o,dict) or o.get("schema_version")!=p["proof_schema"] or
      o.get("symbol")!=symbol or r.get("ranking_eligible") is not False or
      r.get("fiscal_year")!=2025 or
      o.get(p["hash_field"])!=r.get("financial_pdf_sha256") or
      o.get("source_url")!=r.get("financial_source_url") or
      o.get(p["auditor_field"])!="PricewaterhouseCoopers LLP" or
      o.get(p["period_field"])!="2025-12-31" or
      o.get(p["independent_field"]) is not True or
      o.get(p["opinion_field"]) is not True or
      o.get("ranking_eligible") is not False or
      o.get("financial_feed_modified") is not False):
   raise ValueError("Audit scope / issuer / digest mismatch: "+symbol)
  if p["revenue_field"] and o.get(p["revenue_field"])!=r.get("revenue_sgd_thousands"):
   raise ValueError("G13 annual revenue record changed")
  if symbol=="S63" and (o.get("auditor_KAM_mentions_revenue_sgd") !=
                         r.get("revenue_sgd_thousands")*1000 or
                         o.get("published_revenue_matches_auditor_KAM") is not True):
   raise ValueError("S63 audited revenue KAM not aligned")
  result.append({
   "symbol":symbol,"fiscal_year":2025,
   "independent_external_audit_opinion_observed":True,
   "auditor":"PricewaterhouseCoopers LLP",
   "auditor_scope_end":"2025-12-31",
   "annual_report_primary_source_url":o["source_url"],
   "annual_report_primary_sha256":o[p["hash_field"]],
   "fy2025_revenue_in_audited_report_reference":True,
   "reperformed_independent_financial_calculations":False,
   "2026_interim_audited_by_same_fy2025_opinion":False,
   "current_shares_and_quote_independently_verified":False,
   "parent_equity_independently_reperformed":False,
   "eligible_for_ranking":False
  })
 return {
   "schema_version":"sgx-fy2025-audit-assurance-v132",
   "linked_published_feed_updated_at_utc":feed.get("updated_at_utc"),
   "registered_count":len(rows),
   "external_auditor_fy2025_opinion_confirmed_count":len(result),
   "external_auditor_opinion_is_not_live_market_verification":True,
   "numeric_recalculation_completed_count":0,
   "ranking_eligible_count":0,
   "financial_feed_modified":False,
   "records":result
 }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True);p.add_argument("--g13",required=True)
 p.add_argument("--s63",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 original=Path(a.feed);before=hashlib.sha256(original.read_bytes()).hexdigest()
 result=combine(json.loads(original.read_text()),{
  "G13":json.loads(Path(a.g13).read_text()),"S63":json.loads(Path(a.s63).read_text())})
 if before!=hashlib.sha256(original.read_bytes()).hexdigest():
  raise ValueError("Published feed changed mid validation")
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("FY2025 external opinions recorded:",result["external_auditor_fy2025_opinion_confirmed_count"])
if __name__=="__main__":main()
