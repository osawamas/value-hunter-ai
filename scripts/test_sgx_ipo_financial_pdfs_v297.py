#!/usr/bin/env python3
"""v297 zero-network negative tests of original source manifests and PDF parser."""
import importlib.util
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("v297",ROOT/"scripts/replay-sgx-ipo-financial-pdfs-v297.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
doc=json.loads((ROOT/"docs/data/sgx-ipo-financial-documents-v297.json").read_text())
assert len(m.validate_manifest(doc))==3
assert doc["ranking_eligible_count"]==0
assert doc["sources"][0]["historical_audited_periods"]==["2024-03-31","2025-03-31","2026-03-31"]
assert doc["sources"][1]["historical_audited_periods"]==["2023-12-31","2024-12-31","2025-12-31"]
assert doc["sources"][2]["historical_audited_periods"]==[]
def invalid(change):
    d=json.loads(json.dumps(doc));change(d)
    try:m.validate_manifest(d)
    except ValueError:return
    raise AssertionError("Accepted invalid SGX source")
invalid(lambda d:d.update(ranking_enabled=True))
invalid(lambda d:d.update(quote_feed_license_verified=True))
invalid(lambda d:d.update(up_to_date_independent_financial_verification_complete=True))
invalid(lambda d:d["sources"][0].update(url="https://mirror.test/source.pdf"))
invalid(lambda d:d["sources"][0].update(url="http://links.sgx.com/FileOpen/f.pdf?App=IPO&FileID=6803"))
invalid(lambda d:d["sources"][0].update(url=d["sources"][1]["url"]))
invalid(lambda d:d["sources"][0].update(document_type="ISSUER_9M2026_BUSINESS_UPDATE"))
invalid(lambda d:d["sources"][0].update(github_actions_confirmed_sha256="00"))
invalid(lambda d:d["sources"][1].update(github_actions_confirmed_original_bytes=12))
invalid(lambda d:d["sources"][2].update(original_replay_run_id=12345))
try:m.extract_checks(b"<!doctype html><html>SGX</html>",["SGX"])
except ValueError:pass
else:raise AssertionError("HTML disguised as PDF accepted")
print("v297 PASS: SGX prospectus/issuer document source constraints, audit timing, no ranking or quote promotion")
