# VALUE HUNTER AI — v51 continuation checkpoint (2026-11-14 JST)

## Current verified GitHub state
- S68 FY2026 income and balance extracted from official SGX audited results PDF with SHA256, compared to expected audited amounts.
- S68 annual shareholding statistics as of 2026-09-01: gross 1,071,642,400; treasury 798,916; net 1,070,843,484. Direct issuer annual PDF parsing, SHA and reconciliation are reflected in docs/data/latest.json.
- G13 official 1H2026 results as at 2026-06-30: gross 12,094,026,824; treasury 30,384,550; net 12,063,642,274. Treasury rollforward 8,121,350 - 7,567,000 + 29,830,200 = 30,384,550. Official source PDF SHA256 3b7f3ce3ebc648f419b5077c85386673cfa8d10d6025dfc8e6c437fad6144a77.
- G13 IR site displays same net count but IR update 2026-08-14 is NOT the PDF share-count as-of date: use 2026-06-30.
- S68 2026 audited results were cross-checked to separate 2026 annual report issuer PDF: FY2026 operating revenue 1,559,469 SGD thousands and attributable profit 698,411 SGD thousands; both match. This is second issuer document, NOT independent third-party verification.
- In public feed, S68 and G13 have issued_excluding_treasury basis, documented treasury and gross figures, source PDF SHA and dated status. Both retain financial independent verification and parent equity exclusion flags. Investment rankings remain disabled.
- CI v29 updated with v44-v50 tests and live official PDFs. Safe non-force push rebase prefers newly generated docs/data on collisions.

## Remaining blocks and next tasks
- Independently verify scope, source and auditor opinion of attributable parent equity before permitting verified PBR or ranking eligibility.
- Extend the live SGX issuer catalog safely beyond S68, G13, S20, S63 without replacing missing prices/financials with fabricated zeros.
- GitHub Pages site is NOT enabled. The connected GitHub Actions token cannot create it (Resource not accessible by integration). Repo owner needs one-time Settings > Pages > Build and deployment > GitHub Actions. Pages workflow now checks setup and skips deployments until the site is enabled.
- The scheduled daily VALUE HUNTER continuation automation has been updated to keep iterating through verified improvements during each run, while preserving GitHub state.
