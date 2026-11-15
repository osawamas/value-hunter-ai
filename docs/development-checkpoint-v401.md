# VALUE HUNTER AI v401 — Record how a personal J-Quants snapshot was retrieved

The personal exporter can emit a JSON receipt after writing a complete local snapshot. It records the endpoint, price basis, requested codes and date range, completion time, observation count and exact CSV SHA-256. Use the hash to identify the same file in the representative valuation comparison.

    python3 scripts/export-jquants-personal-quotes.py --date 2026-09-30 --require-all --output quotes.csv --provenance 7203 2> retrieval.json

Choose a date that the account can access. The receipt is written to stderr on success. Check the exit code before reading it because errors also use stderr. The timestamp comes from the local clock and the receipt records personal-use provenance. Authentication with real credentials, consecutive live refreshes and public usage rights remain open.
