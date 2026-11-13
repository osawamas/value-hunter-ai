# VALUE HUNTER AI — v45 checkpoint (2026-11-14 JST)

## Completed
- v44 S68 FY2026 audited issuer PDF extraction and scheduled financial pipeline integration.
- G13 FY2025 official results: issued 12,094,026,824 minus treasury 8,121,350 = outstanding 12,085,905,474 at 2025-12-31.
- v45 S68 Annual Report as of 2026-09-01: issued 1,071,642,400 minus treasury 798,916 = 1,070,843,484.
- Added valuation arithmetic protection and unit tests for share-count basis.
- Combined dashboard refresh Action 43494620350 succeeded; published docs/data/latest.json carries S68 LIVE_ISSUER_FY2026_PDF and issued_excluding_treasury.
- Rankings remain disabled while independent financial and owner-equity verification is incomplete.

## Unresolved, do not claim verified
- G13 issuer IR as at 2026-08-14 displays 12,063,642,274 Issued & Paid-up Shares, but that page does not establish treasury-share deduction; retain TREASURY_SHARE_BASIS_UNCONFIRMED.
- S68 share-count snapshot is documented, but annual-report share-count extraction itself is not automated.
- S68 second-document revenue and shareholder-profit comparisons remain unmatched.
- Repeated GitHub Pages workflow failures (zero jobs) remain separately unresolved.

## v46 priorities
1. Find dated G13 2026 gross issued/treasury/net shares on official disclosure and reconcile date.
2. Automate the S68 annual report shareholding table with precise 1 September 2026 date.
3. Investigate Pages workflow parsing/deployment failures.
4. Validate S68 second-issuer document crosschecks, keeping same-issuer vs independent distinct.
