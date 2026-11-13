"""DBS Group D05 FY2025 issuer annual report banking-specific income statement.

Bank revenue is reported as total income. Never alias it to industrial operating
revenue or compute industrial operating margin. This remains a standalone
audit artifact until appropriate bank-specific valuation integration exists.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from d05_shareholding_v62 import SOURCE, fetch

EXPECTED={
    "net_interest_income":(14500,14424),
    "non_interest_income":(8400,7873),
    "total_income":(22900,22297),
    "total_expenses":(9349,9018),
    "allowances_for_credit_losses":(791,622),
    "net_profit":(10934,11290),
    "profit_attributable_to_parent":(10933,11289),
    "non_controlling_profit":(1,1),
}
# A single source document, same issuer, two years and a known income statement.
ROW={
    "net_interest_income":"Net interest income",
    "non_interest_income":"Non-interest income",
    "total_income":"Total income",
    "total_expenses":"Total expenses",
    "allowances_for_credit_losses":"Allowances for credit and other losses",
    "net_profit":"Net profit",
    "profit_attributable_to_parent":"Shareholders of the parent",
    "non_controlling_profit":"Non-controlling interests",
}


def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Not a DBS issuer PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<58:
            raise ValueError("DBS annual report missing statement pages")
        intro=" ".join(doc[i].get_text("text") for i in range(min(35,len(doc))))
        if "DBS" not in intro:
            raise ValueError("DBS issuer identity missing")
        page=doc[57]
        text=" ".join(page.get_text("text").split())
        if not ("DBS Group Holdings Ltd and its Subsidiaries" in text
                and "Consolidated income statement" in text
                and "31 December 2025" in text
                and "2024" in text and "2025" in text
                and "In $ millions" in text):
            raise ValueError("DBS Group income scope, reporting period or unit not found")
        lines=page.get_text("text").splitlines()
        # Only the consolidated INCOME statement; page also includes comprehensive
        # income. Stop before second statement to avoid repeated 'Shareholders'.
        lower=[x.lower() for x in lines]
        try:
            cutoff=next(i for i,x in enumerate(lower) if "consolidated statement of comprehensive income" in x)
            lines=lines[:cutoff]
        except StopIteration:
            pass
        matches={}
        for key,label in ROW.items():
            hits=[]
            for i,line in enumerate(lines):
                if line.strip().lower()!=label.lower():
                    continue
                tail=[x.strip() for x in lines[i+1:i+5]]
                if (len(tail)>=3 and re.fullmatch(r"\d{1,2}",tail[0])
                        and all(re.fullmatch(r"[0-9][0-9,]*",v) for v in tail[1:3])
                        and tuple(int(v.replace(",","")) for v in tail[1:3])==EXPECTED[key]):
                    tail=tail[1:]
                if len(tail)<2:
                    continue
                if not all(re.fullmatch(r"[0-9][0-9,]*",v) for v in tail[:2]):
                    continue
                values=tuple(int(v.replace(",","")) for v in tail[:2])
                if values==EXPECTED[key]:
                    hits.append((i,values))
            if len(hits)!=1:
                raise ValueError(f"DBS income row missing/ambiguous {key}: {hits}")
            matches[key]={"2025":hits[0][1][0],"2024":hits[0][1][1],
                          "pdf_page_number":58,"extraction":"ISSUER_PDF_ROW_REGRESSION_MATCHED"}
        for year in ("2025","2024"):
            get=lambda k:matches[k][year]
            if get("net_interest_income")+get("non_interest_income")!=get("total_income"):
                raise ValueError("DBS bank total income arithmetic mismatch")
            if get("profit_attributable_to_parent")+get("non_controlling_profit")!=get("net_profit"):
                raise ValueError("DBS parent/net profit reconciliation failed")
        return {"symbol":"D05","fiscal_year":2025,"currency":"SGD","unit":"SGD_millions",
                "statement":"DBS Group consolidated income statement",
                "industry_metric_schema":"BANKING_INCOME_V63_NOT_INDUSTRIAL",
                "pdf_page_number":58,"metrics":matches,
                "independent_verification":False,"ranking_eligible":False}
    finally:
        doc.close()


def run(output,raw=None):
    record={"symbol":"D05","status":"NOT_VERIFIED","source_url":SOURCE,
            "pdf_sha256":None,"record":None,"error":None}
    try:
        data=fetch() if raw is None else raw
        record["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        record["record"]=parse_pdf(data)
        record["status"]="BANK_CONSOLIDATED_INCOME_2025_2024_ISSUER_PDF_MATCHED"
    except Exception as exc:
        record["error"]=f"{type(exc).__name__}: {str(exc)[:350]}"
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return record

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    a=p.parse_args()
    result=run(a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(result["status"],result["error"])
    raise SystemExit(0 if result["status"]=="BANK_CONSOLIDATED_INCOME_2025_2024_ISSUER_PDF_MATCHED" else 1)
