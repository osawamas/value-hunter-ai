# VALUE HUNTER AI v389 — Preserve a local price snapshot across failed refreshes

The personal J-Quants exporter now accepts `--output` to replace a local CSV after validation. Use `--require-all` to reject a refresh if any requested symbol has no close in the requested interval. This checks symbol coverage across the interval. For a same-session check, use `--date`. The existing standard-output mode remains available.

Run the exporter with a J-Quants personal API key in the environment and choose dates covered by the account. Save the first export as `previous.csv` and export the same range to `current.csv` for the next observation.

    python3 scripts/export-jquants-personal-quotes.py --from 2026-09-28 --to 2026-10-02 --require-all --output previous.csv 7203
    python3 scripts/export-jquants-personal-quotes.py --from 2026-09-28 --to 2026-10-02 --require-all --output current.csv 7203
    node scripts/check-representative-valuations.js --compare previous.csv current.csv

Tests cover retrieval failure, missing symbols, write failure and successful replacement. The exporter uses the [official J-Quants daily price endpoint](https://jpx-jquants.com/ja/spec/eq-bars-daily) and continues to export unadjusted closes for personal use. An authenticated consecutive live replay, public usage rights and formal ranking eligibility remain open.
