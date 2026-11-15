# VALUE HUNTER AI v377 — select a filing date and match the close

The filing-share date selector can now set the batch valuation date before quote import. Import uses that date only, and clearing the date restores the latest-per-issuer mode. The existing browser test exercises exporting and reimporting the official count, choosing September 30 and importing a synthetic quote file that also contains other dates. It checks that Toyota is the only result on the selected date, with the expected reference capitalization.

This completes a representative local workflow for aligning share evidence and manually acquired closing prices. Public data rights, automated deployed quote retrieval, a second real-data refresh, and formal ranking remain open.
