"""Historical bank-only profitability indicators from audited Group issuer evidence.

This is NOT the bank's official ROE or a ranking signal:
  Simple average-parent-equity ROE = parent profit / average(year-end equity)
  Cost-to-income proxy = absolute issuer Group operating costs / total income
  Parent equity / profit YoY use issuer Group accounting amounts.
All inputs are reported in SGD millions, not SGX share prices.
"""
import argparse
import json
import re
from pathlib import Path


def bank_inputs(row):
    symbol=row.get("symbol")
    if symbol=="D05":
        src=row.get("banking_evidence") or {}
        if (src.get("status")!="BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED"
                or src.get("unit")!="SGD_millions"):
            return None
        income=src.get("income") or {}
        balance=src.get("balance") or {}
        try:
            return {
                "profit":{y:income[y]["profit_attributable_to_parent"] for y in ("2025","2024")},
                "income":{y:income[y]["total_income"] for y in ("2025","2024")},
                "costs":{y:income[y]["total_expenses"] for y in ("2025","2024")},
                "equity":{y:balance[y]["parent_shareholders_funds"] for y in ("2025","2024")},
                "pdf_sha256":src["pdf_sha256"],"source_url":src["source_url"],
                "provenance":"D05_AUDITED_GROUP_ISSUER_PDF",
            }
        except (KeyError,TypeError):
            raise ValueError("DBS bank evidence incomplete")
    if symbol in ("O39","U11"):
        src=row.get("banking_audited") or {}
        if (src.get("status")!="ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS"
                or src.get("scope")!="GROUP_FINANCIALS_NOT_STANDALONE_BANK"
                or src.get("unit")!="SGD_millions"):
            return None
        income=src.get("income") or {}
        bal=src.get("balance") or {}
        try:
            return {
                "profit":income["parent_profit"],
                "income":income["total_income"],
                "costs":income["total_operating_expenses"],
                "equity":bal["parent_equity"],
                "pdf_sha256":src["pdf_sha256"],"source_url":src["source_url"],
                "provenance":symbol+"_AUDITED_GROUP_ISSUER_PDF_MATCHED_SUMMARY",
            }
        except KeyError:
            raise ValueError("Audited Group bank evidence incomplete")
    return None


def compute_bank_indicators(feed):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Wrong public feed")
    result=json.loads(json.dumps(feed))
    for row in result.get("records",[]):
        src=bank_inputs(row)
        if src is None:
            continue
        if (row.get("ranking_eligible") is not False
                or any(row.get(key) is not None for key in (
                    "price_sgd","market_cap_sgd","per_reference",
                    "pbr_reference_unverified","pbr_verified"))):
            raise ValueError("Bank valuation/ranking is not independently validated")
        if not re.fullmatch("[0-9a-f]{64}",src["pdf_sha256"]):
            raise ValueError("Bank audited PDF identification invalid")
        if not src.get("source_url","").startswith("https://"):
            raise ValueError("Bank source URL invalid")
        profit,income,cost,equity=[src[k] for k in ("profit","income","costs","equity")]
        for yr in ("2025","2024"):
            values=[metric.get(yr) for metric in (profit,income,cost,equity)]
            if (any(type(v) is not int for v in values)
                    or profit[yr]<0 or income[yr]<=0 or equity[yr]<=0):
                raise ValueError("Bank input not a positive audited SGD-million value")
            if abs(cost[yr])>income[yr] or abs(cost[yr])<0:
                raise ValueError("Bank expense denominator invalid")
        avg_equity=(equity["2025"]+equity["2024"])/2
        if avg_equity<=0:raise ValueError("Bank equity average invalid")
        values={
            "simple_roe_percent":round(100*profit["2025"]/avg_equity,2),
            "cost_to_income_proxy_percent":round(100*abs(cost["2025"])/income["2025"],2),
            "parent_profit_growth_percent":round(100*(profit["2025"]/profit["2024"]-1),2) if profit["2024"]>0 else None,
            "parent_equity_growth_percent":round(100*(equity["2025"]/equity["2024"]-1),2),
        }
        row["banking_indicators"]={
            "status":"HISTORICAL_DERIVED_FROM_AUDITED_ISSUER_GROUP_FY2025",
            "fiscal_year":2025,"currency":"SGD",
            "source_pdf_sha256":src["pdf_sha256"],
            "source_url":src["source_url"],
            "provenance":src["provenance"],
            "values":values,
            "simple_roe_method":"2025 parent profit / ((2025 closing parent equity + 2024 closing parent equity)/2)",
            "cost_income_method":"absolute 2025 Group operating expense / 2025 Group total income",
            "not_bank_reported_roe":True,
            "not_independently_cross_source_verified":True,
            "ranking_eligible":False,
        }
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    source=json.loads(Path(a.input).read_text(encoding="utf-8"))
    result=compute_bank_indicators(source)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Bank historical derived metrics:",[r["symbol"] for r in result["records"] if r.get("banking_indicators")])
