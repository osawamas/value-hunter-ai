# VALUE HUNTER AI v464

The IBM demo preflight compares the newest date returned by the provider
with the date recorded by an earlier GitHub Actions run. Its summary
reports a first observation, an advance, an unchanged date, or an older
provider response. An older response does not move the saved date back.
The artifact retains only the date for 14 days. An unchanged date alone
does not identify whether the market was closed or the provider was late.

In v465, the comparison uses earlier artifacts from this repository's
`main` branch and includes a link to the baseline run in the summary.

In v466, the same artifact also includes `session.json` with the
comparison result, observed and retained dates, baseline run ID,
and both trading dates' retrieval and valuation statuses. Closing
prices and valuation ratios are excluded. The original date file
continues to be used for the next run's comparison.
