#!/usr/bin/env python3
import importlib.util
import pathlib
p=pathlib.Path(__file__).resolve().with_name("replay-dbs-newsroom-v287.py")
s=importlib.util.spec_from_file_location("dbs_v287",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
bank=m.research()
assert bank["q3profit"]==2813 and bank["nineprofit"]==8822
html="<html><script>fake S$8.82 billion</script><body>DBS third-quarter net profit at SGD 2.81 billion. Singapore, 05 Nov 2026. DBS Group net profit for third-quarter 2026 was SGD 2.81 billion. Nine-month net profit SGD 8.82 billion.</body></html>"
a=m.verify(html.encode(),bank)
assert a["all_source_clues_verified"],a
assert a["not_an_independent_financial_audit"]
assert not a["ranking_eligible"]
for old in ["05 Nov 2026","2.81 billion","8.82 billion","third-quarter 2026"]:
 broken=html.replace(old,"UNKNOWN")
 assert not m.verify(broken.encode(),bank)["all_source_clues_verified"],old
copy=dict(bank);copy["q3profit"]=2875
assert not m.verify(html.encode(),copy)["all_source_clues_verified"]
print("v287 PASS: independent DBS issuer website fetch parser compares 2 reported rounded profit values without unlicensed quotes")
