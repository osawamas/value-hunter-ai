"""Add conservative bank-specific issuer annual highlights for OCBC/UOB.

Never reinterpret rounded UOB SGD billions as exact dollars, or promote these
issuer-highlight metrics to industrial SGX fields, valuations, or ranking.
"""
import argparse
import json
import re
from pathlib import Path

SPEC={
    "O39":{"status":"O39_ISSUER_2025_GROUP_FINANCIAL_HIGHLIGHTS_MATCHED",
           "scope":"ISSUER_SELECTED_GROUP_FINANCIAL_HIGHLIGHTS",
           "unit":"SGD_millions",
           "keys":{"net_interest_income","total_income","parent_attributable_profit",
                   "parent_equity","total_assets"}},
    "U11":{"status":"U11_FY2025_ISSUER_FIVE_YEAR_BANK_SUMMARY_MATCHED",
           "scope":"ISSUER_FIVE_YEAR_GROUP_SUMMARY_NOT_DIRECT_AUDITED_STATEMENTS",
           "unit":"SGD_millions",
           "keys":{"total_income","total_expenses","operating_profit",
                   "parent_net_profit","total_assets_rounded_billions",
                   "parent_equity_rounded_billions"}},
}


def add_bank_summary(feed,raw):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Wrong public comparison feed")
    symbol=raw.get("symbol")
    if symbol not in SPEC:
        raise ValueError("Only O39/U11 summary registration supported")
    spec=SPEC[symbol]
    if raw.get("status")!=spec["status"]:
        raise ValueError("Source PDF not verified")
    evidence=raw.get("record") or {}
    rows=[r for r in feed.get("records",[]) if r.get("symbol")==symbol]
    if len(rows)!=1:
        raise ValueError("Expected exactly one registered bank")
    bank=rows[0]
    if (bank.get("financial_source_kind")!="REGISTERED_SOURCE_NOT_PARSED"
            or bank.get("financial_source_url")!=raw.get("source_url")
            or evidence.get("scope")!=spec["scope"]
            or evidence.get("fiscal_year")!=2025
            or evidence.get("ranking_eligible") is not False
            or not re.fullmatch(r"[0-9a-f]{64}",raw.get("pdf_sha256",""))):
        raise ValueError("Bank source URL, period, scope, or hash invalid")
    if (symbol=="O39" and evidence.get("unit")!="SGD_millions"
        or symbol=="U11" and (evidence.get("financials_unit")!="SGD_millions"
            or evidence.get("rounded_balance_unit")!="SGD_billions_rounded")):
        raise ValueError("Banking unit scale mismatch")
    metrics=evidence.get("metrics") or {}
    if set(metrics)!=spec["keys"]:
        raise ValueError("Incomplete bank financial metrics")
    for key in spec["keys"]:
        row=metrics[key]
        if (set(row)!={"2025","2024"}
                or any(type(row[k]) is not int or row[k]<0 for k in row)):
            raise ValueError("Invalid dated bank metric")
    for year in ("2025","2024"):
        get=lambda key:metrics[key][year]
        if symbol=="O39":
            if (get("total_income")<get("net_interest_income")
                    or get("total_assets")<=get("parent_equity")):
                raise ValueError("OCBC summary arithmetic/scope invalid")
        else:
            if (get("total_income")-get("total_expenses")!=get("operating_profit")
                    or get("total_assets_rounded_billions")<=get("parent_equity_rounded_billions")):
                raise ValueError("UOB summary arithmetic/scale invalid")
    if (bank.get("ranking_eligible") is not False or
        any(bank.get(k) is not None for k in ("market_cap_sgd","price_sgd",
            "per_reference","pbr_reference_unverified"))):
        raise ValueError("Bank quote or valuation not proven")
    result=json.loads(json.dumps(feed))
    row=next(r for r in result["records"] if r["symbol"]==symbol)
    row["banking_summary"]={
        "status":"ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024",
        "scope":spec["scope"],
        "source_url":raw["source_url"],"pdf_sha256":raw["pdf_sha256"],
        "fiscal_year":2025,
        "financial_unit":"SGD_millions",
        "rounded_balance_unit":"SGD_billions_rounded" if symbol=="U11" else None,
        "values":metrics,
        "independently_cross_checked":False,
        "ranking_eligible":False,
    }
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--source",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    feed=json.loads(Path(args.input).read_text(encoding="utf-8"))
    source=json.loads(Path(args.source).read_text(encoding="utf-8"))
    result=add_bank_summary(feed,source)
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Attached source-backed bank-specific summary for",source["symbol"])
