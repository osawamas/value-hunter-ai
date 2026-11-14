# VALUE HUNTER AI — SGX official directory staging v252

This workflow is **an input validator**, not an official SGX listing database or a source licence. It does not scrape the exchange or assert complete coverage.

## What has been found
- SGX's corporate information directory: https://www.sgx.com/securities/corporate-information
- Example paginated index: https://www.sgx.com/securities/corporate-information?page=24
- SGX securities prices viewer: https://www.sgx.com/securities/securities-prices?code=stocks (separate from an issuer master; price redisplay permission not established)
- Historical SGX August 2026 monthly report gives 604 **listed securities**, not an issuer/code list. No exact one-to-one comparison with 182 third-party company candidates is valid.

## Preparing actual input
Before running, source a real dated official SGX list, inspect its scope and permission, and normalize only **known** fields into a UTF-8 CSV whose exact header is:

```csv
Trading Code,Trading Name,Listing Board,Traded Currency
```

Supported listing boards: `MAINBOARD`, `CATALIST`, `GLOBAL LISTING BOARD`. Use standard ISO-like uppercase currency codes accepted by the validator. Quote CSV fields containing commas. **Do not claim this header is SGX's native export format.** It is the application's required normalized input schema. Do not fabricate missing trading codes, names, boards or currencies from the August 604 summary.

```sh
node scripts/stage-sgx-official-directory-v252.js /path/to/verified-export.csv 'https://www.sgx.com/securities/corporate-information' 2026-11-15
```

Output: `build/research/sgx-official-directory-staging-v252.json`, not `docs/data/latest.json`. It records the input's SHA256, snapshot date, source URL, codes absent from the 182 third-party candidate pool and codes absent from the 7-company financial feed.

**Trust boundary:** Even a successfully imported file remains `MANUALLY_SUPPLIED_UNREVIEWED_CSV`. Full SGX completeness, code-by-code primary provenance, source licensing, independent accounting verification and investable ranking all stay FALSE. A later workflow must verify original bytes, source terms, actual dated list scope, and per-security identity before promoting anything.

## Unresolved
- Current complete, dated SGX master export and permission to reproduce it remain to be established. An indexed SGX website page is not, by itself, a verified machine-readable whole-exchange master.
- UOB 2026-11-13 and OCBC 2026-11-12 original SGXNet filings are still unacquired. Licensed current SGX quotes also absent.
