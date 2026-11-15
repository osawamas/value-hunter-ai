# VALUE HUNTER AI v408 — Reconcile IBM annual valuations with the SEC 10-K exhibit

The source verifier replays IBM's FY2024 and FY2025 consolidated revenue, net income, assets and parent equity from the original SEC Exhibit 13. It checks the company identifier, consolidation scope, duration or year-end context, USD unit and million-dollar scale. FY2025 net income of USD 10,593 million and parent equity of USD 32,648 million match the existing trial valuation inputs.

    python3 scripts/verify-market-sources-v315.py --sec-ibm-annual-only

The 10-K defines the contexts and units referenced by the exhibit. Use `--fixture-directory` with copies named `IBM-10K.html` and `IBM-10K-EX13.html` to replay offline. The command is included in the manual SEC live workflow. Public daily-price usage rights and successive authenticated quote refreshes remain open.
