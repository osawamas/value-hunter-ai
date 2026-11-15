# VALUE HUNTER AI — v290 checkpoint (2026-11-15 JST)

## Resume
- Start by reading actual current main, Actions, `docs/data/latest.json`, this checkpoint and `docs/development-checkpoint-v289.md`. The hourly automation can push concurrently.
- v289 ranking-provenance guard and 79/79 PASS remain, formal ranking eligible 0 of 7.
- Latest verified v290 CI integrity #43669577022 SUCCESS **80/80**; another run #43669573265 SUCCESS. Browser ZIP workflow #43669559345 SUCCESS, source-data publishing #43669559381 SUCCESS, direct-open Chrome ZIP #43669559376 was still in progress when first checked.

## Implemented v290
1. `docs/data/sgx-market-license-review-v290.json` records official SGX Data Direct Market Data Policy page `https://www.datadirect.sgx.com/Market-Data-Policy`, current policy effective **1 July 2026**, vendor directory, contact data@sgx.com. Marked `NO_LICENSE_GRANT_OBTAINED`, no display/non-display/redistribution rights asserted. Do NOT treat policy existence as permission.
2. `scripts/check-ranking-license-evidence-v290.js` adds fail-closed date-bounded grant evidence on top of v289. Every formally ranked entry must have an actual explicitly marked executed grant, HTTPS proof, licensor, licensee, product, BOTH `BROWSER_DISPLAY` and `BACKEND_NON_DISPLAY_ANALYTICS` scopes, extra `REDISTRIBUTION` scope when applicable, valid calendar dates and quote date inside contract window, and licensed quote origin URL. Structural checks do **not** authenticate legal grant documents.
3. `docs/test_ranking_license_evidence_v290.js` tests actual data feed, no-license research state, valid calendar dates, negative cases and synthetic positive grant record. This is a fake fixture for tests, NOT a real SGX grant.
4. Registered v290 test in `scripts/verify-evidence-v198.js`; workflow watches relevant source files. CI #43669577022 **80/80 PASS**.

## Major blockers
- SGX dated complete official active universe unacquired.
- Market data display/analytics/redistribution licenses not granted. SGX policy does not imply rights; no ranking.
- Independent audited financial corroboration unresolved; OCBC/DBS/UOB second source only same issuer.
- Official original UOB Nov 13 `SG261113OTHRHOAF`, OCBC Nov12 `SG261112OTHRXH64` URLs missing; third-party mirrors are not official evidence.
- Formal investment ranking eligible remains **0 of seven**. No user action required for code; actual data licensing would require external approval.

## Next task
1. Check all real browser/ZIP Actions; investigate failure if any.
2. Explore authorized full SGX listed securities reference data and usable licensed quotes; document usable terms, not scraped substitutes.
3. Source independent accounting attestations and original share/corporate actions. Reconcile dated ex-treasury shares.
4. Keep existing hourly automation, don't duplicate.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` はv290まで実装。main・Actions・latest.json・development-checkpoint-v290.md確認。SGX公式規定は2026-07-01版、許諾未取得。v290は実行済契約の根拠URL・両利用範囲・期間・株価日付を検証するランキング防御を実装。CI #43669577022は80/80成功。投資適格0/7、SGX公式全銘柄、両用途許諾、第三者財務検証、UOB11/13・OCBC11/12原本取得を優先。毎時タスクは有効。
