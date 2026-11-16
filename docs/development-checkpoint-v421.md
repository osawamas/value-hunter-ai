# VALUE HUNTER AI v421

A refresh can replay both valuations using the filings saved with each input. Previously the comparison used current filings for both, which could hide missing previous evidence or lose a valid previous valuation when the latest filing data changed.

    node scripts/check-representative-valuations.js --filing-dir current/filings --previous-filing-dir previous/filings --require-both-trials --compare previous/quotes.csv current/quotes.csv

The report keeps the SHA-256 hashes for the previous filing inputs under `previousFilingDataSha256` and for the current inputs under `filingDataSha256`. Optional SGXNet notices supplement the current side when a separate prior filing directory is specified. Imports that omit the prior filing directory retain the shared input behavior.

The personal J-Quants refresh automatically uses the preceding snapshot's `filings` directory when it exists. Older snapshots without that directory remain readable. A comparison detects valuation changes with fixture quotes. The data supply and public-distribution review, two live updates, and formal listing remain pending.
