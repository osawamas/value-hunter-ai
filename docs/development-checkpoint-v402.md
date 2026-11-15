# VALUE HUNTER AI v402 — Verify personal J-Quants quote provenance offline

Added `scripts/verify-jquants-personal-snapshot.py` and `scripts/test-verify-jquants-personal-snapshot.py`.

After successfully exporting a complete personal J-Quants snapshot with `--require-all --provenance --output quotes.csv`, capture the JSON receipt from stderr and run:

```sh
python3 scripts/verify-jquants-personal-snapshot.py quotes.csv receipt.json
python3 scripts/test-verify-jquants-personal-snapshot.py
```

The verifier checks the CSV SHA-256, personal-use provenance, requested security coverage, observation count, dates, currency, positive finite unadjusted closes, and duplicate market/date rows. It performs no network calls and does not authorize public redistribution or promote any security to the official ranking. The receipt must be captured only after the exporter exits successfully.

Local standalone regression on equivalent verifier logic: 6/6 passed. GitHub Actions status for v401 was unavailable (commit workflow runs and combined statuses both empty). v402 GitHub-hosted CI and Chrome HTTP/ZIP regressions are **not independently verified** in this execution. Do not label them successful until checked.

Next: check v402 Actions and HTTP/ZIP regression, test the committed verifier, then connect verified personal quote snapshots to same-date share counts and financials without treating private quote rights as public redistribution rights. Continue JP/US/SGX representative first-release pipeline; ranking remains disabled (0 eligible) until provenance, price permission and independent valuation inputs pass.
