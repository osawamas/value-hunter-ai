# VALUE HUNTER AI v409 — Verify IBM's valuation inputs on source updates

The market-source workflow checks IBM's exact-date share count against the SEC 10-Q and its annual financial inputs against the SEC 10-K and Exhibit 13 on every matching push and manual run. The IBM filing check runs independently of the optional SEC Company Facts replay.

    python3 scripts/verify-market-sources-v315.py --sec-ibm-shares-only
    python3 scripts/verify-market-sources-v315.py --sec-ibm-annual-only

The checks cover SEC filing inputs. Public daily-price usage rights and two consecutive authenticated price updates remain open.
