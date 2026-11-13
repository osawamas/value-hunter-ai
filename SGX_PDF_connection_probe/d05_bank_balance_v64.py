"""DBS Group D05 consolidated bank balance sheet FY2025/FY2024.

Do not confuse DBS GROUP (D05) with DBS Bank Ltd or standalone Company.
Balance sheet metrics retain bank scope, SGD_millions, audited issuer provenance
and are not promoted to generic industrial ranking or price-based valuation.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from d05_shareholding_v62 import SOURCE, fetch

EXPECTED={
    "total_assets":(897488,827219),
    "total_liabilities":(828572,758386),
    "net_assets":(68916,68833),
    "parent_shareholders_funds":(68867,68786),
    "non_controlling_interests":(49,47),
    "total_equity":(68916,68833),
    "customer_loans":(445011,430594),
}
LABELS={
    "total_assets":"Total assets",
    "total_liabilities":"Total liabilities",
    "net_assets":"Net assets",
    "parent_shareholders_funds":"Shareholders' funds",
    "non_controlling_interests":"Non-controlling interests",
    "total_equity":"Total equity",
    "customer_loans":"Loans and advances to customers",
}


def pair_after_label(lines,label,expected):
    found=[]
    for i,line in enumerate(lines):
        if line.strip().lower()!=label.lower():
            continue
        values=[]
        # A table's Group columns precede Company columns. Ignore note number
        # only if explicitly demonstrated by the next two expected numbers.
        for nextline in lines[i+1:i+8]:
            token=nextline.strip()
            if re.fullmatch(r"[0-9][0-9,]*",token):
                values.append(int(token.replace(",","")))
            elif token in ("–","—","-"):
                continue
            else:
                break
        if tuple(values[:2])==expected:
            found.append(i)
        elif len(values)>=3 and tuple(values[1:3])==expected and values[0]<100:
            found.append(i)
    if len(found)!=1:
        raise ValueError(f"DBS Group balance row missing or ambiguous: {label} {found}")
    return {"2025":expected[0],"2024":expected[1]}


def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("DBS balance PDF invalid")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<60:
            raise ValueError("DBS report shorter than audited financial statements")
        preface=" ".join(doc[i].get_text("text") for i in range(min(len(doc),35)))
        if "DBS" not in preface: raise ValueError("DBS issuer identity not found")
        candidates=[]
        for index in range(55,min(78,len(doc))):
            page=doc[index]
            lines=page.get_text("text").splitlines()
            full=" ".join(lines).lower()
            if not ("balance sheets" in full and "31 december 2025" in full
                    and "the group" in full and "the company" in full
                    and "in $ millions" in full and "2024" in full):
                continue
            if "dbs group holdings ltd and its subsidiaries" not in full:
                raise ValueError("Wrong legal reporting entity")
            metrics={key:pair_after_label(lines,label,EXPECTED[key])
                     for key,label in LABELS.items()}
            for yr in ("2025","2024"):
                get=lambda key:metrics[key][yr]
                if get("total_assets")-get("total_liabilities")!=get("net_assets"):
                    raise ValueError("DBS assets minus liabilities mismatch")
                if get("parent_shareholders_funds")+get("non_controlling_interests")!=get("total_equity"):
                    raise ValueError("DBS Group parent+NCI equity mismatch")
                if get("net_assets")!=get("total_equity"):
                    raise ValueError("DBS reported net assets not equal equity")
            candidates.append({"pdf_page_number":index+1,"metrics":metrics})
        if len(candidates)!=1:
            raise ValueError(f"Expected one DBS Group balance sheet, found {len(candidates)}")
        return {"symbol":"D05","fiscal_year":2025,
                "unit":"SGD_millions","reporting_entity":"DBS Group Holdings Ltd and Subsidiaries",
                "metric_schema":"BANKING_BALANCE_V64_NOT_INDUSTRIAL",
                "pdf_page_number":candidates[0]["pdf_page_number"],
                "metrics":candidates[0]["metrics"],
                "ranking_eligible":False,"independent_verification":False}
    finally:
        doc.close()


def run(output,raw=None):
    record={"symbol":"D05","source_url":SOURCE,"pdf_sha256":None,
            "status":"NOT_VERIFIED","record":None,"error":None}
    try:
        data=fetch() if raw is None else raw
        record["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        record["record"]=parse_pdf(data)
        record["status"]="BANK_GROUP_BALANCE_2025_2024_ISSUER_PDF_RECONCILED"
    except Exception as exc:
        record["error"]=f"{type(exc).__name__}: {str(exc)[:330]}"
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return record


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    a=p.parse_args()
    data=run(a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(data["status"],data["error"])
    raise SystemExit(0 if data["status"]=="BANK_GROUP_BALANCE_2025_2024_ISSUER_PDF_RECONCILED" else 1)
