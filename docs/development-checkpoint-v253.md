# VALUE HUNTER AI — v253 checkpoint (2026-11-15 JST)

## Resume
- Repo `osawamas/value-hunter-ai`, first observed main `b0317651992fd9e813c3f7eb94d3943d4e9388b4` (v252 checkpoint). Re-fetch latest main, Actions and `docs/data/latest.json` because concurrent work possible.
- v252 already developed local normalized CSV staging with security-code/board/currency/date checks; test 52/52 passed. Do not repeat without an actual source file.
- Financial feed last observed 7 records, rankings disabled and eligible 0. Official full SGX master and licensed quotes still unavailable.

## Actual new public SGX issuer name data
- Search-indexed SGX official corporate info page `https://www.sgx.com/securities/corporate-information?page=24` visibly reports entries **461 through 480 of 727 records** with issuer name and Mainboard/Catalist segment. Search-indexed content includes 20 named companies, from OCEANUS GROUP LIMITED to PACIFIC CENTURY REGIONAL DEVTS, including OVERSEA-CHINESE BANKING CORP.
- Direct opening that same URL with lightweight web fetch yielded the SGX browser-unsupported shell, **not the source page body or all records**. The 20 values are therefore provenance-qualified `SEARCH_ENGINE_INDEXED_OFFICIAL_SGX_PAGE_NOT_RAW_DOCUMENT`, not verified primary original bytes. This is not evidence of source CSV/code download rights.
- Saved all 20 named companies and listing boards into `docs/data/sgx-corporate-indexed-page-v253.json` (commit `d68ff642ea1f2c11977e0fcbe7b4f6cdf9fae21e`). All `trading_code:null` and `trading_currency:null`; no inference from company name or other sources. Each entry has page ordinal 461–480 and false financial/ranking promotion.
- **Do not equate 727 company directory hits with 604 listed securities (SGX August 2026 month-end v251): different time, definition, and direct-verification level.** No source-specific as-of date for the 727 indexed page is verified.
- Search also found official CDP securities lending pool at `https://www1.cdp.sgx.com/sgx-cdp-web/lendingpool/show?lang=en` with actual CDP *security codes* and names, dated Nov14 2026. These four-character codes are NOT proven identical to SGX trading counters and the lending pool is NOT the full listed universe; **do not merge these into trading codes**. A third-party `dividends.sg` site states it uses SGX monthly list for currently traded filtering, but this does NOT supply official source file or redistribution permission. Separately, the SGX price-viewer website permits browsing/downloading affordances, but redisplay/data-feed rights remain unverified.
- Created test `docs/test_sgx_corporate_indexed_v253.js` (commit `ebe6bba4b0b81479ce46c94bb10c75410e3f57fb`), preserving named-board-only nature, 20 unique names, exact page ordinals, null code/currency, false independent provenance and ranking. Registered in `scripts/verify-evidence-v198.js` (`82ddd30755186e4f51a871def1991b2965dcfcab`), workflow `.github/workflows/bank-corporate-actions-v191.yml` (`e96aa0c874cc4f24fc5b2e4eaab2628a38d0bb68`).
- Actual GitHub Actions run [43621908828](https://github.com/osawamas/value-hunter-ai/actions/runs/43621908828), job 132529239926 completed SUCCESS, log `PASS docs/test_sgx_corporate_indexed_v253.js`, `Evidence smoke suite: 53/53 passed; rankings remain independently gated.`

## Priorities
1. Acquire and document an **actual** complete dated SGX security-code master, using an authorized original export/API rather than indexed pages, manually generated examples, or the CDP securities lending pool. Reuse v252 importer only once grounded source bytes and license verified.
2. Obtain SGX UOB 2026-11-13 `SG261113OTHRHOAF` original share buyback and OCBC 2026-11-12 `SG261112OTHRXH64` original attachment; only syndicated mirrors found so far. Do not promote unknown latest outstanding shares.
3. Secure timestamped real price-feed legal access, calculation and public redistribution rights; independent financial numeric/audit verification. Keep ranking eligible 0.
4. GitHub Pages public publishing still skipped until owner settings enable Pages > Source GitHub Actions. ZIP preview works but is not public website.
5. Prioritize verifiable original source *data acquisition* and actual service usability over repeatedly adding display panels.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv253から継続。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v253.md`を読み既済作業を繰り返さない。v252は公式一覧の規格化CSV手動入力器と実CLI動作テスト（52/52）。v253はSGX Corporate Information公式ページの検索インデックスから20社（461〜480／全727件と表示）の会社名とMainboard/Catalist区分を新しいJSONに保存。直接HTML取得はブラウザ非対応で失敗、取引コード・通貨は未取得なので全件null、全銘柄とは扱わない。SGX2026年8月上場証券604件とも母集団が違う。Actions #43621908828 53/53 PASS。財務7、ランキング0。残る最大課題は公式取引コード完全一覧の取得、合法な株価の接続、UOB11/13・OCBC11/12原本、独立財務検証、Pages設定。
