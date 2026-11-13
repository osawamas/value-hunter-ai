"""v76: publish dated February 2026 shareholding as historical evidence only.

It is NOT an up-to-date market share count. Keep top-level shares_outstanding,
gross_issued_shares, treasury_shares, market_cap_sgd, PER/PBR and all ranking
flags unchanged. Match same official 2025 annual PDF used for audited Group.
"""
import argparse,json,re
from pathlib import Path
from bank_historical_shares_v75 import CONFIG

def attach(feed,proof):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Unexpected public feed")
 symbol=proof.get("symbol")
 if symbol not in CONFIG or proof.get("status")!="ISSUER_HISTORICAL_TREASURY_ARITHMETIC_RECONCILED":
  raise ValueError("Historical bank shares not verified")
 snap=proof.get("record") or {}
 spec=CONFIG[symbol]
 rows=[row for row in feed.get("records",[]) if row.get("symbol")==symbol]
 if len(rows)!=1:raise ValueError("Ambiguous bank")
 bank=rows[0]
 audited=bank.get("banking_audited") or {}
 if (audited.get("status")!="ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS"
    or proof.get("source_url")!=audited.get("source_url")
    or proof.get("pdf_sha256")!=audited.get("pdf_sha256")
    or not re.fullmatch(r"[a-f0-9]{64}",proof.get("pdf_sha256",""))):
  raise ValueError("Historical shareholding source PDF differs from audited annual filing")
 if (snap.get("symbol")!=symbol or snap.get("as_of_date")!=spec["date"]
    or snap.get("historical_only") is not True
    or snap.get("market_cap_or_ranking_eligible") is not False
    or snap.get("shares_count_basis")!="issued_excluding_treasury"
    or snap.get("source_pdf_page")!=spec["page"]
    or snap.get("subsidiary_holdings")!=0):
  raise ValueError("Invalid historical share date and basis")
 gross=snap.get("gross_issued_shares")
 treasury=snap.get("treasury_shares")
 net=snap.get("issued_excluding_treasury")
 if (any(type(n) is not int for n in (gross,treasury,net))
    or gross<=0 or treasury<0 or net<=0 or gross-treasury!=net
    or (gross,treasury,net)!=(spec["gross"],spec["treasury"],spec["net"])):
  raise ValueError("Bank dated share arithmetic mismatch")
 if (bank.get("ranking_eligible") is not False
    or any(bank.get(k) is not None for k in (
      "shares_outstanding","gross_issued_shares","treasury_shares",
      "price_sgd","market_cap_sgd","per_reference","pbr_reference_unverified"))):
  raise ValueError("Unexpected current bank share or valuation already present")
 out=json.loads(json.dumps(feed))
 row=next(item for item in out["records"] if item["symbol"]==symbol)
 row["bank_historical_shares"]={
    "status":"HISTORICAL_ISSUER_PDF_TREASURY_RECONCILED_NOT_CURRENT",
    "as_of_date":snap["as_of_date"],
    "issued_excluding_treasury":net,
    "gross_issued_shares":gross,
    "treasury_shares":treasury,
    "source_url":proof["source_url"],
    "source_pdf_sha256":proof["pdf_sha256"],
    "source_pdf_page":spec["page"],
    "historical_only":True,
    "current_market_cap_usable":False,
    "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--feed",required=True)
 p.add_argument("--source",required=True)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 feed=json.loads(Path(a.feed).read_text(encoding="utf-8"))
 evidence=json.loads(Path(a.source).read_text(encoding="utf-8"))
 result=attach(feed,evidence)
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("Attached historical bank shares for",evidence["symbol"])
