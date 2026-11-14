"""v145: direct PDF authenticity of three OCBC 3Q26 SGX attachments.

Only records byte hashes, PDF page counts, extractability and issuer/period
markers. It does NOT assert bank income or profit figures are validated.
"""
import argparse,hashlib,json
from pathlib import Path
from urllib.request import Request,urlopen
from sgx_ocbc_q3_original_v143 import ATTACHMENTS

def audit(links,fetcher):
 if (links.get("status")!="SGX_OCBC_Q3_ATTACHMENT_LINKS_RESEARCHED" or
     links.get("record",{}).get("schema_version")!="sgx-ocbc-q3-official-attachment-links-v144" or
     links["record"].get("all_three_verified_attachment_links") is not True):
  raise ValueError("Three official links missing")
 import fitz
 rows=[]
 for attachment in links["record"]["attachments"]:
  name=attachment.get("filename");url=attachment.get("resolved_official_link")
  if name not in ATTACHMENTS or attachment.get("unique_direct_sgx_link") is not True or not url:
   raise ValueError("Unverified filename/URL")
  raw=fetcher(url)
  if not isinstance(raw,bytes) or not raw.startswith(b"%PDF") or len(raw)>12_000_000:
   raise ValueError("No genuine PDF: "+name)
  doc=fitz.open(stream=raw,filetype="pdf")
  try:
   pages=len(doc)
   samples=[p.get_text("text") for p in doc]
  finally:doc.close()
  extracted=" ".join(" ".join(samples).split()).lower()
  if pages<1 or pages>100 or "ocbc" not in extracted:
   raise ValueError("Wrong or empty text PDF: "+name)
  if not any(s in extracted for s in ("2026","3q26","third quarter")):
   raise ValueError("Quarterly period not visible in PDF text")
  rows.append({
   "filename":name,"official_sgx_original_url":url,
   "sha256":hashlib.sha256(raw).hexdigest(),
   "bytes":len(raw),"page_count":pages,
   "extracted_text_chars":len(extracted),
   "issuer_and_2026_period_text_observed":True,
   "individual_numerical_metrics_parsed_and_verified":False})
 if len(rows)!=3 or len(set(x["filename"] for x in rows))!=3:
  raise ValueError("Three distinct attachments not verified")
 return {"schema_version":"sgx-ocbc-q3-pdf-originals-v145",
   "symbol":"O39","financial_period_end":"2026-09-30",
   "original_attachment_count":3,"records":rows,
   "financial_metrics_independently_reperformed":False,
   "current_quote_or_shares_verified":False,"ranking_eligible":False}

def fetch_pdf(url):
 if not url.startswith("https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/"):
  raise ValueError("Not expected SGX original")
 request=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0 OCBC-PDF-audit","Accept":"application/pdf"})
 with urlopen(request,timeout=35) as res:
  if res.geturl()!=url or "pdf" not in res.headers.get("Content-Type","").lower():
   raise ValueError("Original SGX PDF not returned")
  b=res.read(12_000_001)
 return b
def main():
 p=argparse.ArgumentParser();p.add_argument("--links",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 out={"schema_version":"sgx-ocbc-q3-pdfs-probe-v145","status":"NOT_VERIFIED","record":None,"error":None}
 try:
  links=json.loads(Path(a.links).read_text())
  out["record"]=audit(links,fetch_pdf)
  out["status"]="SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED"
 except Exception as e:
  out["error"]=type(e).__name__+": "+str(e)[:280]
  try:
   manifest=json.loads(Path(a.links).read_text())
   diag=[]
   for item in manifest.get("record",{}).get("attachments",[]):
    url=item.get("resolved_official_link")
    if not url:continue
    try:
     req=Request(url,headers={"User-Agent":"Mozilla/5.0 VALUE-HUNTER-AI/1.0","Accept":"application/pdf"})
     with urlopen(req,timeout=20) as resp:
      sample=resp.read(128)
      diag.append({"filename":item.get("filename"),"url_host":resp.geturl().split("/")[2],
       "final_path":"/"+"/".join(resp.geturl().split("/")[3:])[:180],
       "content_type":resp.headers.get("Content-Type",""),
       "sample_pdf_magic":sample.startswith(b"%PDF"),
       "sample_html_magic":b"<html" in sample.lower() or b"<!doctype" in sample.lower()})
    except Exception as inner:
     diag.append({"filename":item.get("filename"),"error":type(inner).__name__+": "+str(inner)[:140]})
   out["response_diagnostics"]=diag
  except Exception as diag_error:
   out["response_diagnostics_error"]=type(diag_error).__name__+": "+str(diag_error)[:140]
 f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
 f.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(out["status"],out["error"])
if __name__=="__main__":main()
