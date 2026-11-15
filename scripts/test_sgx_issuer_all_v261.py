#!/usr/bin/env python3
"""Offline integrity tests for all 19 direct SGXNet source replay records."""
import importlib.util
import pathlib
root=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("sgx_all_replay_v261",root/"replay-sgx-issuer-all-v261.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
rows=v.source_rows()
assert len(rows)==19
assert len({r["name"] for r in rows})==19
assert len({r["code"] for r in rows})==19
assert "O39" not in {r["code"] for r in rows}
assert all(v.probe.validate_url(row["url"])==row["url"] for row in rows)
responses=[]
for row in rows:
    words="Issuer & Securities\n"+row["name"]+" - "+row["isin"]+" - "+row["code"]+"\nAnnouncement Reference "+row["reference"]
    found=v.probe.inspect(row,("<html><body>"+words+"</body></html>").encode())
    assert found["original_body_identity_verified"] is True
    assert len(found["download_sha256"])==64
    responses.append(found)
good=v.build_report(responses)
assert good["direct_original_html_identity_verified_count"]==19
assert good["not_verified_count"]==0
assert not good["full_official_sgx_security_master_verified"]
assert not good["live_quote_data_rights_verified"]
assert good["ranking_eligible_count"]==0
spoofed=[dict(x) for x in responses]
spoofed[4]["original_body_identity_verified"]=False
spoofed[4]["observation_status"]="NOT_VERIFIED"
bad=v.build_report(spoofed)
assert bad["direct_original_html_identity_verified_count"]==18
assert bad["not_verified_count"]==1
assert bad["ranking_eligible_count"]==0
for broken in (spoofed[:18],spoofed+[spoofed[0]]):
    try:v.build_report(broken);raise AssertionError("accepted invalid response count")
    except ValueError:pass
print("v261 PASS: 19 bounded official SGX issuer URL fixtures; partial failures never promote original proof")
