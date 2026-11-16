# VALUE HUNTER AI v435

Run the dashboard refresh on main with `sgx_preflight` enabled to try a
reviewed SGX closing-price endpoint before allowing publication. Optionally
set `sgx_session` to a Singapore trading date when testing a past session
or rerunning after a holiday. The run uses the same feed validation as the
scheduled update. It skips the history step and repository push in preflight
mode and does not trigger a Pages deployment. An explicit session or preflight requires a configured grant.

The scheduled refresh still defaults to the current Singapore date. A
preflight does not grant redistribution rights, and the official ranking is
still empty. The July 2026 SGX Market Data Policy governs redistribution;
ICE lists SGX end-of-day data, but its listing does not establish free
publication rights for this app.

- https://www.datadirect.sgx.com/Market-Data-Policy
- https://developer.ice.com/fixed-income-data-services/catalog/singapore-exchange-sgx
