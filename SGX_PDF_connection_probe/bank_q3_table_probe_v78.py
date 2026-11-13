"""v78: bounded issuer PDF rows for precise quarterly bank schema design.

Not an investor data publication. Read Q3 and 9M tables from the actual
trading update, preserving document text order for safe column extraction.
"""
import argparse
from bank_q3_2026_probe_v77 import SOURCES
from official_http_v57 import get_pdf

PAGES={"D05":[7],"O39":[2,4],"U11":[3]}
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--symbol",choices=tuple(PAGES),required=True)
 a=p.parse_args()
 import fitz
 raw=get_pdf(SOURCES[a.symbol]["url"],max_bytes=75_000_000,timeout=90)
 doc=fitz.open(stream=raw,filetype="pdf")
 try:
  for page in PAGES[a.symbol]:
   lines=doc[page-1].get_text("text").splitlines()
   print("BEGIN_BANK_REPORT",a.symbol,page)
   for i,line in enumerate(lines[:300]):
    print(f"REPORT_LINE {i:03d} {line[:180]}")
   print("END_BANK_REPORT",a.symbol,page)
 finally:
  doc.close()
