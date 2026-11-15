# VALUE HUNTER AI v398 — Identify the input files in a valuation comparison

The local representative valuation comparison now records the SHA-256 and observation count of each input CSV. Each representative issuer also reports the first and last included trading dates and the number of observations for each file. An issuer absent from a file has null coverage. The coverage reflects observations in the supplied files.

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

Use the hashes to verify which files were compared and the coverage to spot differences in the supplied date ranges. Public daily-close usage rights and consecutive authenticated refreshes remain open.
