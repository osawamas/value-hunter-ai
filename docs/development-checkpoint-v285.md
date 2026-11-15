# VALUE HUNTER AI — v285 checkpoint (2026-11-15 JST)

## Resume
- Repo `osawamas/value-hunter-ai`. Read latest main, GitHub Actions, `docs/data/latest.json` and this checkpoint first: concurrent hourly tasks and source refresh jobs may commit to main.
- Latest previously checked checkpoint `docs/development-checkpoint-v284.md`, main SHA `3ccc2a1c0b0f610be2b19f5fd218dcada5798d32`. Base finance feed 7 issuers, ranking eligible 0. Partial 182 third-party candidates; 30 historically sourced SGX names/codes including 19 SGXNet original HTML proofs and 11 SGX static page-indexed identities (NOT direct HTML verified).
- User explicitly wants autonomous fast progression. Existing hourly automation enabled at maximum interval, avoid duplicates and don't say continuously running between scheduled jobs.
- Prior user-facing completion estimate was **subjective ~45% overall**, ~80% interface/distribution and ~20% automated investment ranking core. It is not an engineering estimate with target date. Progress toward licensing and independent source readiness remains slow even when UX grows.

## Original-source check this run
- UOB 2026-11-13 `SG261113OTHRHOAF` secondary ShareInvestor announcement https://c2charts.shareinvestor.com/news/news.html?nid=515671689&source=regional_sgxnet; exact original `links.sgx.com` URL **still not found** from web search. Secondary reported 34,000 shares bought/cancelled and 1,646,677,591 ex-treasury shares after Nov13. Do NOT mark independently official.
- OCBC 2026-11-12 `SG261112OTHRXH64` secondary notice https://a.siasset.com/news/news.html?nid=515671461&source=sg_sgxnet names `Anno_12Nov2026.pdf`. Its exact SGXNet original file URL **still unlocated**; do not invent one, parse or certify those shares.
- 2026-11-12 UOB official Nov12 original IS SHA-verified from v284: 7,612 bytes SHA-256 `02722c970c4200e6507d60fbaa5458a2bcf43d96686f5111853bffb800e6e8e2`, 1,646,711,591 shares issued excluding treasury after event. This historical value is NOT automatically the current shares. Earlier v284 74/74 tests; original replay GitHub Actions #43664272047, source JSON `docs/data/uob-original-12nov-share-count-v284.json`.

## v285 substantial user workflow: side-by-side user-entered bank valuation
- New `docs/bank-manual-compare-v285.js`, added new table/form section in `docs/index.html`: three rows DBS D05, OCBC O39, UOB U11 allow user-entered SGD price, source price date, issued shares excluding treasury (explicitly self-declared) and dated share count. One click outputs comparable illustrative FY2025 parent profit-based PER, parent equity-based PBR and market cap SGD, sorted by **illustrative PBR low-to-high**. Links every original FY2025 issuer PDF with SHA. Warns on cross-bank date differences and quote/share-date conflicts. Most importantly clearly says **NOT an investable rank**, licensed quote feed not used, user inputs never sent/saved to server, feed/rank remains unchanged.
- Reuses original `docs/bank-scenario-v277.js` strict bank financial and manual-input validator (exposed as `window.VALUE_HUNTER_MANUAL_BANK_CALCULATE`) instead of a parallel unverified valuation formula.
- New `docs/test_bank_manual_compare_v285.js`: exact three banks, PBR sorting, source SHA and refusal of missing/duplicate/invalid symbol, zero/invalid prices, invalid dates, missing share counts and a feed ranking promotion. Registered in `scripts/verify-evidence-v198.js` and `.github/workflows/bank-corporate-actions-v191.yml`.
- Commits: new module `83f76dba7e9c2c12decc346246c28a608472c36d`, shared vetted calculator `b728486da63c3376866aa25fbfa9f1069df938c7`, UI `9bf350ffe95d1eb71a6827405827ac9019a75e19`, test `ebb95f03f110f5eff05f3cf95e16265d2e33c7e7`, suite `1de6584f4cf26f94ca6a312f89826c8f3cfa6d89`, workflow `6162cb622cbaef1b88ff6ef972d28d3d64c25c06`, real Chromium test `0c3598025e151b7e7f05db6263d8ddf7673f7ae4`.
- **GitHub Actions run #43665316765**: `PASS docs/test_bank_manual_compare_v285.js` and **Evidence smoke suite: 75/75 PASS**, no ranking promotion.
- **Actual Chrome E2E #43665350743** SUCCESS (full dashboard and v285 inputs).
- **Actual file:// double-click standalone ZIP full Chrome #43665350692** SUCCESS. Prior artifact name `value-hunter-direct-open-v279` retained but build includes latest modules.
- Latest HTTP ZIP after E2E #43665350750 was still in progress at last poll, check before calling verified.

## Major blockers remain
1. Complete dated official SGX master (active security instruments, not partial corporate indexing); source redistribution rights.
2. Licensed current date-stamped SGX equity quotes with both browser display AND back-end/non-display analytics permission. Do not insert market prices scraped from community sites or listing pages.
3. Original UOB 13-Nov and OCBC 12-Nov share/treasury filings; verify current shares excluding treasury, not just past dates, plus issuer PDF independent evidence.
4. Independent profit/equity figures and full 7 + SGX universe historical accounting data validation; formal ranking remains zero.
5. GitHub Pages owner Settings enablement, currently ZIP works offline file://. Need actual Pages publish job success to claim public deployment.
6. Avoid spending all hourly work on repetitive ranking blocker dashboards, cosmetic versions or additional fake checks. Focus source acquisition and licensed data.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv285から継続。まずmain、Actions、最新`docs/data/latest.json`、`docs/development-checkpoint-v285.md`を読む。v284はUOB 11/12 SGX原本SHA256確認、財務銀行3社2024/25比較、74/74 PASS。v285では手入力株価＋自己株式控除後株数を銀行3社D05/O39/U11まとめて入力し、参考PER/PBR/時価総額を横比較する画面を実装、単一銀行の厳密計算関数を再使用。PBRの低い順でも正式投資ランキングではなく、未検証入力は外部配布も保存もされず、ランキング0を維持。GitHub Actions #43665316765 は75/75 PASS、実Chromium #43665350743 SUCCESS、file:// ZIP #43665350692 SUCCESS。UOB 11/13原本SG261113OTHRHOAF・OCBC 11/12原本SG261112OTHRXH64は今回の公的リンク検索でも取得できず、第三者掲載のみ。次は正規SGX全銘柄台帳、許諾付き株価、最新原本株数、独立財務照合に注力。毎時自動開発は継続有効。
