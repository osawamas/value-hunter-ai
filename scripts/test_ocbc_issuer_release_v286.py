#!/usr/bin/env python3
"""A same-issuer second publication only verifies rounded source concordance."""
import importlib.util
import pathlib
path=pathlib.Path(__file__).resolve().with_name("replay-ocbc-issuer-release-v286.py")
spec=importlib.util.spec_from_file_location("ocbc_cross_source_v286",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
bank=m.source_rows()
body=("OCBC Group Third Quarter 2026 Results "
      "Singapore, 6 November 2026. "
      "Group net profit in the third quarter of 2026 was S$2.04 billion. "
      "First nine months 9M26 profit of S$6.24 billion. "
      "Third quarter net interest income was S$2.31 billion. "
      "Nine-month net interest income reached S$6.80 billion.")
result=m.rounded_matches(body,bank)
assert result["issuer_release_text_matched"] is True
assert all(result["SGX_precision_within_rounded_release_bounds"].values())
assert result["independent_financial_audit_complete"] is False
assert result["ranking_eligible"] is False
assert result["reported_rounding_only_not_exact_reverification"] is True
for old in ["2.04 billion","6.24 billion","2.31 billion","6.80 billion","OCBC Group","6 November 2026"]:
    broken=body.replace(old,"UNKNOWN")
    assert m.rounded_matches(broken,bank)["issuer_release_text_matched"] is False,old
tampered=dict(bank);tampered["q3profit"]=2075
assert not m.rounded_matches(body,tampered)["issuer_release_text_matched"]
html='<html><head><script>fictional 6.80 billion</script></head><body>'+body+"</body></html>"
clean=m.PlainHTML();clean.feed(html)
assert "fictional" not in " ".join(clean.parts)
print("v286 PASS: issuer OCBC Q3/9M 2026 cross-publication rounded values check, explicit NOT independent audit/ranking")
