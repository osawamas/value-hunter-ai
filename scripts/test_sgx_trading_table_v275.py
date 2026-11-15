#!/usr/bin/env python3
"""Synthetic SGX original-table parser regression; no quote prices or current-listed claims."""
import importlib.util
import pathlib
root=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("sgx_trading_v275",root/"replay-sgx-trading-table-v275.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=m.expected()
assert len(rows)==11
assert len({x["symbol"] for x in rows})==11
html="<html><table><tr><th>Security</th><th>Stock code</th><th>Traded currency</th></tr>"+''.join(
 "<tr><td>"+x["name"]+"</td><td>"+x["symbol"]+"</td><td>"+x["trading_currency"]+"</td></tr>"
 for x in rows)+"</table></html>"
good=m.verify(html.encode(),rows)
assert all(x["exact_table_row_verified"] for x in good)
assert all(not x["ranking_eligible"] and not x["current_listed_status_verified"] for x in good)
assert sum(x["exact_table_row_verified"] for x in good)==11
bad=html.replace("<td>O39</td>","<td>O38</td>")
check=m.verify(bad.encode(),rows)
assert sum(x["exact_table_row_verified"] for x in check)==10
# A code/currency elsewhere must not count as a verified adjacent issuer row.
bad2=html.replace("<td>O39</td>","<td></td><td>O39</td>")
check2=m.verify(bad2.encode(),rows)
assert sum(x["exact_table_row_verified"] for x in check2)==10
try:
 m.verify(html.encode(),[{**rows[0],"eligible_for_valuation":True}])
 raise AssertionError("accepted valuation promotion")
except ValueError:pass
print("v275 PASS: exact 11 issuer/code/currency row matching, no false positive from scattered matches or valuation promotion")
