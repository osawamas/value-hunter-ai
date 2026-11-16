# VALUE HUNTER AI v480

Run a read-only two-session S63 close and valuation check with the
configured SGX HTTPS endpoint and reviewed grant:

    node scripts/fetch-sgx-public-quotes.js docs/data/latest.json grant.json --compare-s63 2026-11-13 2026-11-16

The same endpoint must supply both exact sessions. The report contains
valuation status, interim status and publication errors for each date.
It omits price and ratio values and leaves the feed and its history
untouched. Exit status 2 means both closes were retrieved but at least
one annual valuation is incomplete. Publication tests run independently
against the supplied current feed, so historical quotes can pass the
valuation check while falling behind the published session.
HTTPS regression uses fixture prices and the real SGXNet share counts.
A live licensed feed is still needed.
