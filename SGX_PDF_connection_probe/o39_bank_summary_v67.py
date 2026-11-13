"""OCBC (O39) issuer annual FY2025 selected GROUP banking financial highlights.

This is a summary table within OCBC's 2025 annual report; not a direct
verification of the separate audited financial statements. Never promote it
to industrial revenue/margin or ranking without additional checks.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from bank_statements_probe_v66 import SOURCES
from official_http_v57 import get_pdf

SOURCE=SOURCES["O39"]["url"]
VALUES={
    "net_interest_income":("Net interest income",(9150,9755)),
    "total_income":("Total income",(14614,14473)),
    "parent_attributable_profit":("Net profit attributable to equity holders",(7422,7587)),
    "parent_equity":("Equity attributable to equity holders of the Bank",(61768,59316)),
    "total_assets":("Total assets",(675688,625050)),
}

def extract_pair(lines,label,expected):
    matches=[]
    for i,line in enumerate(lines):
        if line.strip().lower()!=label.lower():
            continue
        values=[]
        for token in lines[i+1:i+5]:
            token=token.strip()
            if re.fullmatch(r"[0-9][0-9,]*",token):
                values.append(int(token.replace(",","")))
            elif token in ("(1)","(2)"):
                continue
            else:
                break
        if tuple(values[:2])==expected:
            matches.append(i)
    if len(matches)!=1:
        raise ValueError(f"OCBC issuer summary metric absent or ambiguous {label}: {matches}")
    return {"2025":expected[0],"2024":expected[1]}

def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("OCBC Annual Report not a PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<=97:
            raise ValueError("OCBC annual report too short")
        first=" ".join(doc[i].get_text("text") for i in range(min(35,len(doc)))).lower()
        if "ocbc" not in first and "oversea-chinese" not in first:
            raise ValueError("OCBC issuer name not found")
        page=doc[97]
        text=" ".join(page.get_text("text").lower().split())
        if not ("selected income statement items" in text
                and "selected balance sheet items" in text
                and "2025" in text and "2024" in text):
            raise ValueError("Wrong Group financial summary or period")
        rows={}
        lines=page.get_text("text").splitlines()
        for key,(label,expected) in VALUES.items():
            rows[key]=extract_pair(lines,label,expected)
        for y in ("2025","2024"):
            if rows["total_income"][y] < rows["net_interest_income"][y]:
                raise ValueError("Bank income subtotal inconsistent")
            if rows["total_assets"][y] <= rows["parent_equity"][y]:
                raise ValueError("Bank assets/equity inconsistent")
        return {"symbol":"O39","fiscal_year":2025,
                "scope":"ISSUER_SELECTED_GROUP_FINANCIAL_HIGHLIGHTS",
                "independent_statement_crosscheck":False,
                "unit":"SGD_millions",
                "pdf_page_number":98,
                "metrics":rows,
                "ranking_eligible":False}
    finally:
        doc.close()

def run(output,raw=None,verified_pdf_copy=None):
    out={"symbol":"O39","status":"NOT_VERIFIED",
         "source_url":SOURCE,"pdf_sha256":None,
         "record":None,"error":None}
    try:
        pdf=get_pdf(SOURCE,max_bytes=75_000_000,timeout=90) if raw is None else raw
        out["pdf_sha256"]=hashlib.sha256(pdf).hexdigest()
        out["record"]=parse_pdf(pdf)
        out["status"]="O39_ISSUER_2025_GROUP_FINANCIAL_HIGHLIGHTS_MATCHED"
        if verified_pdf_copy is not None:
            target=Path(verified_pdf_copy)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(pdf)
    except Exception as exc:
        out["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    p.add_argument("--verified-pdf-copy")
    a=p.parse_args()
    r=run(a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None,a.verified_pdf_copy)
    print(r["status"],r["error"])
    raise SystemExit(0 if r["status"]=="O39_ISSUER_2025_GROUP_FINANCIAL_HIGHLIGHTS_MATCHED" else 1)
