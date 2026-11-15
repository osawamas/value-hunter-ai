# VALUE HUNTER AI v396 — Replay both ST Engineering parent-equity filings

The market source workflow now downloads the two FY2025 PDFs referenced in the v395 evidence. It checks each original SHA-256, extracts the consolidated balance sheet page, and compares the FY2025 group amounts for parent equity, non-controlling interests and net assets. It also checks that the two components reconcile to total equity.

    python3 scripts/verify-market-sources-v315.py --sgx-s63-equity-only

The optional fixture directory accepts the same originals as `annual_report.pdf` and `results.pdf`. The matching documents are issuer filings. Independent financial verification, public closing-price usage rights and two consecutive authenticated updates remain open.
