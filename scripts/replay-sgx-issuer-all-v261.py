#!/usr/bin/env python3
"""v261 replay all 19 publicly available SGXNet issuer identity announcement pages.
Never acquire market quotes; record only identity match observations, SHA256 and source URL.
"""
import datetime as dt
import importlib.util
import json
import pathlib
import time

ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("sgx_original_probe_v260",
 ROOT/"scripts/replay-sgx-issuer-html-v260.py")
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
def source_rows():
    a=json.loads((ROOT/"docs/data/sgx-official-issuer-code-filings-v255.json").read_text())
    b=json.loads((ROOT/"docs/data/sgx-net-eleven-codes-v256.json").read_text())
    index=json.loads((ROOT/"docs/data/sgx-corporate-indexed-page-v253.json").read_text())
    accepted={r["issuer_name"] for r in index["records"]}
    items=[]
    for r in a["records"]:
        items.append(dict(name=r["issuer_name"],code=r["trading_code"],
                          isin=r["isin"],reference=r["announcement_ref"],url=r["source_url"]))
    for r in b["records"]:
        items.append(dict(name=r["issuer_name"],code=r["code"],isin=r["isin"],
                          reference=r["filing_reference"],url=r["source_url"]))
    if (len(items)!=19 or len({x["name"] for x in items})!=19
        or len({x["code"] for x in items})!=19
        or len({x["isin"] for x in items})!=19
        or {x["name"] for x in items}-accepted
        or accepted-{x["name"] for x in items}!={"OVERSEA-CHINESE BANKING CORP"}):
        raise ValueError("Original source listing does not cover exactly 19 reviewed issuer identities")
    for row in items:probe.validate_url(row["url"])
    return sorted(items,key=lambda x:x["name"])
def build_report(observations):
    if len(observations)!=19 or len({r["security_code"] for r in observations})!=19:
        raise ValueError("Incomplete response/replay set")
    verified=sum(x["original_body_identity_verified"] for x in observations)
    return {"schema_version":"sgx-net-nineteen-original-html-replay-v261",
      "observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "scope":"19_HISTORICAL_SGXNET_ISSUER_FILINGS_NOT_COMPLETE_OR_CURRENT_SGX_MASTER",
      "sample_count":19,"direct_original_html_identity_verified_count":verified,
      "not_verified_count":19-verified,
      "source_bytes_saved_or_redistributed":False,
      "full_official_sgx_security_master_verified":False,
      "current_listings_verified":False,"live_quote_data_rights_verified":False,
      "issuer_financial_audit_verified":False,
      "ranking_eligible_count":0,"entries":observations}
def main():
    reports=[]
    for i,item in enumerate(source_rows()):
        if i:time.sleep(1.0)
        r=probe.fetch(item)
        reports.append(r)
        print(f"{i+1}/19 {item['code']} {r['observation_status']}",flush=True)
        if r["original_body_identity_verified"]:
            print(f"SGX_DIGEST_V262 {item['code']} {r['download_sha256']} {r['download_bytes']}",flush=True)
    result=build_report(reports)
    out=ROOT/"build/research/sgx-original-nineteen-html-v261.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(f"v261 PROVENANCE {result['direct_original_html_identity_verified_count']}/19 verified, "
          f"{result['not_verified_count']} unverified. No rankings promoted.")
if __name__=="__main__":main()
