# VALUE HUNTER AI v328 — automate JPX quote-export regression checks

The source workflow now runs the J-Quants personal exporter tests on API-shaped responses. The test covers paginated closing prices, trading holidays/no-trade rows, selection of C instead of AdjC, response symbol and date mismatches, and a repeated continuation key. No personal credential or historical quote file is required for this check. An authenticated request is still pending. See v327 for the live SEC limitation and current 16 listed / 12 comparable / 0 ranked coverage.

Resume from main and these checkpoint notes. Continue the hourly three-market plan, prioritizing the official price path and same-date share evidence alongside issuer filings.
