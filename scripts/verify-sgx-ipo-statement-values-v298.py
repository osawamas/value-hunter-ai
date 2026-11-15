#!/usr/bin/env python3
"""v298 verify exact fiscal-period statement rows in SHA-pinned original PDFs.
The committed amounts are a reviewed extraction, not computed by guessing a
similarly named pro-forma table, and are never promoted into a quote/rank feed.
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import tempfile
import urllib.request
from urllib.parse import urlsplit
import datetime

ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("v297",ROOT/"scripts/replay-sgx-ipo-financial-pdfs-v297.py")
v297=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v297)

LABELS={
 "revenue":r"^\s*Revenue\s+",
 "gross_profit":r"^\s*Gross profit\s+",
 "profit_for_year":r"^\s*Profit for the (?:financial )?year(?:/period)?\s+",
 "total_equity":r"^\s*Total equity\s+",
 "total_assets":r"^\s*Total assets\s+",
}

def verify_deluge_segment_note(lines, periods):
 """Match the total column of Appendix A, Note 31, for each March year."""
 start=next(i for i,line in enumerate(lines) if re.match(r"^\s*31\.\s+Segment information\s*$",line))
 end=next(i for i in range(start+1,len(lines)) if re.match(r"^\s*32\.\s+Significant related party transactions\s*$",lines[i]))
 for period in periods:
  year=period["period_end"][:4]
  expected=period["segment_operating_result"]
  matches=[]
  for i in range(start,end):
   if lines[i].strip()!=year:
    continue
   section=lines[i+1:i+20]
   revenue_total=f'{period["revenue"]:,}'
   if not any(re.fullmatch(r"\s*External customers\s+.+?\s+"+re.escape(revenue_total)+r"\s*",row)
              for row in section):
    continue
   for row in section:
    match=re.fullmatch(r"\s*Profit from operations\s+.+?\s+([\d,]+)\s*",row)
    if match:
     matches.append(int(match[1].replace(",","")))
  if matches!=[expected]:
   raise ValueError(f"9DC Note 31 FY{year} operating result mismatch: {matches}, expected {expected}")

def values_from_row(line,label,count):
 pattern=LABELS[label]
 if not re.match(pattern,line,re.IGNORECASE):return None
 rest=re.sub(pattern,"",line,count=1,flags=re.IGNORECASE)
 tokens=re.findall(r"(?<!\w)\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?|(?<!\w)\(?-?\d+(?:\.\d+)?\)?",rest)
 if len(tokens)!=count or any("." in x or "(" in x for x in tokens):return None
 return [int(x.replace(",","")) for x in tokens]
def verify_section(text,record):
 lines=text.splitlines()
 if record["symbol"]=="9DC":
  anchor="SELECTED COMBINED FINANCIAL INFORMATION"
  start=next((i for i,x in enumerate(lines) if x.strip()==anchor),-1)
  if start<0:raise ValueError("9DC audited financial section missing")
  end=next((i for i in range(start+1,len(lines)) if lines[i].strip()=="SELECTED PRO FORMA COMBINED FINANCIAL INFORMATION"),-1)
  if end<0 or end-start>450:raise ValueError("Audited/pro forma boundary missing")
  scope=lines[start:end]
  top=" ".join(scope[:24])
  if "Audited" not in top or "FY2024" not in top or "FY2026" not in top:
   raise ValueError("9DC column scope not marked audited FY2024-FY2026")
  periods=record["periods"]
 else:
  anchor="SUMMARY COMBINED STATEMENTS OF PROFIT OR LOSS AND OTHER COMPREHENSIVE"
  start=next((i for i,x in enumerate(lines) if x.strip().startswith(anchor)), -1)
  if start<0:raise ValueError("MIM combined audited/unaudited table missing")
  scope=lines[start:start+210]
  top=" ".join(scope[:22])
  if "Audited" not in top or "Unaudited" not in top or "2023" not in top or "2026" not in top:
   raise ValueError("MIM five-column audited/unaudited scope missing")
  periods=record["periods"]+record["interim"]
 counts={label:0 for label in LABELS}
 for label in LABELS:
  expected=[x[label] for x in periods]
  if any(x is None for x in expected):
   # MIM's balance sheet has four columns (2023, 2024, 2025, 2026-H1),
   # unlike the five-column income statement (which has both H1 years).
   if label not in {"total_equity","total_assets"} or record["symbol"]!="MIM" or [i for i,x in enumerate(expected) if x is None]!=[3]:
    raise ValueError("Missing unexpectedly required financial figure")
   expected=[periods[i][label] for i in [0,1,2,4]]
  for line in scope:
   row=values_from_row(line,label,len(expected))
   if row is not None and row==expected:counts[label]+=1
  if counts[label]==0 and record["symbol"]=="MIM" and label=="profit_for_year":
   # PDF text layout breaks the printed heading into two lines for "Profit
   # for the financial year/period". Require a matching numerical row and
   # explicit nearby profit-for-period heading, not owner-attributable totals.
   number_sequence=r"\s+".join(re.escape(f"{v:,}") for v in expected)
   candidates=[i for i,line in enumerate(scope) if i>0 and
     scope[i-1].strip()=="Profit for the financial" and
     re.match(r"^\s*year/period\s+",line,re.I) and re.search(number_sequence,line)]
   if len(candidates)==1:counts[label]=1
  if counts[label]!=1:raise ValueError(record["symbol"]+" audited scope row mismatch: "+label+
    " expected "+str(expected)+" matched "+str(counts[label]))
 if record["symbol"]=="9DC":
  if record["operating_result_basis"]!="SEGMENT_NOTE_PROFIT_FROM_OPERATIONS":
   raise ValueError("9DC operating result must be labelled as a segment note figure")
  verify_deluge_segment_note(lines,record["periods"])
  counts["segment_operating_result"]=len(record["periods"])
  pro=record["rejected_lookalike_pro_forma"]
  pro_scope=lines[end:end+800]
  for label in ["revenue","gross_profit","profit_for_year"]:
   if not any(values_from_row(line,label,1)==[pro[label]] for line in pro_scope):
    raise ValueError("9DC excluded unaudited pro forma value not corroborated: "+label)
 elif record["operating_result_basis"]!="NO_SEPARATE_OPERATING_PROFIT_SUBTOTAL" or any(
  period["segment_operating_result"] is not None for period in record["periods"]
 ):
  raise ValueError("MIM has no separately reported operating profit subtotal")
 return {"symbol":record["symbol"],"fiscal_years":len(record["periods"]),
  "interim_periods":len(record.get("interim",[])),
  "rows_confirmed":counts,
  "audit_scope_safe":True,"pro_forma_investment_figures_used":False,
  "rank_eligible":False}

def download(url, sha256, size):
 original=urlsplit(url)
 if original.scheme!="https" or original.netloc not in {"links.sgx.com","miequipment.listedcompany.com"}:
  raise ValueError("Unexpected PDF source")
 req=urllib.request.Request(url,headers={
  "User-Agent":"VALUE-HUNTER-AI-source-validation/1.0 (+https://github.com/osawamas/value-hunter-ai)",
  "Accept":"application/pdf"})
 with urllib.request.urlopen(req,timeout=45) as reply:
  final=urlsplit(reply.geturl())
  if (final.scheme,final.netloc)!=(original.scheme,original.netloc):
   raise ValueError("Unexpected redirect to another host")
  blob=reply.read(v297.MAX_BYTES+1)
 if hashlib.sha256(blob).hexdigest()!=sha256 or len(blob)!=size:
  raise ValueError("Verified PDF checksum drift")
 return blob

def original_text(source, pages=()):
 raw=download(source["url"],source["sha256"],source["bytes"])
 with tempfile.TemporaryDirectory() as temp:
  pdf=pathlib.Path(temp)/"original.pdf"
  pdf.write_bytes(raw)
  proc=subprocess.run(["pdftotext","-layout",*pages,str(pdf),"-"],capture_output=True,timeout=65,check=True)
 return proc.stdout.decode("utf-8",errors="replace")

def manifest_text(source):
 return original_text({"url":source["url"],"sha256":source["github_actions_confirmed_sha256"],
  "bytes":source["github_actions_confirmed_original_bytes"]})

def verify_mim_business_update(source, update):
 if (update["source_pdf_url"]!=source["url"]
     or update["audit_status"]!="UNAUDITED_ISSUER_UPDATE"
     or update["period_end"]!="2026-09-30"
     or update["prior_year_same_period_revenue"] is not None):
  raise ValueError("MIM 9M2026 source or comparison period mismatch")
 content=" ".join(manifest_text(source).split())
 expected=[
  "nine months ended 30 September 2026",
  f'Revenue reached US${update["revenue_usd_millions"]:.1f} million in 9M2026',
  f'gross profit margin of {update["gross_margin_percent"]:.1f}%',
  f'adjusted profit after tax of US${update["adjusted_pat_usd_millions"]:.1f} million in 9M2026',
  f'3Q2026 revenue growing {update["q3_revenue_qoq_percent"]:.1f}% quarter-on-quarter',
 ]
 if any(row not in content for row in expected):
  raise ValueError("MIM 9M2026 issuer figures did not match original release")
 presentation=update["presentation_source"]
 deck=original_text(presentation,("-f","14","-l","14"))
 if not re.search(r"Adjustments to PAT[\s\S]*?FY2023\s+FY2024\s+FY2025\s+9MFY26",deck):
  raise ValueError("MIM PAT adjustment table is absent")
 for label, field in [("Revenue","revenue_usd_millions"),("PAT","pat_usd_millions"),("Adj. PAT","adjusted_pat_usd_millions")]:
  pattern=rf"^\s*{re.escape(label)}(?:\s+\d+\.\d+){{3}}\s+{re.escape(f'{update[field]:.1f}')}\s*$"
  if not re.search(pattern,deck,re.MULTILINE):
   raise ValueError(f"MIM 9M2026 presentation row mismatch: {label}")
 segment=update["parent_segment_comparison"]
 if segment["basis"]!="MITB_SMBU_EXTERNAL_CUSTOMER_REVENUE" or segment["currency"]!="MYR":
  raise ValueError("Mi Technovation SMBU comparison scope mismatch")
 tables=original_text(segment["source"],("-f","13","-l","15")).split("\f")
 for label,year,page in [("prior",2025,15),("current",2026,13)]:
  if segment[f"{label}_period_end"]!=f"{year}-09-30":
   raise ValueError("Mi Technovation SMBU comparison period mismatch")
  table=tables[page-13]
  heading=rf"Results for the financial period ended 30 September {year}[^\n]*\n\s*SEBU\s+SMBU"
  values=rf"^\s*Revenue from external customers\s+[\d,]+\s+{segment[f'{label}_revenue_thousands']:,}\s+"
  if not re.search(heading,table) or not re.search(values,table,re.MULTILINE):
   raise ValueError(f"Mi Technovation 9M{year} SMBU external revenue mismatch")
 print("MIM VERIFIED issuer release, reported and adjusted PAT, and separate parent segment revenue")
 return {"original_pdf_sha256":source["github_actions_confirmed_sha256"],
  "period_end":update["period_end"],"audit_status":update["audit_status"],
  "prior_year_same_period_revenue":None,"values_confirmed":5,
  "issuer_presentation_sha256":presentation["sha256"],"parent_segment_comparison":segment}

def main():
 manifest=json.loads((ROOT/"docs/data/sgx-ipo-financial-documents-v297.json").read_text())
 sources=v297.validate_manifest(manifest)
 financial=json.loads((ROOT/"docs/data/sgx-ipo-audited-historical-v298.json").read_text())
 if financial["schema_version"]!="sgx-ipo-audited-historical-financials-v298" or financial["ranking_eligible_count"]!=0 or financial["ranking_enabled"] is not False:
  raise ValueError("Research schema/ranking state changed")
 out=[]
 for record in financial["issuers"]:
  source=next(x for x in sources if x["symbol"]==record["symbol"] and x["document_type"]=="REGISTERED_IPO_PROSPECTUS")
  if record["source_pdf_sha256"]!=source["github_actions_confirmed_sha256"] or record["source_pdf_url"]!=source["url"]:
   raise ValueError("Audited statement evidence mismatch")
  result=verify_section(manifest_text(source),record)
  if record["symbol"]=="MIM":
   update_source=next(x for x in sources if x["document_type"]=="ISSUER_9M2026_BUSINESS_UPDATE")
   result["business_update"]=verify_mim_business_update(update_source,record["business_update"])
  result["original_pdf_sha256"]=source["github_actions_confirmed_sha256"]
  out.append(result)
  print(f'{result["symbol"]} VERIFIED original SHA and rows {result["rows_confirmed"]}; '
        f'{result["fiscal_years"]} annual and {result["interim_periods"]} interim periods')
 report={"schema_version":"sgx-ipo-original-audited-financial-reconciliation-v298",
  "checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "sources":out,"all_source_tables_reconciled":len(out)==2,
  "pro_forma_not_used":True,"live_market_data_licence_verified":False,
  "independent_current_financial_reverification":False,"ranking_eligible_count":0}
 dest=ROOT/"build/research/sgx-ipo-audited-reconciliation-v298.json"
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
