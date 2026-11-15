# VALUE HUNTER AI v414 — Check the latest local valuation in each market

    node scripts/check-representative-valuations.js --require-latest-trials --compare previous.csv current.csv

The optional check selects the newest observation per representative in the supplied current CSV. It requires a same-date filing share match and calculated market cap, PER and PBR for Toyota, IBM and ST Engineering. It prints a per-market report with available filing links and exits with status 2 if any check fails. The historical trial details remain available for diagnosis.

Regression checks run the CLI against three synthetic matched closes and against a newer S63 price without matching shares. This is a local diagnostic. The dates are relative to the supplied files, and published price usage rights, provider authentication and two consecutive live updates remain unverified.
