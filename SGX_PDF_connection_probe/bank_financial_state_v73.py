"""v73: distinguish issuer-bank financial extraction from industrial ranking inputs.

Historical bank Group statements CAN be parsed while generic-industrial
financial schema remains intentionally missing. Preserve exclusion reason
codes, source metadata, and all valuation/ranking safety gates.
"""
import argparse
import json
import re
from pathlib import Path

BANKS={"D05","O39","U11"}
AUDITED_STATUS="ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS"
DBS_STATUS="BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED"


def annotate(feed):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Wrong public feed")
    result=json.loads(json.dumps(feed))
    for row in result.get("records",[]):
        if row.get("symbol") not in BANKS:
            continue
        symbol=row["symbol"]
        source=row.get("banking_evidence") if symbol=="D05" else row.get("banking_audited")
        if not source:
            continue
        expected=DBS_STATUS if symbol=="D05" else AUDITED_STATUS
        if (source.get("status")!=expected
                or row.get("financial_source_kind")!="REGISTERED_SOURCE_NOT_PARSED"
                or source.get("source_url")!=row.get("financial_source_url")
                or not re.fullmatch("[a-f0-9]{64}",source.get("pdf_sha256",""))):
            raise ValueError("Bank financial source provenance inconsistent")
        if (row.get("ranking_eligible") is not False
                or any(row.get(k) is not None for k in
                       ("price_sgd","market_cap_sgd","per_reference",
                        "pbr_reference_unverified","pbr_verified"))):
            raise ValueError("Unexpected bank valuation")
        row["bank_financial_state"]={
            "status":"AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED",
            "fiscal_year":2025,
            "source_url":source["source_url"],
            "pdf_sha256":source["pdf_sha256"],
            "banking_metrics_parsed":True,
            "generic_industrial_metrics_not_applicable":True,
            "third_party_numerical_verification":False,
            "current_quote_verified":False,
            "current_share_count_verified":False,
            "ranking_eligible":False,
        }
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    src=json.loads(Path(a.input).read_text(encoding="utf-8"))
    output=annotate(src)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Bank-specific finance states:",[r["symbol"] for r in output["records"] if "bank_financial_state" in r])
