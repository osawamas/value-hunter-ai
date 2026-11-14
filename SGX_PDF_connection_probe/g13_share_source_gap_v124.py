"""v124: distinguish a G13 primary share quantity match from an as-of-date match."""
import argparse,hashlib,json
from pathlib import Path
from datetime import date
def compare(feed,evidence):
 if feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_eligible_count")!=0:
  raise ValueError("Unsafe feed")
 matches=[r for r in feed.get("records",[]) if r.get("symbol")=="G13"]
 if len(matches)!=1:raise ValueError("G13 not unique")
 r=matches[0]
 if (evidence.get("schema_version")!="sgx-g13-buyback-share-basis-v122" or
     evidence.get("status")!="SGX_G13_PRIMARY_JUNE10_BUYBACK_SHARE_SNAPSHOT"):
  raise ValueError("SGX original not verified")
 s=evidence.get("record")
 if (not isinstance(s,dict) or s.get("status")!=evidence["status"] or
     s.get("symbol")!="G13" or s.get("isin")!="SGXE21576413" or
     s.get("reference")!="SG260610OTHRU53S" or
     s.get("proof_applies_only_to_june_10") is not True or
     s.get("june_30_shares_independently_confirmed") is not False or
     s.get("current_shares_verified") is not False or
     s.get("ranking_eligible") is not False or
     s.get("source_url")!=evidence.get("source_url")):
  raise ValueError("SGX original trust flags or identity mismatch")
 original=date.fromisoformat(s["purchase_date"])
 published=date.fromisoformat(r["shares_as_of_date"])
 if published<original:raise ValueError("Publication date predates evidence")
 if r.get("shares_count_basis")!="issued_excluding_treasury":
  raise ValueError("Treasury-adjusted basis not declared")
 observed=s["issued_excluding_treasury_after_purchase"]
 displayed=r.get("shares_outstanding")
 if type(displayed) is not int or type(observed) is not int or displayed<=0 or observed<=0:
  raise ValueError("Share counts invalid")
 return {
  "schema_version":"sgx-g13-share-source-date-gap-v124",
  "symbol":"G13",
  "sgx_original_purchase_date":str(original),
  "public_feed_claimed_shares_date":str(published),
  "date_difference_days":(published-original).days,
  "published_shares":displayed,
  "sgx_primary_record_shares":observed,
  "quantity_matched":displayed==observed,
  "primary_source_proves_published_date":published==original,
  "sgx_primary_source_url":s["source_url"],
  "source_reference":s["reference"],
  "pdf_or_html_source_sha256":s["html_sha256"],
  "current_treasury_adjusted_shares_independently_verified":False,
  "reference_market_cap_pbr_per_permitted":False,
  "ranking_eligible":False,
  "financial_feed_modified":False,
  "warning":"Same share quantity at two described dates is not proof of shares on the later date."
 }
def main():
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--original",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 fp=Path(a.feed);before=hashlib.sha256(fp.read_bytes()).hexdigest()
 o=compare(json.loads(fp.read_text()),json.loads(Path(a.original).read_text()))
 assert hashlib.sha256(fp.read_bytes()).hexdigest()==before
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("G13 day gap",o["date_difference_days"],"quantity match",o["quantity_matched"])
if __name__=="__main__":main()
