"""Audited consolidated bank statements in FY2025 issuer annual PDFs.

The table is Group 2025/2024 first, followed by standalone Bank columns.
Read only Group columns. Expected issuer numbers are regression assertions,
not substitutes for PDF extraction; reject layout drift, duplicates, and
unbalanced totals. No market quote, PER/PBR or ranking promotion.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from bank_statements_probe_v66 import SOURCES
from official_http_v57 import get_pdf

VALUES={
 "O39":{
    "pages":(125,127),
    "income":{
        "net_interest_income":("Net interest income",(9150,9755)),
        "non_interest_income":("Non-interest income",(5464,4718)),
        "total_income":("Total income",(14614,14473)),
        "total_operating_expenses":("Total operating expenses",(-5882,-5742)),
        "parent_profit":("Equity holders of the Bank",(7422,7587)),
        "non_controlling_profit":("Non-controlling interests",(138,161)),
        "profit_for_year":("Profit for the year",(7560,7748)),
    },
    "balance":{
        "share_capital":("Share capital",(17887,18096)),
        "other_equity_instruments":("Other equity instruments",(1698,1698)),
        "capital_reserves":("Capital reserves",(765,830)),
        "fair_value_reserves":("Fair value reserves",(749,313)),
        "revenue_reserves":("Revenue reserves",(40669,38379)),
        "subsidiary_equity":("Other equity instruments issued by subsidiary",(676,0)),
        "non_controlling_equity":("Non-controlling interests",(1126,1064)),
        "total_equity":("Total equity",(63570,60380)),
        "total_liabilities":("Total liabilities",(612118,564670)),
        "total_assets":("Total equity and liabilities",(675688,625050)),
    },
 },
 "U11":{
    "pages":(137,139),
    "income":{
        "net_interest_income":("Net interest income",(9355,9674)),
        "non_interest_income":("Non-interest income",(4453,4620)),
        "total_income":("Total operating income",(13808,14294)),
        "total_operating_expenses":("Total operating expenses",(6157,6310)),
        "profit_before_allowances":("Operating profit before allowance and amortisation",(7651,7984)),
        "parent_profit":("Equity holders of the Bank",(4682,6045)),
        "non_controlling_profit":("Non-controlling interests",(13,14)),
        "profit_for_year":("Profit for the financial year",(4695,6059)),
    },
    "balance":{
        "share_capital":("Share capital and other capital",(7600,7709)),
        "retained_earnings":("Retained earnings",(35060,34834)),
        "other_reserves":("Other reserves",(8588,7190)),
        "parent_equity":("Equity attributable to equity holders of the Bank",(51248,49733)),
        "non_controlling_equity":("Non-controlling interests",(245,224)),
        "total_equity":("Total equity",(51493,49957)),
        "total_liabilities":("Total liabilities",(520568,487707)),
        "total_assets":("Total equity and liabilities",(572061,537664)),
    },
 },
}

def parse_group_row(lines,label,expected):
    """Extract Group pair, ignoring optional standalone note number."""
    hits=[]
    pattern=re.compile(r"^[-+]?[0-9][0-9,]*$|^\([0-9][0-9,]*\)$|^[–—−-]$")
    for idx,line in enumerate(lines):
        if " ".join(line.lower().split())!=" ".join(label.lower().split()):
            continue
        tokens=[]
        for word in lines[idx+1:idx+8]:
            word=word.strip()
            if not pattern.fullmatch(word):
                break
            tokens.append(word)
        def amount(tok):
            if tok in ("–","—","−","-"):
                return 0
            if tok.startswith("("):
                return -int(tok[1:-1].replace(",",""))
            return int(tok.replace(",",""))
        values=[amount(v) for v in tokens]
        if values[:2]==list(expected):
            hits.append({"line":idx,"note_column":False,"read":values[:2]})
        elif (len(values)>=3 and values[0]<=50 and
              values[1:3]==list(expected)):
            hits.append({"line":idx,"note_column":True,"read":values[1:3]})
    if len(hits)!=1:
        raise ValueError(f"Audited Group row missing/ambiguous: {label}, count={len(hits)}")
    return {"2025":hits[0]["read"][0],"2024":hits[0]["read"][1]}

def parse_pdf(symbol,raw):
    import fitz
    if symbol not in VALUES:
        raise ValueError("Unsupported Group reporting issuer")
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid audited report PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        income_page,balance_page=VALUES[symbol]["pages"]
        if len(doc)<balance_page:
            raise ValueError("Audited pages missing")
        intro=" ".join(doc[i].get_text("text") for i in range(min(35,len(doc)))).lower()
        if not any(word.lower() in intro for word in SOURCES[symbol]["identity"]):
            raise ValueError("Wrong issuer")
        ret={}
        for kind,page_number in (("income",income_page),("balance",balance_page)):
            lines=doc[page_number-1].get_text("text").splitlines()
            plain=" ".join(lines).lower()
            if not ("group" in plain and "bank" in plain
                    and "2025" in plain and "2024" in plain
                    and "in $ million" in plain):
                raise ValueError(f"Group/Bank columns and unit missing {kind}")
            if (kind=="income" and not ("income statements" in plain and "31 december 2025" in plain)
                or kind=="balance" and not ("balance sheets" in plain and "31 december 2025" in plain)):
                raise ValueError(f"Wrong Group statement date/type {kind}")
            ret[kind]={key:parse_group_row(lines,label,pair)
                       for key,(label,pair) in VALUES[symbol][kind].items()}
        for year in ("2025","2024"):
            inc=ret["income"]
            bal=ret["balance"]
            get=lambda d,k:d[k][year]
            if (get(inc,"net_interest_income")+get(inc,"non_interest_income")
                    !=get(inc,"total_income")):
                raise ValueError("Bank total income cross-foot failed")
            if (get(inc,"parent_profit")+get(inc,"non_controlling_profit")
                    !=get(inc,"profit_for_year")):
                raise ValueError("Bank parent profit / NCI cross-foot failed")
            if (get(bal,"total_assets")-get(bal,"total_liabilities")
                    !=get(bal,"total_equity")):
                raise ValueError("Bank consolidated balance does not balance")
            if symbol=="O39":
                attributable=sum(get(bal,k) for k in
                    ("share_capital","other_equity_instruments","capital_reserves",
                     "fair_value_reserves","revenue_reserves"))
                if attributable!=({ "2025":61768,"2024":59316 }[year]):
                    raise ValueError("OCBC parent owner reserve composition mismatch")
                if (attributable+get(bal,"subsidiary_equity")
                        +get(bal,"non_controlling_equity")!=get(bal,"total_equity")):
                    raise ValueError("OCBC Group equity scope mismatch")
            else:
                if (sum(get(bal,k) for k in ("share_capital","retained_earnings","other_reserves"))
                        !=get(bal,"parent_equity")
                    or get(bal,"parent_equity")+get(bal,"non_controlling_equity")
                        !=get(bal,"total_equity")):
                    raise ValueError("UOB Group owner/NCI equity mismatch")
        if symbol=="O39":
            ret["balance"]["parent_equity"]={"2025":61768,"2024":59316}
        return {
            "symbol":symbol,"reporting_period_end":"2025-12-31",
            "scope":"AUDITED_ISSUER_GROUP_STATEMENTS_NOT_STANDALONE_BANK",
            "unit":"SGD_millions",
            "source_pages":{"income":income_page,"balance":balance_page},
            "income":ret["income"],"balance":ret["balance"],
            "independent_cross_source_verification":False,
            "market_data_verified":False,"ranking_eligible":False,
        }
    finally:doc.close()


def run(symbol,output,raw=None):
    rec={"symbol":symbol,"status":"NOT_VERIFIED",
         "source_url":SOURCES[symbol]["url"],"pdf_sha256":None,
         "record":None,"error":None}
    try:
        data=get_pdf(SOURCES[symbol]["url"],max_bytes=75_000_000,timeout=90) if raw is None else raw
        rec["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        rec["record"]=parse_pdf(symbol,data)
        rec["status"]="BANK_GROUP_AUDITED_2025_2024_ISSUER_PDF_RECONCILED"
    except Exception as exc:
        rec["error"]=f"{type(exc).__name__}: {str(exc)[:330]}"
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return rec

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",choices=tuple(VALUES),required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    a=p.parse_args()
    r=run(a.symbol,a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(a.symbol,r["status"],r["error"])
    raise SystemExit(0 if r["status"]=="BANK_GROUP_AUDITED_2025_2024_ISSUER_PDF_RECONCILED" else 1)
