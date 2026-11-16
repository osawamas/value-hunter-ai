# VALUE HUNTER AI v422

## Toyota personal refresh

    python3 scripts/refresh-jquants-personal.py --output-dir session-1 --date YYYY-MM-DD 7203
    python3 scripts/refresh-jquants-personal.py --output-dir session-2 --previous-dir session-1 --require-toyota-refresh --date YYYY-MM-DD 7203

Use the second command for a later Toyota trading date. With `--require-toyota-refresh` the personal refresh requires two receipt-matched snapshots, a later Toyota session and complete filing-based valuations on both dates. Status 2 means the snapshot and diagnostics were saved, but valuation acceptance failed. Retrieval and receipt verification errors still prevent publishing the local snapshot directory.

Offline regression tests covered both a passing pair and an incomplete comparison on the same session. The development environment had no J-Quants API key available, so these tests do not record live retrieval. The fixture trading dates are dated filing matches and do not establish daily availability of exact outstanding-share evidence.

## Public price supply

The [Twelve Data end-of-day guide](https://support.twelvedata.com/en/articles/12682324-end-of-day-eod-pricing-market-data) restricts individual plans to personal non-commercial use and ties distribution to end users to the business plan tier. The [SGX market data policy](https://www.datadirect.sgx.com/Market-Data-Policy) covers distribution and display. The [NYSE historical product catalog](https://www.nyse.com/market-data/historical) confirms historical feed products and delivery timing. The [JPX catalog](https://clientportal.jpx.co.jp/ClientPortalEN/s/datacatalog/a08J4000000E0MrIAK/a141) lists the paid J-Quants Pro OHLC offering with external distribution possible. These documents did not establish a free public feed grant for the app. No credentials or subscription were added. Public data rights and two live updates remain pending for JP, US and SG.
