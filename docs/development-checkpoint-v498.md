# VALUE HUNTER AI v498

Toyota's two-session J-Quants check can run from GitHub Actions on
weekdays at 19:37 Japan time and on manual dispatch. It reuses the
free-plan date selection, exact-date share reconciliation and receipt
verification. When the repository secret is unavailable it reports that
live retrieval was skipped. When both closes arrive, the summary shows
the dates and valuation status. The temporary directory is removed
without uploading the provider data or valuation figures.

This uses an existing personal J-Quants API key supplied through the
repository secret. Live access and public ranking data rights remain
unverified.
