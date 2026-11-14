# VALUE HUNTER AI — v103 checkpoint (2026-11-14 JST)

## Read before next development
Repository: `osawamas/value-hunter-ai`; starting point v102 was main `80ae135ce479cffc80719479692717604208015d`. Read main, latest Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-provider-quality-v103.json`, and this checkpoint. Do not repeat completed work.

## v103 completed on main
- Added `SGX_PDF_connection_probe/sgx_provider_audit_v103.py`, tests `test_sgx_provider_audit_v103.py`, and GitHub Actions `.github/workflows/value-hunter-v103.yml`.
- The independent v103 CI https://github.com/osawamas/value-hunter-ai/actions/runs/43547438813 **SUCCESS**. It ran unit tests and live StocksSG `?limit=200` response, asserted exact matching source SHA256 to the preexisting candidate sidecar, and committed `docs/data/sgx-provider-quality-v103.json` (`e00b271e8707ae2d9d63ba4d564740ea066315c4`).
- Raw 183 rows; 182 candidate companies; 1 excluded row. The excluded row is **index symbol `^STI`, name `Straits Times Index`, board `Benchmark`, is_active true**. It fails the company-ticker regex, appropriately excluded from company candidates. This is not evidence of a delisted issuer.
- For 182 accepted rows, provider `is_active` is true for all 182; false 0; unknown 0; provided `delisting_date` 0. These are strictly third-party assertions, **NOT exchange certification**. Observed status fields: `board`, `delisting_date`, `is_active`. No claim of SGX total market coverage.
- Diagnostics stay in separate file, with `ranking_eligible=false`, `promoted_to_financial_feed=false`. Do not add to `latest.json`, do not compute PER/PBR based on provider signals.
- Potential future improvement: explicitly tag `^STI` as a noncompany benchmark instead of only generic ticker-format rejection; add tests for benchmark guard, while handling unknown invalid codes conservatively.

## Exchange master research (incomplete)
- Official SGX page https://www.sgx.com/securities/securities-prices?code=stocks provides exchange securities list/search and a Download UI, but this session did not retrieve a machine-readable, dated complete official SGX master for automatic reconciliation. SGX Rulebook 7.1.1 defines official list as admitted/unremoved Mainboard, Global Listing Board and Catalist issuers: https://rulebook.sgx.com/rulebook/chapter-7-listing-and-quotation. Do not infer full 182-company listing proof from the SGX securities-prices web page.
- Official SGX trading page https://www.sgx.com/securities/trading explicitly lists several bank tickers (D05/O39/U11), but does not certify the entire candidate set.

## November 2026 bank announcements (research only, NOT PRIMARY-SOURCE-VERIFIED)
- UOB 13-Nov announcement reference `SG261113OTHRHOAF`, secondary syndication https://c2charts.shareinvestor.com/news/news.html?nid=515671689&source=regional_sgxnet. It reports 13-Nov buyback 34,000 cancelled, issued shares excluding treasury 1,646,677,591; treasury 14,548,000. SGX-hosted original for 13-Nov was **not located/verified**. The existing 12-Nov SGX primary https://links.sgx.com/1.0.0/corporate-announcements/MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d gives issued excl treasury 1,646,711,591; arithmetic difference 34,000, but this crosscheck does not promote 13-Nov values to verified.
- OCBC 12-Nov reference `SG261112OTHRXH64`, secondary listing https://c2charts.shareinvestor.com/news/news.html?nid=515671461&source=sg_sgxnet with attachment named `Anno_12Nov2026.pdf`. **SGX hosted attachment/PDF NOT recovered**; no share count promotion.

## Dated market quote lead (research only)
- SGX homepage https://www.sgx.com/ itself displayed 13-Nov-2026 17:16 SGT delayed bank snapshots D05 69.90 SGD, O39 28.53 SGD, U11 37.75 SGD at the time of web retrieval. This is a **human-readable exchange page lead, not a stable, symbol-validated, timestamp-validated automated feed**. It must not alter `latest.json` price, market cap, PER/PBR, or rankings until durable machine parsing, timestamp and ticker checks, and secondary crosschecks are proven.

## Remaining next steps (v104+)
1. Find a durable, downloadable **official dated SGX security master** and reconcile symbols/ISIN/security type; preserve separate candidate and official-verification fields.
2. Investigate accessible links for UOB Nov-13 original and OCBC Nov-12 original PDF, verify SGX host and announcement reference and filing date with content; until then remain research leads.
3. Design an SGX quote extractor that requires explicit ticker/currency/exchange timestamp and refuses stale or ambiguously dated quotes. Test replay and freshness boundaries without changing financial rankings.
4. Maintain `ranking_eligible_count=0` until independent financial, current share and quote verification is complete.
5. Document new code/test and Actions success/failure with exact run IDs.

## Handoff text
VALUE HUNTER AI `osawamas/value-hunter-ai` をv103の続きから再開。main、Actions、`docs/data/latest.json`、`docs/data/sgx-universe-candidates.json`、`docs/data/sgx-provider-quality-v103.json`、`docs/development-checkpoint-v103.md`を読む。v103 Actions #43547438813成功。183件中除外1件は`^STI`株価指数（board=Benchmark）で、残り182件は第三者StocksSGのis_active=true。ただしSGX公式で上場確認済みとはしない。財務登録7社・ランキング0社は維持。SGX公式銘柄マスターの機械取得、UOB11/13原本、OCBC11/12 PDF原本、日時付きSGX株価取得の検証を続け、テスト後GitHubへ保存。未検証データはPER/PBR・時価総額・ランキングに使用しない。
