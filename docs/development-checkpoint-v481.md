# VALUE HUNTER AI v481

The **SGX S63 two-session close check** workflow runs the v480 comparison
on demand from main. Enter two Singapore trading dates, for example 13
and 16 November 2026. It uses the existing reviewed SGX close grant and
records both valuation statuses and publication blockers in the Actions
summary. Missing credentials or an incomplete comparison fails the run.
The workflow has read-only repository permissions.

A push that changes the workflow or its comparison entry point runs the
HTTPS fixture independently of the grant. The live comparison remains
unverified until a licensed endpoint and grant are configured.
