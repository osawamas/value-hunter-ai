# VALUE HUNTER AI v411 — Preserve the filing inputs used in each refresh

Successful personal refreshes save the three JSON inputs used for the report in a `filings` subdirectory. The valuation command reads these copies and records their SHA-256 hashes. A second refresh uses its own current copies for both quote snapshots, so the comparison isolates price changes against one set of financial inputs.

    node scripts/check-representative-valuations.js --filing-dir next/filings --compare-jquants baseline/quotes.csv baseline/receipt.json next/quotes.csv next/receipt.json

CI verifies the hashes against the saved files and reproduces the saved report with the same code. Public daily-price usage rights and two successive authenticated price refreshes remain open.
