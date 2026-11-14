"""v121: SGX original Genting Singapore 3Q26 business update, unaudited risks.

The quarterly figures are management-account, unaudited and unreviewed.
Do not combine with older audited full-year earnings for PER promotion.
"""
import argparse,hashlib,json,re,subprocess,tempfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

URL="https://links.sgx.com/FileOpen/Q3%202026%20GENS%20Quarterly%20Business%20Overview.ashx?App=Announcement&FileID=911200"
REF="SG261112OTHRSMFB"

def parse_text(content,sha):
 if not isinstance(content,str) or not 100<len(content)<100000:
  raise ValueError("PDF text absent or garbled")
 if "Genting Singapore Limited" not in content or "QUARTERLY BUSINESS OVERVIEW" not in content:
  raise ValueError("Incorrect SGX quarter document")
 if not re.search(r"three months ended\s+30 September 2026",content,re.I):
  raise ValueError("Wrong financial period")
 def row(label):
  match=re.findall(r"(?im)^\s*"+re.escape(label)+r"\s+([0-9,]+)\s+([0-9,]+)\s+\(?\d+\)?\s+([0-9,]+)",content)
  if len(match)!=1:
   raise ValueError("Missing/ambiguous quarterly row "+label)
  return tuple(int(y.replace(",","")) for y in match[0])
 revenue=row("Total Revenue")
 profit=row("Net profit after taxation")
 if revenue!=(566096,649790,595951) or profit!=(54731,94618,90884):
  raise ValueError("New actual report differs from pinned Q3 values")
 if not re.search(r"not been audited nor reviewed",content,re.I):
  raise ValueError("Unaudited disclaimer absent")
 if revenue[1]<=0 or profit[1]<=0:
  raise ValueError("Invalid reference period")
 return {
  "status":"SGX_PRIMARY_2026Q3_UNAUDITED_BUSINESS_UPDATE",
  "source_url":URL,"source_pdf_sha256":sha,
  "announcement_reference_from_issuer_news_page":REF,
  "quarter_end_date":"2026-09-30",
  "revenue_2026q3_sgd_thousands":revenue[0],
  "revenue_2025q3_sgd_thousands":revenue[1],
  "net_profit_after_tax_2026q3_sgd_thousands":profit[0],
  "net_profit_after_tax_2025q3_sgd_thousands":profit[1],
  "revenue_yoy_pct":round((revenue[0]/revenue[1]-1)*100,2),
  "net_profit_yoy_pct":round((profit[0]/profit[1]-1)*100,2),
  "financials_audited":False,
  "financials_reviewed":False,
  "annual_profit_period_compatible_for_repricing":False,
  "older_fy_per_cannot_be_described_as_current":True,
  "shares_or_quote_validated":False,
  "ranking_eligible":False
 }

def fetch():
 req=Request(URL,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 official-evidence",
                          "Accept":"application/pdf"})
 with urlopen(req,timeout=30) as r:
  if r.geturl()!=URL or "pdf" not in r.headers.get("Content-Type","").lower():
   raise ValueError("Source not a direct SGX PDF")
  content=r.read(3_000_001)
 if not content.startswith(b"%PDF") or len(content)>3_000_000:
  raise ValueError("Bad PDF magic or length")
 return content

def extract_pdf(raw):
 with tempfile.TemporaryDirectory() as d:
  pdf=Path(d)/"original.pdf"
  pdf.write_bytes(raw)
  cmd=subprocess.run(["pdftotext","-layout",str(pdf),"-"],
                     capture_output=True,text=True,timeout=30,check=True)
  return cmd.stdout

def run(path):
 z={"schema_version":"sgx-g13-2026q3-original-v121",
    "attempted_at_utc":datetime.now(timezone.utc).isoformat(),
    "source_url":URL,"status":"NOT_VERIFIED","record":None,"error":None}
 try:
  b=fetch()
  z["record"]=parse_text(extract_pdf(b),hashlib.sha256(b).hexdigest())
  z["status"]=z["record"]["status"]
 except Exception as e:
  z["error"]=type(e).__name__+": "+str(e)[:300]
  try:
   raw=fetch()
   content=extract_pdf(raw)
   z["pdf_content_debug"]={
      "text_length":len(content),
      "row_lines":[line.strip()[:240] for line in content.splitlines()
                   if any(term in line.lower() for term in
                          ("total revenue","net profit after taxation","not been audited"))][:12]}
  except Exception as debug_error:
   z["pdf_content_debug_error"]=type(debug_error).__name__+": "+str(debug_error)[:180]
 target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(z,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return z

if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",required=True)
 p=a.parse_args();x=run(p.output);print(x["status"],x["error"])
