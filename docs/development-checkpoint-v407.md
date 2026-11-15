# VALUE HUNTER AI v407 — Reconcile IBM shares against its original SEC 10-Q

The source verifier can replay IBM's unrounded common-share count from the actual SEC filing. It checks the IBM CIK, exact instant, consolidated context, shares unit and unscaled integer fact. The stored observation is 945,120,805 shares as of September 30, 2026.

    python3 scripts/verify-market-sources-v315.py --sec-ibm-shares-only

The optional fixture directory accepts the same downloaded filing as `IBM-10Q.html`. The SEC live workflow includes the command when dispatched with live checking enabled. Public price usage rights and successive authenticated price refreshes remain open.
