# VALUE HUNTER AI — v47 continuation checkpoint

## Confirmed achievements (2026-11-14 JST)
- v44 official FY2026 S68 financial PDF extraction is live in the v29 integrated comparison pipeline.
- v46 SGX annual report shareholding table parser extracted 2026-09-01 S68 issued 1,071,642,400, treasury 798,916, net 1,070,843,484 with PDF arithmetic and dated-source checks.
- v47 public feed now publishes S68 gross issued count, treasury shares, actual PDF SHA256 and explicit share-count basis, through the v25 -> v28 -> v29 pipeline.
- Publish-visibility round-trip test test_public_shares_v47.py is included in the scheduled workflow.
- Latest public feed successfully checked after run 43497392689; S68 SHA256: 31f159fb83655acbd68bc590b9706defaf5e3d15f530a2ba8c6892cc9360eef4.
- Long-running dashboard refresh now rebases to origin/main and retries non-force pushes after concurrent repository updates.
- Pages workflow syntax/jobs repaired; direct validation succeeds.

## Important blockers
- GitHub Pages is not yet enabled on this repo. GitHub Actions configure-pages with enablement:true failed with 'Resource not accessible by integration'. User must enable GitHub Pages once under Settings -> Pages -> Build and deployment -> Source: GitHub Actions. A passing validation-only workflow is not a successful deployment.
- G13 2026-08-14 IR shares count 12,063,642,274 is still 'Issued & Paid-up Shares' with treasury deduction unconfirmed, while FY2025 treasury subtraction is independently arithmetic-checked within the same issuer PDF. Do not label G13 2026 shares as excluding treasury or promote it into ranking.
- S68 second-issuer financial crosschecks and independent verification remain incomplete. Ranking must remain excluded.

## Next tasks (v48)
1. Obtain G13 1H2026 SGX Financial Results announcement PDF, report date 2026-06-30 (SGX FileID 900902 reportedly linked to announcement); verify its actual canonical URL and extract gross/treasury/net share counts with synthetic+live PDF tests. Never assume filename or values.
2. Reconcile G13 2026 issuer IR quote 12,063,642,274 with reporting-date net shares and dated buybacks; preserve provenance and dates.
3. Once Pages user-enabled, rerun deployment and verify public rendered site and current feed.
4. Work on S68 independent/same-issuer cross-report distinctions.
