# VALUE HUNTER AI v409 — Verify IBM's valuation inputs on source updates

The market-source workflow checks IBM's exact-date share count and annual financial inputs on every matching push and manual run using excerpts saved from the SEC 10-Q, 10-K and Exhibit 13. The GitHub-hosted runner received HTTP 403 from the SEC archive, so the live original downloads run on manual dispatch with `check_sec_live` enabled, independently of the optional SEC Company Facts replay.

    python3 scripts/verify-market-sources-v315.py --sec-ibm-shares-only
    python3 scripts/verify-market-sources-v315.py --sec-ibm-annual-only

The three excerpts preserve the relevant inline XBRL facts, contexts and units after XML serialization. The original download SHA-256 values were `20ef6420ee80928924ea3338c0b234eeaf162ca42a545c010a2bbf6e599b0e72` (10-Q), `c4b72cd6a769d15d3d72310cdd5d01176706287e28794b019061e3ceee45a6e1` (10-K), and `03fa442bdfbcb98a091deaa99abbe00ea10bcb9c06a7628fc799036757ba1b5e` (Exhibit 13). Offline runs print the excerpt hashes. Public daily-price usage rights and two consecutive authenticated price updates remain open.
