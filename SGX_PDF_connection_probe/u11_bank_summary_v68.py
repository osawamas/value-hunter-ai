"""UOB (U11) FY2025 annual issuer five-year BANK financial summary.

Unlike audited balance sheet, total assets/equity are rounded SGD billions.
Do not promote approximated balance amounts to precise PBR or combine them with
SGD_millions without explicit scale and rounding uncertainty.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from official_http_v57 import get_pdf
from bank_statements_probe_v66 import SOURCES

SOURCE=SOURCES["U11"]["url"]
EXPECTED={
    "total_income":("Total income",(9789,11575,13932,14294,13808)),
    "total_expenses":("Total expenses",(4313,5281,6217,6310,6157)),
    "operating_profit":("Operating profit",(5476,6294,7715,7984,7651)),
    "parent_net_profit":("Net profit after tax",(4075,4573,5711,6045,4682)),
    "total_assets_rounded_billions":("Total assets",(459,504,524,538,572)),
    "parent_equity_rounded_billions":("Shareholders' equity",(43,43,46,50,51)),
}
BALANCE={"total_assets_rounded_billions","parent_equity_rounded_billions"}


def read_row(lines,label,expected):
    hits=[]
    for i,line in enumerate(lines):
        t=line.strip().lower().replace("’","'")
        if t!=label.lower() and not (t.startswith(label.lower()) and re.search(r"\b[ab]\b",t[len(label):])):
            continue
        nums=[]
        for v in lines[i+1:i+8]:
            v=v.strip()
            if re.fullmatch(r"[0-9][0-9,]*",v):
                nums.append(int(v.replace(",","")))
            else:break
        if tuple(nums[:5])==expected:
            hits.append(i)
    if len(hits)!=1:
        raise ValueError(f"UOB Group five-year bank summary row missing/ambiguous {label}: {hits}")
    return {"2025":expected[-1],"2024":expected[-2]}


def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("UOB annual source is not PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<=44:
            raise ValueError("UOB PDF too short")
        preface=" ".join(doc[i].get_text("text") for i in range(min(35,len(doc)))).lower()
        if not ("uob" in preface or "united overseas bank" in preface):
            raise ValueError("UOB Group issuer identity absent")
        page=doc[44]
        lines=page.get_text("text").splitlines()
        txt=" ".join(lines).lower()
        if not ("five-year group financial summary" in txt
                and "selected income statement items" in txt
                and "selected balance sheet items" in txt
                and "2021" in txt and "2025" in txt):
            raise ValueError("UOB Group five-year summary scope absent")
        metrics={key:read_row(lines,label,expected)
                 for key,(label,expected) in EXPECTED.items()}
        for yr in ("2025","2024"):
            if metrics["total_income"][yr]-metrics["total_expenses"][yr]!=metrics["operating_profit"][yr]:
                raise ValueError("UOB Group operating profit arithmetic mismatch")
            if metrics["total_assets_rounded_billions"][yr]<=metrics["parent_equity_rounded_billions"][yr]:
                raise ValueError("UOB rounded assets/equity inconsistent")
        return {"symbol":"U11","fiscal_year":2025,
                "scope":"ISSUER_FIVE_YEAR_GROUP_SUMMARY_NOT_DIRECT_AUDITED_STATEMENTS",
                "financials_unit":"SGD_millions",
                "rounded_balance_unit":"SGD_billions_rounded",
                "pdf_page_number":45,
                "metrics":metrics,
                "current_market_data_available":False,
                "independent_verification":False,
                "ranking_eligible":False}
    finally:doc.close()


def run(output,raw=None):
    result={"symbol":"U11","status":"NOT_VERIFIED","source_url":SOURCE,
            "pdf_sha256":None,"record":None,"error":None}
    try:
        data=get_pdf(SOURCE,max_bytes=75_000_000,timeout=90) if raw is None else raw
        result["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        result["record"]=parse_pdf(data)
        result["status"]="U11_FY2025_ISSUER_FIVE_YEAR_BANK_SUMMARY_MATCHED"
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    a=p.parse_args()
    result=run(a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(result["status"],result["error"])
    raise SystemExit(0 if result["status"]=="U11_FY2025_ISSUER_FIVE_YEAR_BANK_SUMMARY_MATCHED" else 1)
