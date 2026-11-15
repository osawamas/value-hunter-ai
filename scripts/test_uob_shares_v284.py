#!/usr/bin/env python3
"""Offline SGX UOB share-count original body positive/negative tests."""
import importlib.util
import pathlib
p=pathlib.Path(__file__).resolve().with_name("replay-uob-shares-v284.py")
spec=importlib.util.spec_from_file_location("uob284",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
good=("<html><body>Issuer &amp; Securities\nIssuer Manager UNITED OVERSEAS BANK LIMITED "
 "Securities UNITED OVERSEAS BANK LIMITED - SG1M31001969 - U11 "
 "Announcement Reference SG261112OTHRSYPK Date &amp; Time of Broadcast 12-Nov-2026 "
 "Share Buy-Back - Daily Share Buy-Back Notice\n"
 "Date of Purchase 12/11/2026\n"
 "Total Number of shares purchased 34,000\n"
 "Number of shares cancelled 34,000\n"
 "Number of issued shares excluding treasury shares after purchase 1,646,711,591\n"
 "Number of treasury shares held after purchase 14,548,000</body></html>").encode()
ok=m.check_body(good)
assert ok["fully_original_verified"]
assert ok["shares_ex_treasury_after"]==1646711591
assert ok["treasury_after"]==14548000
assert not ok["current_share_count_verified"] if "current_share_count_verified" in ok else True
assert not ok["latest_2026_11_13_original_verified"]
assert not ok["ranking_eligible"]
for old,new in [
 (b"SG261112OTHRSYPK",b"SG261113OTHRHOAF"),
 (b"12/11/2026",b"13/11/2026"),
 (b"1,646,711,591",b"1,646,677,591"),
 (b"14,548,000",b"14,548,001"),
 (b"34,000",b"33,999"),
 (b"SG1M31001969",b"SG1M31001968"),
 (b"UNITED OVERSEAS BANK LIMITED",b"UNITED OVERSEAS BANK LXD")
]:
 bad=m.check_body(good.replace(old,new))
 assert not bad["fully_original_verified"],(old,new)
 assert bad["shares_ex_treasury_after"] is None
print("v284 PASS: exact Nov12 official issuer identity and labelled shares match; Nov13 and ranking remain unverified")
