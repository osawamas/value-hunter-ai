# VALUE HUNTER AI v373 — Japanese closing prices by common trading date

The local J-Quants exporter supports `--date` so selected Japanese common stocks can be fetched through one paginated market-wide session query. It matches the exact trading date and five-character common-stock identifiers, uses the unadjusted close, and reports missing requested codes to stderr. Existing `--from` and `--to` mode is retained. The exported CSV works with the existing exact-date share match and remains personal-use data.

Example

    python3 scripts/export-jquants-personal-quotes.py --date 2026-09-30 3861 4375 7201 7203 > quotes.csv

Requires an individual's J-Quants API key in the local environment and access to the requested date under the account plan. Local and CI tests use representative responses. Authenticated provider access and public quote redistribution have not been verified. Formal ranking remains at zero. Continue public pricing and same-date evidence work without a version cap.
