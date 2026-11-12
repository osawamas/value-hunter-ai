import json, urllib.request, urllib.error, hashlib, time, re, pathlib
from datetime import datetime, timezone
URLS = {
 "S68_FY2026_results": "https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584",
 "S68_FY2026_release": "https://links.sgx.com/FileOpen/1.%20SGX%20Group%20reports%20FY2026%20net%20profit%20of%20S%24759%20million.ashx?App=Announcement&FileID=898861",
}
out=pathlib.Path("results");out.mkdir(exist_ok=True)
records=[]
for name,url in URLS.items():
 rec={"name":name,"url":url,"tested_at":datetime.now(timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; SGX-financial-validation/0.1)","Accept":"application/pdf"})
  with urllib.request.urlopen(req,timeout=25) as r:
   content=r.read(12*1024*1024+1)
   rec.update(http_status=r.status,content_type=r.headers.get("Content-Type"),bytes=len(content),pdf_magic=content.startswith(b"%PDF-"))
   if len(content)>12*1024*1024:raise ValueError("File over 12MB cap")
   if not content.startswith(b"%PDF-"):raise ValueError("Response is not a PDF")
   rec["sha256"]=hashlib.sha256(content).hexdigest()
   import fitz
   doc=fitz.open(stream=content,filetype="pdf")
   rec["pages"]=len(doc)
   txt="\n".join(p.get_text() for p in doc)
   (out/(name+".txt")).write_text(txt,encoding="utf-8")
   rec["extracted_chars"]=len(txt)
   rec["year_2026_present"]=bool(re.search(r"2026",txt))
   rec["year_2025_present"]=bool(re.search(r"2025",txt))
   rec["extraction_ok"]=bool(len(txt)>1000 and rec["year_2026_present"])
   # No automated investment metric is emitted until column and accounting scope are validated.
 except Exception as e:
  rec["error"]=str(e)
 records.append(rec)
 (out/"report.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(rec,ensure_ascii=False))
