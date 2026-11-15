#!/usr/bin/env python3
"""v298 locate compact statement table rows in the three byte-pinned SGX originals.
Read-only research artifact, not finance feed, and never publish wholesale PDF text.
"""
import importlib.util,json,pathlib,subprocess,tempfile,urllib.request,re,hashlib,datetime
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("v297",ROOT/"scripts/replay-sgx-ipo-financial-pdfs-v297.py")
v297=importlib.util.module_from_spec(spec);spec.loader.exec_module(v297)
LABELS={
 "Revenue":r"^\s*(?:Revenue|Total revenue)\s+",
 "Gross profit":r"^\s*Gross profit\s+",
 "Profit after tax":r"^\s*(?:Profit for the (?:financial )?year(?:/period)?|Profit for the year(?:/period)?|Profit attributable to owners|Net profit)\s+",
 "Total equity":r"^\s*(?:Total equity|Total shareholders. equity|Total equity attributable to owners)\s+",
 "Operating profit":r"^\s*(?:Operating profit|Profit from operations|Results from operating activities)\s+"
}
def row_candidates(text):
 lines=text.splitlines();rows=[]
 for i,line in enumerate(lines):
  for key,pattern in LABELS.items():
   if re.search(pattern,line,re.I):
    digits=re.findall(r"(?<![A-Za-z])\(?-?\d[\d,]*(?:\.\d+)?\)?",line)
    rows.append({"label":key,"text":line.strip()[:180],
     "numeric_tokens":digits[:8],"nearby_previous":lines[i-1].strip()[:100] if i else "",
     "position_line":i+1})
 return rows
def main():
 sources=v297.validate_manifest(json.loads((ROOT/"docs/data/sgx-ipo-financial-documents-v297.json").read_text()))
 files=[]
 for source in sources:
  req=urllib.request.Request(source["url"],headers={"User-Agent":"VALUE-HUNTER-AI-source-validation/1.0 (+https://github.com/osawamas/value-hunter-ai)","Accept":"application/pdf"})
  with urllib.request.urlopen(req,timeout=45) as response:raw=response.read(v297.MAX_BYTES+1)
  assert hashlib.sha256(raw).hexdigest()==source["github_actions_confirmed_sha256"]
  assert len(raw)==source["github_actions_confirmed_original_bytes"]
  with tempfile.TemporaryDirectory() as tmp:
   inp=pathlib.Path(tmp)/"original.pdf";inp.write_bytes(raw)
   extracted=subprocess.run(["pdftotext","-layout",str(inp),"-"],capture_output=True,check=True,timeout=60).stdout.decode("utf8",errors="replace")
  rows=row_candidates(extracted)
  if source["document_type"]=="REGISTERED_IPO_PROSPECTUS":
   seq=extracted.splitlines()
   positions=[5216,5506] if source["symbol"]=="9DC" else [2051,4681]
   for pos in positions:
    print("v298-context "+source["symbol"]+" lines "+str(pos-14)+".."+str(pos+14))
    for idx in range(max(0,pos-15),min(len(seq),pos+14)):
     print("v298-context-line "+str(idx+1)+" "+seq[idx][:190])
  files.append({"symbol":source["symbol"],"type":source["document_type"],
   "source_sha256":source["github_actions_confirmed_sha256"],
   "candidate_line_count":len(rows),"rows":rows[:140],
   "raw_extraction_contains_multiple_tables":True,
   "automatically_selected_financial_table":False,
   "ranking_eligible":False})
  print("v298 "+source["symbol"]+" "+source["document_type"]+" candidate_rows="+str(len(rows)))
  for row in rows[:22]:print("v298-row "+json.dumps(row,ensure_ascii=False))
 report={"schema_version":"sgx-ipo-table-discovery-v298","checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_pdf_hard_hash_matched":True,"files":files,
  "figures_verified_by_table_selection":False,"financial_feed_mutated":False,"ranking_eligible_count":0}
 target=ROOT/"build/research/sgx-ipo-financial-table-discovery-v298.json";target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
