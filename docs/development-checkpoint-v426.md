# VALUE HUNTER AI v426

Run `python3 scripts/check-ibm-personal-refresh.py --demo 2026-09-30 2026-11-13`
for a local IBM comparison with the [official Alpha Vantage example](https://www.alphavantage.co/documentation/#daily).
The tool fetches both dates in one API response, uses the existing issuer/filing
valuation, and prints the results locally. Status 2 means one or both days lack
the evidence required for a complete valuation. An individual API key can be
used via ALPHA_VANTAGE_API_KEY when the requested dates are no longer in the example.

The live demo returned 100 days. The September 30 close matched the exact
945,120,805 common shares reported in the [SEC 10-Q](https://www.sec.gov/Archives/edgar/data/51143/000005114326000095/ibm-20260930.htm).
The November 13 close came back, but the bundled filings did not contain an exact
share count for that date. The report includes the latest available earlier
filing date as a reference. This was one live retrieval with two trading dates.
Neither the [Alpha Vantage terms](https://www.alphavantage.co/terms_of_service/) nor
[FMP's plan terms](https://site.financialmodelingprep.com/pricing-plans?planType=commercial)
established free public distribution rights for the app. The public feed
and formal ranking did not receive any demo prices.
