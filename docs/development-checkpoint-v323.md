# VALUE HUNTER AI v323 — personal JPX daily closes

The J-Quants V2 exporter requests one or more four-character common-stock codes and a bounded daily date interval using the user's local `JQUANTS_API_KEY`. It checks code and date, traverses pagination, skips no-trade rows, and selects the unadjusted close `C` before exporting personal CSV in the research page's format. It sends no results to GitHub Pages.

```sh
python3 scripts/export-jquants-personal-quotes.py --from 2026-03-30 --to 2026-03-31 7203 7201 > jp-closes.csv
```

The official [daily bars V2 reference](https://jpx-jquants.com/ja/spec/eq-bars-daily) documents the fields. The free plan has a twelve-week delay. Paging, non-trading rows, unadjusted closes, and invalid identity/dates were tested on synthetic responses. An authenticated request remains to be verified using a personal subscription. Public automated quotes for JP, US and SGX, additional filing coverage, and formal ranking validation remain open.
