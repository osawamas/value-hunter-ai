#!/usr/bin/env python3
"""Offline mutated HTML regression; no remote dependency."""
import importlib.util
import pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("v293",ROOT/"scripts/replay-sgx-issuer-october-v293.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
good=(b"<html><body>SGX Group's derivatives volume hits six-month high. "
      b"12 November 2026. Securities turnover strengthens in October. "
      b"October 2026 two initial share offerings: Deluge Corporation and "
      b"Mi Material Holding.</body></html>")
p=mod.inspect_html(good)
assert p["all_required_text_matched"]
assert not p["sgxnet_original_attachment_fetched"]
assert not p["october_month_end_listings_verified"]
assert not p["investment_ranking_eligible"]
for bad in [
 good.replace(b"Mi Material Holding",b"Unknown IPO"),
 good.replace(b"Deluge Corporation",b"Unknown IPO"),
 good.replace(b"two initial share offerings",b"one initial share offering"),
 good.replace(b"SGX Group's",b"Other Group's"),
 good.replace(b"12 November 2026",b"12 November 2024").replace(b"October 2026",b"October 2024")
]:
 assert not mod.inspect_html(bad)["all_required_text_matched"]
print("v293 offline PASS: SGX issuer text mutation and ranking/filing scope checks")
