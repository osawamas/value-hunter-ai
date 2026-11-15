#!/usr/bin/env python3
"""Offline negative tests for the SGXNet original HTML research probe."""
import importlib.util
import pathlib
import urllib.error

module_path=pathlib.Path(__file__).with_name("replay-sgx-issuer-html-v260.py")
spec=importlib.util.spec_from_file_location("sgx_replay_v260",module_path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
rows=m.source_rows()
assert len(rows)==4
assert {x["code"] for x in rows}=={"HQU","5ML","OTS","5UX"}
for x in rows:
    assert m.validate_url(x["url"])==x["url"]
    words="Issuer & Securities\n"+x["name"]+" - "+x["isin"]+" - "+x["code"]+"\nAnnouncement Reference "+x["reference"]
    found=m.inspect(x,("<html><body>"+words+"</body></html>").encode())
    assert found["original_body_identity_verified"] is True
    assert found["observation_status"]=="MATCHED_OFFICIAL_BODY"
    assert found["current_listing_verified"] is False
    assert found["financial_ranking_eligible"] is False
    for missing in (x["name"],x["isin"],x["code"],x["reference"],"Issuer & Securities"):
        forged=words.replace(missing,"MASKED-EMPTY")
        result=m.inspect(x,("<html><body>"+forged+"</body></html>").encode())
        assert result["original_body_identity_verified"] is False
    assert not m.inspect(x,b"%PDF-1.7",200,"application/pdf")["original_body_identity_verified"]
class FakeResponse:
    status=200
    headers={"Content-Type":"text/html"}
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,size):return self.payload[:size]
    def geturl(self):return rows[0]["url"]
row=rows[0]
text="Issuer & Securities\n"+row["name"]+" - "+row["isin"]+" - "+row["code"]+"\nAnnouncement Reference "+row["reference"]
out=m.fetch(row,lambda req,timeout:FakeResponse(text.encode()))
assert out["original_body_identity_verified"] is True
unavailable=m.fetch(row,lambda req,timeout:(_ for _ in ()).throw(urllib.error.URLError("offline")))
assert unavailable["observation_status"]=="FETCH_UNAVAILABLE"
assert unavailable["financial_ranking_eligible"] is False
for u in [
 "http://links.sgx.com/1.0.0/corporate-announcements/0123456789ABCDEF/",
 "https://evil.test/1.0.0/corporate-announcements/0123456789ABCDEF/",
 "https://links.sgx.com.evil.test/1.0.0/corporate-announcements/0123456789ABCDEF/",
 "https://links.sgx.com/1.0.0/corporate-announcements/0123456789ABCDEF/?token=secret",
 "https://links.sgx.com/1.0.0/corporate-announcements/../etc/passwd",
]:
    try:m.validate_url(u);raise AssertionError("unsafe source accepted: "+u)
    except ValueError:pass
print("v260 PASS: four issuer original HTML replay probes, fail-closed mismatches, no rank/current listing promotion")
