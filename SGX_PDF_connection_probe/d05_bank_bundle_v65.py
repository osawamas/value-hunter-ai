"""Assemble three DBS official FY2025 PDF extractors from ONE verified raw download.

Produces a bank-only evidence bundle, not a generic industrial issuer financial
record. Prevents accidental promotion of stale shares or unverified valuations.
"""
import argparse
import hashlib
import json
from pathlib import Path

import d05_shareholding_v62 as shares
import d05_bank_income_v63 as income
import d05_bank_balance_v64 as balance


def combine(raw):
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("DBS PDF bytes invalid")
    sha=hashlib.sha256(raw).hexdigest()
    s=shares.parse_pdf(raw)
    i=income.parse_pdf(raw)
    b=balance.parse_pdf(raw)
    if (s.get("as_of_date")!="2026-02-10"
            or i.get("industry_metric_schema")!="BANKING_INCOME_V63_NOT_INDUSTRIAL"
            or b.get("metric_schema")!="BANKING_BALANCE_V64_NOT_INDUSTRIAL"
            or i.get("fiscal_year")!=2025 or b.get("fiscal_year")!=2025
            or i.get("unit")!="SGD_millions" or b.get("unit")!="SGD_millions"
            or i.get("ranking_eligible") is not False
            or b.get("ranking_eligible") is not False):
        raise ValueError("DBS report scopes / banking schema inconsistent")
    return {
        "symbol":"D05","issuer":"DBS Group Holdings Ltd",
        "financial_period_end":"2025-12-31",
        "shares_as_of_date":"2026-02-10",
        "source_url":shares.SOURCE,"pdf_sha256":sha,
        "source_type":"AUDITED_ISSUER_ANNUAL_REPORT_NOT_THIRD_PARTY_CROSS_CHECK",
        "status":"DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED",
        "unit":"SGD_millions",
        "income":{"2025":{key:entry["2025"] for key,entry in i["metrics"].items()},
                  "2024":{key:entry["2024"] for key,entry in i["metrics"].items()}},
        "balance":{"2025":{key:entry["2025"] for key,entry in b["metrics"].items()},
                   "2024":{key:entry["2024"] for key,entry in b["metrics"].items()}},
        "shares":{"as_of_date":s["as_of_date"],
                  "shares_outstanding":s["shares_outstanding"],
                  "treasury_shares":s["treasury_shares"],
                  "issued_shares_including_treasury_derived":s["issued_shares_including_treasury_derived"]},
        "financials_verified_as_current":False,
        "market_quote_available":False,
        "ranking_eligible":False,
        "bank_income_pdf_page":i["pdf_page_number"],
        "bank_balance_pdf_page":b["pdf_page_number"],
        "shares_pdf_page":s["page_pdf_number"],
    }


def run(output,raw=None):
    output=Path(output)
    rec={"symbol":"D05","status":"NOT_VERIFIED",
         "evidence":None,"error":None}
    try:
        pdf=shares.fetch() if raw is None else raw
        rec["evidence"]=combine(pdf)
        rec["status"]="DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED"
    except Exception as exc:
        rec["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return rec


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    a=p.parse_args()
    r=run(a.output,Path(a.offline_pdf).read_bytes() if a.offline_pdf else None)
    print(r["status"],r["error"])
    raise SystemExit(0 if r["status"]=="DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED" else 1)
