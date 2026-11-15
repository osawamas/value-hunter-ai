# VALUE HUNTER AI — v266 checkpoint (2026-11-15 JST)

## State / safe resume
- Repo `osawamas/value-hunter-ai`; start of this turn latest main `3b7c9467cb6799a753190a508ee53ffacf6a5ef5` v264 checkpoint. Background data-refresh Actions periodically push to main. **Always re-fetch actual latest main, Actions, `docs/data/latest.json` and latest checkpoint**. Never duplicate completed work.
- Previously: v262 SGXNet 19/19 original HTML issuer code/ISIN/ref directly re-fetched and SHA256 saved permanently; 11 SGX static board-lot codes, union 30 partial historical counters, not complete current SGX listed universe.
- v263/v264 matched 30 partial counter source records to seven financial issuers by exact SGX symbol; four intersection `D05,O39,S68,U11` (all financial ranking excluded), and 26 without financial record. Financial registered seven includes `G13,S20,S63` beyond the limited counter-source set. Dropdown shows all, finance-registered and finance-unregistered. v264 Actions #43657700568 62/62 PASS.
- Hourly automation already enabled for this repo. User explicitly wants multiple consequential tasks per run without manual “続けて”. Automation has max one-hour frequency; do not create duplicates. Some publishing workflows run concurrently.

## v265: actual integration from source-code search into financial detail pane
- `docs/app.js` adds a validated hash route `#issuer=O39` (also D05/S68/U11), via pure `parseIssuerHash`, `openIssuerFromHash` looking up `state.feed.records` by exact symbol. Rejects unknown/tampered hashes and symbols not registered, never promotes ranking. Hash is handled both on `hashchange` and when financial data loads, so deep link works even if feed loads after the link click. Shows existing complete financial details, source references and exclusion blockers and scrolls the detail pane.
- `docs/sgx-historical-code-search-v258.js` displays `財務詳細を見る` link only on the four financial-registered source research rows. Other 26 rows do not get a fake finance record.
- Regression `docs/test_sgx_detail_navigation_v265.js` tests pure hash parser for normal and injection-like inputs, source-link consistency, ranking protection.
- Commits `19aea7822783509b191bb8f3b69ba5a7c86c1dd6` app, `00178a7f8eeeb79e8542e7958f53052ca19b84c3` search, `f7fc506cada616e4571bb431eb1f78f03c173e9b` test, `530ae77e0cf68ee97d1a3d215f90b1217c63b237` suite, `93267485bb6f30e6c6718ca23d945abdac9f80dc` workflow.
- Real Node20 CI [43658353779](https://github.com/osawamas/value-hunter-ai/actions/runs/43658353779), 63/63 PASS.

## v266: downloadable filtered SGX source + finance evidence CSV
- `docs/sgx-historical-code-search-v258.js` added `exportDirectoryCsv()`, exporting exactly current table's search + board + finance filters. Columns include symbol, company, ISIN, board (including UNKNOWN), SGXNet/static origin, source URL/date, original HTML proof status, financial registered, actual financial exclusion reason codes, 5WA/P11 material event warning, and `ranking_eligible=false`.
- CSV uses UTF-8 BOM / Windows CRLF and escaped text with protection against spreadsheet formula execution `=+@-`. No unlicensed quote price, no invented active listing or valuation data. Button added to `docs/index.html` labelled `絞り込み結果をCSV保存`. The export rejects source rows with investment ranking/market eligibility wrongly enabled.
- Regression `docs/test_sgx_catalog_export_v266.js` checks 30 records + header, 4-record filtered export, zero rows, BOM, exclusions/provenance, formula injection and rejecting illicit rank promotion.
- Commits: `8d4c0b40c1e3b49533e67df36a8a7e9f03b4bbe0` feature, `1d0116a31bca918b3a73bdf79533117db6081e28` real BOM/CRLF fix, `89e7ca4c99c82317b836b3edcd6c6989981431d4` HTML, `7aa04c89c4e7c66efea2056b4912f4941174921e` test, `5dc442bb06901d5a22040d1cb4133e9d10168508` suite, `22f5b85fb480ca5384d5a08660e0f6dffbae7afb` workflow.
- Real Node20 evidence workflow [43658509567](https://github.com/osawamas/value-hunter-ai/actions/runs/43658509567), job 132642354385 **completed SUCCESS**, logs `PASS docs/test_sgx_detail_navigation_v265.js`, `PASS docs/test_sgx_catalog_export_v266.js`, `Evidence smoke suite: 64/64 passed; rankings remain independently gated.`

## No false completion claims
- Financial registered 7, ranking eligible still 0; none of the 30 historic counters is certified as currently trading and no live quote source with redistribution/computation rights has been integrated. Original SGX code evidence is not current share-count/price evidence.
- The complete dated official SGX issuer-security code master still missing. SGX 2026 Aug monthly 604 listed securities and search indexed corporate list 727 records refer to different scope/date.
- UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` exact original issuer buyback documents not obtained. Do not invent filing URLs.
- Original issuer financial independent verification, accurate ex-treasury shares, true PER/PBR, and daily investable ranks remain blocked. GitHub Pages `pages` job still historically skipped pending repo owner enablement; dashboard preview ZIP is available through Actions, but public URL must not be asserted live.

## Next high-impact batch
1. **Real-browser smoke test of new v265 deep link and v266 filtered CSV** using the preview ZIP, not just Node unit/DOM source assertion; catch runtime UI issues, check if browser can fetch all JSONs and actual navigation behavior. Add evidence artifact for browser job if available.
2. Prioritize authorized complete SGX security-code master, licensed quotes and current listing/issuer-share originals. Avoid multiplying small panels that can't enable investable rankings.
3. Polish financial data tooltips from untranslated exclusion code to Japanese reason dictionary; add accessible labels, verify across 4 registered and 26 unregistered.
4. Downloaded dashboard ZIP regression v250 should validate new script and CSV export UI dependency. Compare generated ZIP content/HTTP source with `docs/` latest after v266.
5. Verify latest GitHub Pages Settings prerequisite; do not blindly claim deployment from successful preview.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv266から継続。main、Actions、最新`docs/data/latest.json`、`docs/development-checkpoint-v266.md`から再開。v264までSGX公式部分30銘柄と財務7社の厳密コード照合（共通D05/O39/S68/U11の4社、未登録26件）、62/62 PASS。v265では30銘柄検索から財務登録4社の完全な財務詳細に飛ぶ`#issuer=CODE`ディープリンクを実装、v266では絞り込み30銘柄を原本・ISIN・株式コード・除外理由・リスク付きでCSV出力（式注入防止）を実装、CI #43658509567 64/64 PASS。原本SGXNet19/19 SHA検証はv262で完了。財務7、ランキング0は維持。次は実ブラウザUIとZIPで動作確認、正規全銘柄台帳、許諾付き市場価格、最新UOB/OCBC原本、独立財務監査、Pages所有者設定。自動実行は毎時設定済み、作業はまとめて複数進める。
