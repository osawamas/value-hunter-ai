"""v127: reconcile actual G13 June 30 half-year SGX original vs June 10 buyback.

A June-30 issuer document can directly support the June-30 public feed share
basis; the June-10 notice by itself cannot. These are both SAME-ISSUER
records, not independent third-party market verification, and never verify
shares as of Nov 14.
"""
import argparse,hashlib,json
from pathlib import Path
from g13_shareholding_v48 import fetch,parse_pdf,SOURCE

def compare(feed, notice, halfyear, halfyear_sha):
 if feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_eligible_count")!=0:
  raise ValueError("Unsafe current financial feed")
 rec=[r for r in feed.get("records",[]) if r.get("symbol")=="G13"]
 if len(rec)!=1:raise ValueError("G13 not unique")
 r=rec[0]
 if (r.get("shares_as_of_date")!="2026-06-30" or
     r.get("shares_count_basis")!="issued_excluding_treasury" or
     r.get("shares_source_url")!=SOURCE):
  raise ValueError("Public reference provenance not exact")
 if (notice.get("schema_version")!="sgx-g13-buyback-share-basis-v122" or
     notice.get("status")!="SGX_G13_PRIMARY_JUNE10_BUYBACK_SHARE_SNAPSHOT"):
  raise ValueError("Unverified June notice")
 n=notice.get("record")
 if (not isinstance(n,dict) or n.get("symbol")!="G13" or
     n.get("purchase_date")!="2026-06-10" or
     n.get("june_30_shares_independently_confirmed") is not False or
     n.get("issued_excluding_treasury_after_purchase")!=12063642274 or
     n.get("treasury_shares_after_purchase")!=30384550):
  raise ValueError("June notice identity or quantity mismatch")
 if (not isinstance(halfyear,dict) or halfyear.get("as_of_date")!="2026-06-30" or
     halfyear.get("shares_outstanding")!=12063642274 or
     halfyear.get("treasury_shares")!=30384550 or
     halfyear.get("issued_shares_including_treasury")!=12094026824 or
     halfyear.get("share_count_basis")!="issued_excluding_treasury" or
     halfyear["issued_shares_including_treasury"]-halfyear["treasury_shares"]!=
     halfyear["shares_outstanding"] or
     not isinstance(halfyear_sha,str) or len(halfyear_sha)!=64):
  raise ValueError("No valid dated H1 SGX source proof")
 if (r["shares_outstanding"]!=halfyear["shares_outstanding"] or
     r["treasury_shares"]!=halfyear["treasury_shares"] or
     r["gross_issued_shares"]!=halfyear["issued_shares_including_treasury"] or
     r.get("shares_pdf_sha256")!=halfyear_sha):
  raise ValueError("Public G13 source hash or shares not equal to official PDF")
 return {
  "schema_version":"sgx-g13-h1-direct-primary-share-confirmation-v127",
  "symbol":"G13",
  "published_share_date":"2026-06-30",
  "official_h1_report_date":"2026-06-30",
  "official_june10_buyback_date":"2026-06-10",
  "published_june30_count_original_primary_supported":True,
  "june10_primary_count_matches_june30_primary":True,
  "issued_gross_at_june30":halfyear["issued_shares_including_treasury"],
  "treasury_at_june30":halfyear["treasury_shares"],
  "issued_ex_treasury_at_june30":halfyear["shares_outstanding"],
  "june10_notice_source_url":n["source_url"],
  "june30_halfyear_source_url":SOURCE,
  "june30_primary_pdf_sha256":halfyear_sha,
  "same_issuer_documents_not_independent_third_party_verification":True,
  "shares_after_june30_unchanged_verified":False,
  "live_market_quote_verified":False,
  "market_cap_per_pbr_promoted":False,
  "ranking_eligible":False,
  "financial_feed_modified":False
 }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True)
 p.add_argument("--june-notice",required=True)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 fp=Path(a.feed);pre=hashlib.sha256(fp.read_bytes()).hexdigest()
 source=fetch();sha=hashlib.sha256(source).hexdigest()
 parsed=parse_pdf(source)
 r=compare(json.loads(fp.read_text()),json.loads(Path(a.june_notice).read_text()),parsed,sha)
 if hashlib.sha256(fp.read_bytes()).hexdigest()!=pre:
  raise ValueError("Unexpected financial feed change")
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("G13 June 30 original source verified:",r["published_june30_count_original_primary_supported"])
if __name__=="__main__":main()
