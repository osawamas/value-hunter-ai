# VALUE HUNTER AI v331 — find newer SEC periodic filings

`python3 scripts/check-sec-filing-updates.py` checks SEC Submissions directly for the selected US issuers. It reports 10-K, 10-Q and amendments with end date, filing date, accession and filing link for review. It distinguishes a failed retrieval from a successful check with no new report and leaves the verified annual display untouched. Use `--symbol AAPL` for a single issuer. The live Apple response returned no report subsequent to its FY2026 annual snapshot. Replaying that response against an older baseline found both annual and quarterly reports. The separate GitHub-hosted SEC restriction remains documented in v327.

Continue by running filing discovery during the hourly development task where SEC originals are reachable. Review changed periods before publishing updates. Current counts are 16 listed, 12 annual comparisons, 0 ranked. Personal closing-price and share imports join on the same date in v330.
