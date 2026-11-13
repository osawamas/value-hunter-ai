"""Expose bank-specific D05 audited issuer evidence in dashboard without valuations.

Only adds 'banking_evidence' nested data; never rewrites generic financial,
price, PER, PBR, ranking or source-provenance fields. Fail closed on mismatch.
"""
import argparse
import json
import re
from pathlib import Path

ALLOWED_METRICS=("net_interest_income","non_interest_income","total_income",
                 "total_expenses","allowances_for_credit_losses","net_profit",
                 "profit_attributable_to_parent","non_controlling_profit")
BALANCE_METRICS=("total_assets","total_liabilities","net_assets",
                 "parent_shareholders_funds","non_controlling_interests",
                 "total_equity","customer_loans")


def attach_bank_evidence(feed,bundle):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Cannot enrich incompatible dashboard")
    if bundle.get("symbol")!="D05" or bundle.get("status")!="DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED":
        raise ValueError("DBS bank source failed verification")
    ev=bundle.get("evidence") or {}
    d05=[r for r in feed.get("records",[]) if r.get("symbol")=="D05"]
    if len(d05)!=1 or ev.get("symbol")!="D05":
        raise ValueError("DBS record missing or duplicated")
    row=d05[0]
    if (row.get("ranking_eligible") is not False
            or row.get("financial_source_kind")!="REGISTERED_SOURCE_NOT_PARSED"
            or row.get("financial_source_url")!=ev.get("source_url")
            or ev.get("financial_period_end")!="2025-12-31"
            or ev.get("shares_as_of_date")!="2026-02-10"
            or ev.get("unit")!="SGD_millions"
            or ev.get("status")!="DBS_FY2025_BANK_GROUP_ISSUER_RECONCILED"
            or not re.fullmatch(r"[a-f0-9]{64}",ev.get("pdf_sha256",""))):
        raise ValueError("Bank scope/period/source/hash mismatch")
    inc=ev.get("income",{})
    bal=ev.get("balance",{})
    shares=ev.get("shares",{})
    for year in ("2025","2024"):
        if set(inc.get(year,{}))!=set(ALLOWED_METRICS) or set(bal.get(year,{}))!=set(BALANCE_METRICS):
            raise ValueError("DBS bank data incomplete")
        vals=list(inc[year].values())+list(bal[year].values())
        if any(type(v) is not int or v<0 for v in vals):
            raise ValueError("Bank amounts invalid")
        if (inc[year]["net_interest_income"]+inc[year]["non_interest_income"]!=inc[year]["total_income"]
            or inc[year]["profit_attributable_to_parent"]+inc[year]["non_controlling_profit"]!=inc[year]["net_profit"]
            or bal[year]["total_assets"]-bal[year]["total_liabilities"]!=bal[year]["total_equity"]
            or bal[year]["parent_shareholders_funds"]+bal[year]["non_controlling_interests"]!=bal[year]["total_equity"]):
            raise ValueError("Bank Group statement reconciliation mismatch")
    if (type(shares.get("shares_outstanding")) is not int
            or type(shares.get("treasury_shares")) is not int
            or type(shares.get("issued_shares_including_treasury_derived")) is not int
            or shares.get("shares_outstanding")<=0
            or shares.get("treasury_shares")<0
            or shares.get("issued_shares_including_treasury_derived")!=shares["shares_outstanding"]+shares["treasury_shares"]
            or shares.get("as_of_date")!="2026-02-10"):
        raise ValueError("Historical DBS treasury reconciliation mismatch")
    if any(row.get(k) is not None for k in ("price_sgd","market_cap_sgd",
                                           "per_reference","pbr_reference_unverified")):
        raise ValueError("Unexpected unverified DBS valuation already present")
    result=json.loads(json.dumps(feed))
    d05out=next(r for r in result["records"] if r["symbol"]=="D05")
    d05out["banking_evidence"]={
        "status":"BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED",
        "scope":"GROUP_BANKING_NOT_INDUSTRIAL_FINANCIALS",
        "fiscal_year":2025,
        "unit":"SGD_millions",
        "source_url":ev["source_url"],
        "pdf_sha256":ev["pdf_sha256"],
        "income":inc,"balance":bal,
        "historical_shareholding":shares,
        "independent_cross_source_verification":False,
        "ranking_eligible":False,
    }
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--feed",required=True)
    p.add_argument("--bundle",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    src=json.loads(Path(a.feed).read_text(encoding="utf-8"))
    proof=json.loads(Path(a.bundle).read_text(encoding="utf-8"))
    out=attach_bank_evidence(src,proof)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("D05 FY2025 banking-only evidence attached; valuation remains blank.")

if __name__=="__main__":
    main()
