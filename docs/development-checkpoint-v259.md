# VALUE HUNTER AI — v259 checkpoint (2026-11-15 JST)

## Start from real repo
- Repo `osawamas/value-hunter-ai`. Initial observed latest commit before v258 `3fdaac32854baa9146ccb88a39b35a68638674f2` (concurrent refresh workflows had updated the data feed since v257). Always re-read main, GitHub Actions, `docs/data/latest.json`, and checkpoint before editing. Feed timestamp last observed `2026-11-14T23:55:36.674442+00:00`, 7 financial records, ranking eligible 0.
- v257 checked 5WA conditional privatisation and P11 Chapter11 restructuring; no current live listing/price. v256 had 20 historic issuer code identities matched, not full exchange universe.

## v258 genuine user-facing searchable code page
- Created `docs/sgx-historical-code-search-v258.js` with browser search (symbol, name, ISIN) and Mainboard/Catalist filters using original SGX v253/v255/v256/v196 files and v257 material-event guard. Each row links its official SGX original static code source or SGXNet announcement, marks current listing and quote as unverified, flags 5WA/P11 event risk. Validates fail closed on conflicting class and investor rank, does not republish live SGX quote.
- Modified existing `docs/index.html` with live search/table and an external SGX official Securities Prices URL for users to check prices on SGX site themselves. No quote scraping/republication/automated source approval. Browser UI does not treat 20 indexed names as complete SGX.
- New regression `docs/test_sgx_historical_code_search_v258.js`, registered in `scripts/verify-evidence-v198.js` and CI triggers. Real GitHub Actions [43655931673](https://github.com/osawamas/value-hunter-ai/actions/runs/43655931673), job `132634323459`, **SUCCESS**; logs `PASS docs/test_sgx_historical_code_search_v258.js`, `Evidence smoke suite: 58/58 passed; rankings remain independently gated.`
- Commits: `ba0b09aa9c955d3e725e365a8bc5a9ac93e9ee6a` browser, `a5eb1783a3a7006a915927ec6f8fdbb3dd9e7467` HTML, `e8b4c6af358ea0ef431e0a082039d662f1b69f9b` test, `ae45d9ac605befdbf496ff9f65933a2c2ee66587` suite, `b1af773b7530e3a86dbefcd5a7297583ee3f89f9` workflow.

## v259 meaningful extension: **30 unique historically sourced SGX codes**
- Existing SGX October 5 reduced board-lot static table `docs/data/sgx-official-batch-seed-v196.json` contains 11 company/counter codes: D05, G07, H02, C07, J36, BN4, O39, K6S, S68, U11, V03. Prior v258 20 company source set includes O39; strict exact duplicate elimination yields **30 distinct codes**.
- Expanded `docs/sgx-historical-code-search-v258.js` via `buildExpanded` (retains v258 `build` backward compatible), adding 10 newly exposed SGX official boardlot sources to the searchable lookup. Those 10 rows are labeled `board: UNKNOWN`, as board-lot evidence does not itself establish market listing board; user can filter `市場区分未確認`. No inference of ISIN, current listing, quote or ranking. Browser count shows 30. Modified panel headings/filter in `docs/index.html`.
- New regression `docs/test_sgx_union_thirty_v259.js` checks 30 unique codes, 20+10 scope, 10 unknown boards, two risk flags, no ranking, and rejection of forged provenance, duplicate symbols and invented currencies.
- Commits: `42d38a938cf1b7b487be9ce62166c04bfc1539e5` browser, `0879e7008f077b742d49fd6cafeee9ae840df2a7` HTML, `c8c01506f5885e159b1b1a16945fda9eac09b68f` test, `40f9488048ee50e6c43fc7e5983cfbb1c28369a5` suite, `4f1e420cd0baa6afef806cb4cf55d764a427b8d1` workflow.
- Real Actions [43656149879](https://github.com/osawamas/value-hunter-ai/actions/runs/43656149879), job 132634979577, **SUCCESS**, logs `PASS docs/test_sgx_union_thirty_v259.js`, `Evidence smoke suite: 59/59 passed; rankings remain independently gated.`
- Note: 30 is just a hand-selected overlapping set of SGX original static and announcement historical identity codes; it is NOT a complete current SGX tradable security master. SGX official prices site `https://www.sgx.com/securities/securities-prices?code=stocks` is a viewer, not evidence of quote-redisplay rights; no live quote data added.

## Unresolved priorities / clear next tasks
1. SGX full dated, license-appropriate security-master file; not one-page SGX corporate indexed 20 or 11 reduced-boardlot subset. Aug 2026 604 listed securities vs indexed 727 company list are not directly comparable; don't compute an exact capture fraction.
2. Official UOB U11 2026-11-13 `SG261113OTHRHOAF` original, and OCBC O39 2026-11-12 `SG261112OTHRXH64` PDF `Anno_12Nov2026.pdf` originals. Secondary pages do not suffice to promote shares; do not fabricate source links/FileIDs.
3. SGX-licensed timestamped quote feed and redistribution/computation rights, independent accounting numbers including parent-equity and current shares; rankings remain blocked at zero.
4. 5WA / P11 official current status follow-ups (court, regulatory, suspension and exchange delisting orders), avoid treating planned dates as final.
5. GitHub Pages owner enablement still needed; green Actions with `pages=skipped` is not public deployment. v249/v250 local preview ZIP can be downloaded and smoke tested.
6. Next high-impact effort: verify SGXNet original source URLs directly and their returned issuer/ISIN/code text, or find real official bulk security master. Do not just add another decorative badge or status card.

## Next-thread copy/paste
VALUE HUNTER AI `osawamas/value-hunter-ai` をv259から継続。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v259.md`を読む。v257 SGX企業イベントリスク5WA/P11追加、57/57 PASS。v258は20社の取引コードを名前・コード・ISINで検索し公式SGXNet出典へ飛べるUI、58/58 PASS。v259は公式売買単位の11コードから重複OCBC O39を除いた10を追加し、検索画面30件へ拡張、区分不明はUNKNOWN表記。CI #43656149879 は59/59 PASS。30件は部分的な歴史資料でSGX全銘柄ではない。財務7・ランキング0、許諾付き株価・公式全銘柄・UOB/OCBC最新原本・独立財務数値検証・Pages本番公開は未完。優先度は原本の再取得と現在の上場・取引状態の検証。
