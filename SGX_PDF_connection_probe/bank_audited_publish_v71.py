"""Attach audited Group financial evidence for OCBC/UOB after same-PDF crosscheck.

Not a market-data or third-party cross-source verification. Keep existing
industrial fields, PER/PBR and rankings unchanged. Reject unbalanced accounts,
wrong issuer/period/group scope, mismatched PDF hashes, and rounded-value
precision inflation.
"""
import argparse
import json
import re
from pathlib import Path

METRICS={
    "O39":{
        "net_interest_income":("income","net_interest_income"),
        "total_income":("income","total_income"),
        "parent_attributable_profit":("income","parent_profit"),
        "parent_equity":("balance","parent_equity"),
        "total_assets":("balance","total_assets"),
    },
    "U11":{
        "total_income":("income","total_income"),
        "total_expenses":("income","total_operating_expenses"),
        "operating_profit":("income","profit_before_allowances"),
        "parent_net_profit":("income","parent_profit"),
        "total_assets_rounded_billions":("balance","total_assets"),
        "parent_equity_rounded_billions":("balance","parent_equity"),
    }
}
ROUNDED={"total_assets_rounded_billions","parent_equity_rounded_billions"}


def crosscheck(feed,audit):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Unexpected public feed schema")
    symbol=audit.get("symbol")
    if symbol not in METRICS or audit.get("status")!="BANK_GROUP_AUDITED_2025_2024_ISSUER_PDF_RECONCILED":
        raise ValueError("Audited Group PDF evidence not verified")
    record=audit.get("record") or {}
    if (record.get("symbol")!=symbol or
            record.get("scope")!="AUDITED_ISSUER_GROUP_STATEMENTS_NOT_STANDALONE_BANK"
            or record.get("unit")!="SGD_millions"
            or record.get("reporting_period_end")!="2025-12-31"
            or record.get("ranking_eligible") is not False
            or not re.fullmatch("[0-9a-f]{64}", audit.get("pdf_sha256",""))):
        raise ValueError("Audited Group financial scope/period/hash invalid")
    matches=[r for r in feed.get("records",[]) if r.get("symbol")==symbol]
    if len(matches)!=1:
        raise ValueError("Ambiguous/missing Group issuer")
    row=matches[0]
    summary=row.get("banking_summary") or {}
    if (summary.get("status")!="ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024"
            or summary.get("pdf_sha256")!=audit["pdf_sha256"]
            or summary.get("source_url")!=audit.get("source_url")
            or summary.get("fiscal_year")!=2025):
        raise ValueError("Highlights and audited statements are not the same source PDF")
    if (row.get("ranking_eligible") is not False
            or any(row.get(k) is not None for k in (
                "price_sgd","market_cap_sgd","per_reference",
                "pbr_reference_unverified","pbr_verified"))):
        raise ValueError("Unexpected priced bank data")
    income=record.get("income") or {}
    balance=record.get("balance") or {}
    if not income or not balance:
        raise ValueError("Missing audited Group statements")
    for year in ("2025","2024"):
        for collection in (income,balance):
            if any(type(v.get(year)) is not int for v in collection.values()):
                raise ValueError("Audited figures require exact integer millions")
        get=lambda d,k:d[k][year]
        if (get(income,"net_interest_income")+get(income,"non_interest_income")
                    !=get(income,"total_income")
            or get(income,"parent_profit")+get(income,"non_controlling_profit")
                    !=get(income,"profit_for_year")
            or get(balance,"total_assets")-get(balance,"total_liabilities")
                    !=get(balance,"total_equity")):
            raise ValueError("Bank audited accounting equation mismatch")
        if get(balance,"parent_equity")+get(balance,"non_controlling_equity") + (
            get(balance,"subsidiary_equity") if symbol=="O39" else 0
        )!=get(balance,"total_equity"):
            raise ValueError("Parent owner / subsidiary / NCI mismatch")
        for summary_key,(scope,audited_key) in METRICS[symbol].items():
            expected=(summary.get("values",{}).get(summary_key) or {}).get(year)
            actual=(income if scope=="income" else balance)[audited_key][year]
            if type(expected) is not int:
                raise ValueError(f"Summary metric missing {summary_key}")
            if summary_key in ROUNDED:
                if symbol!="U11" or summary.get("rounded_balance_unit")!="SGD_billions_rounded":
                    raise ValueError("Bank rounded balance scale incorrect")
                if abs(actual/1000 - expected)>=0.5:
                    raise ValueError(f"UOB rounded summary and audited amount differ: {summary_key}")
            elif expected!=actual:
                raise ValueError(f"Bank audited statement differs from highlights: {summary_key}")
    out=json.loads(json.dumps(feed))
    target=next(r for r in out["records"] if r["symbol"]==symbol)
    target["banking_audited"]={
        "status":"ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS",
        "scope":"GROUP_FINANCIALS_NOT_STANDALONE_BANK",
        "period_end":"2025-12-31",
        "unit":"SGD_millions",
        "source_url":audit["source_url"],
        "pdf_sha256":audit["pdf_sha256"],
        "source_pages":record.get("source_pages"),
        "income":income,"balance":balance,
        "independent_cross_source_verification":False,
        "ranking_eligible":False,
    }
    return out


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--feed",required=True)
    p.add_argument("--audit",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    feed=json.loads(Path(a.feed).read_text(encoding="utf-8"))
    audit=json.loads(Path(a.audit).read_text(encoding="utf-8"))
    result=crosscheck(feed,audit)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Matched audited bank Group and annual highlights:",audit["symbol"])
