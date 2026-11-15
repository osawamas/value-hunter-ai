# VALUE HUNTER AI — v289 checkpoint (2026-11-15 JST)

## Resume
- Read latest main, Actions, `docs/data/latest.json`, and `docs/development-checkpoint-v288.md` first. Concurrent hourly automation can change main.
- v288 already established three same-issuer second-publication corroborations for OCBC/DBS/UOB; 78/78 PASS, real Chrome and file:// ZIP worked. Same-issuer corroboration is NOT independent financial verification.
- Ranking eligible remains 0 of seven; SGX complete official dated active master, licensed display+non-display quote source and true independent evidence remain absent.

## v289: actual feed-level fail-closed ranking provenance
- Implemented `scripts/check-ranking-provenance-v289.js` to check published `docs/data/latest.json` records for duplicate symbols, eligible counts and flag synchronization, disabled-record scores, and for any promoted investment ranking entry: positive ex-treasury share count, dated quote/share fields, non-unofficial quote source, explicit display AND non-display analytics licensing, independent financial verification evidence, finite ranking score, and no exclusion reasons.
- Added `docs/test_ranking_provenance_v289.js` with actual feed and mutation cases for unlicensed quote promotions, ineligible scores, duplicated symbols, count mismatches, ranking flag mismatches, and a synthetic fully-evidenced valid promotion.
- Registered test in `scripts/verify-evidence-v198.js` and trigger paths in `.github/workflows/bank-corporate-actions-v191.yml`.
- First Actions #43668269594 and #43668272755 failed 78/79 because escaped date regex inadvertently matched a literal backslash. Fixed at commit `751e7a7d6cbe6bd8dbadb0e4ded7d567670f2bae`. **Final retest #43668335776 SUCCESS: 79/79 tests passed**, after date regex repair.
- This is a gate and CI regression, not new licensed quotes, independent audit, active SGX universe or new ranking-eligible issuers.

## Source search
- UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` still lack verified SGX original file URLs. Found only third-party listing and quote histories; do not promote those to original evidence.

## Next
1. Check Actions #43668335776, fix regressions if failed.
2. Seek actual original SGXNet files and permitted complete active SGX securities listing, research licensing for both display and non-display.
3. Do actual issuer accounting independence verification; keep ranking strict.
4. Maintain single existing hourly task; don't duplicate.

## Handoff
VALUE HUNTER AI osawamas/value-hunter-ai をv289から続ける。main・Actions・docs/data/latest.json・docs/development-checkpoint-v289.mdを読む。v289は未許諾株価や独立検証不足の財務を正式ランキングへ混入させないための実フィード検証モジュールと変異テストを追加。最初のCI 78/79失敗は日付正規表現の二重エスケープで、commit 751e7a7 で修正。最新CI #43668335776 は79/79 PASS。適格0社のまま。SGX公式全銘柄台帳、株価の表示・解析両許諾、UOB11/13・OCBC11/12原本、財務独立照合を優先。既存毎時自動タスク有効。
