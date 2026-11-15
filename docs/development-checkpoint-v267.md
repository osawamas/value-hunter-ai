# VALUE HUNTER AI — v267 checkpoint (2026-11-15 JST)

## Verified baseline and automatic continuation
- Repo: `osawamas/value-hunter-ai`. At start of this turn latest main `3b7c9467cb6799a753190a508ee53ffacf6a5ef5`, v264 checkpoint. Background data-refresh jobs may push to main; always read latest commit, Actions, feed `docs/data/latest.json`, latest checkpoint before changing code. User explicitly wants multiple substantial tasks in each autonomous execution without manual “続けて”.
- Hourly automation `Automation_5cb3f22c5da88191a2dc9365d7a365d1` already enabled (max supported cadence), with multi-step delivery prompt. Avoid duplicate automations. Scheduled runs are discrete, not continuous execution.
- Prior v264: selected 30 SGX historical counter identities including 19 actual original SGXNet HTML SHA-256-verified sources + 11 static SGX reduced-boardlot entries (not SGX full master). Exact code union with seven financial feed records yields four matched finance names `D05,O39,S68,U11`, other 26 code catalogue entries lack a finance record. All ranking eligibility stays zero, no authorized live quote.

## v265: direct link into existing actual financial details
- `docs/app.js` adds constrained `parseIssuerHash("#issuer=O39")` and `openIssuerFromHash`: checked against loaded official existing financial feed and ranking-gated record. Hash works after delayed feed load and on hashchange, links exact code to full existing company detail (accounting, source links, exclusion reasons) without inventing a financial record. Uses `state.selected`, history selection and scroll. No arbitrary code or HTML injection.
- `docs/sgx-historical-code-search-v258.js` shows `財務詳細を見る` only for the four financial registered codes (D05/O39/S68/U11), links to `#issuer=CODE`.
- New `docs/test_sgx_detail_navigation_v265.js` checks financial overlap, hash parser rejects invalid input and click/display wiring.
- Commits: app `19aea7822783509b191bb8f3b69ba5a7c86c1dd6`, search `00178a7f8eeeb79e8542e7958f53052ca19b84c3`, test `f7fc506cada616e4571bb431eb1f78f03c173e9b`, suite `530ae77e0cf68ee97d1a3d215f90b1217c63b237`, workflow `93267485bb6f30e6c6718ca23d945abdac9f80dc`.
- Actual GitHub Actions [43658353779](https://github.com/osawamas/value-hunter-ai/actions/runs/43658353779) completed SUCCESS with 63/63 passed.

## v266: export current SGX research filters to CSV
- `docs/sgx-historical-code-search-v258.js` adds `exportDirectoryCsv`: exports exactly the visible user-filtered SGX code list (30 overall; 4 finance registered; 26 not registered). Includes source URL, date, ISIN, market segment (UNKNOWN where not verified), direct original HTML proof status, finance exclusion reasons, material corporate events, ranking disabled. UTF-8 BOM, CRLF and CSV quoting; protects formula injection (leading =,+,@,-). No unlicensed live price or PER/PBR.
- `docs/index.html` adds `絞り込み結果をCSV保存` button.
- `docs/test_sgx_catalog_export_v266.js` verifies counts, filters, BOM/CRLF, source columns, no pricing, malicious spreadsheet strings and ranking gate.
- Commits: implementation `8d4c0b40c1e3b49533e67df36a8a7e9f03b4bbe0`, BOM fix `1d0116a31bca918b3a73bdf79533117db6081e28`, HTML `89e7ca4c99c82317b836b3edcd6c6989981431d4`, regression `7aa04c89c4e7c66efea2056b4912f4941174921e`, suite `5dc442bb06901d5a22040d1cb4133e9d10168508`, workflow `22f5b85fb480ca5384d5a08660e0f6dffbae7afb`.
- Actual GitHub Actions [43658509567](https://github.com/osawamas/value-hunter-ai/actions/runs/43658509567) completed SUCCESS: **64/64 tests passed**. Prior checkpoint `docs/development-checkpoint-v266.md`, commit `4fe118afee1b3cdb3a92a62515227aeb3bbfa7a3`.

## v267: Japanese, mobile-readable ranking exclusion details
- Exports existing `reasons` dictionary from `docs/app.js` to read-only browser `window.VALUE_HUNTER_EXCLUSION_LABELS`, avoiding a second independent translation table. Commit `4afddbe0bfb6b17c3535f7aeb53d21dcd0f062ae`.
- Enhances `docs/sgx-historical-code-search-v258.js`: four financial-registered rows now have a clickable `<details><summary>除外理由を表示</summary><ul>...日本語理由...</ul></details>`, alongside finance-detail deep link. All strings from real feed and existing translation map inserted via `textContent` (safe), untranslated unknown codes fail to `要確認（CODE）`. Mobile readers no longer need desktop hover tooltip. Commit `9423017881cecaf6dd4b1006c8e8f14469e92a3f`.
- New `docs/test_sgx_japanese_exclusions_v267.js`, verifies actual dictionary English-to-Japanese mappings via VM, four financial records and safe source text DOM. Test commit `0ca891e8b0fdd84bfd2ae749a501ef402d05a0f3`. Added suite `9ef511d06c56a62d4a3df5ba5f1f337aee47f080` and workflow `a4c9096c17e775eabb4a6a8c5c3bcb541279d74f`.
- Initial v267 CI failed because old v263 test expected `financialExclusionReasons.join` whereas new Japanese mapping uses `financialExclusionReasons.map`. Updated regression without weakening source/financial protection: commit `30a336e46800b066ef1c054702121c6f2e43a29b`.
- **Final actual CI** [43658726050](https://github.com/osawamas/value-hunter-ai/actions/runs/43658726050), job `132643022044`, completed SUCCESS: `PASS docs/test_sgx_financial_join_v263.js`, `PASS docs/test_sgx_japanese_exclusions_v267.js`, **Evidence smoke suite: 65/65 passed; rankings remain independently gated**.
- Important: static/Node tests confirm functions, integration pathways and labels. A complete browser integration test (real hash navigation and CSV download) has not yet been executed; don't claim that.
- `docs/data/latest.json` feed at start 7 financial securities, ranking eligible 0. No unauthorized prices have been added and security-source identity is still not independent financial valuation.

## Remaining priority blockers and action items
1. Real rendered/browser smoke of financial deep links (click from SGX search and directly open `#issuer=O39` before data load), Japanese collapsible exclusions and filtered CSV download. Current tests include source/static/Node/VM, not full actual browser.
2. Actual dated complete licensed SGX security-code master, quote rights permitting SGX security data processing and redisplay, audited and parent-equity independent numeric corroboration, current share counts and timestamps. No invented live quotes or investable ranks. SGX official August 2026 604 listed securities vs indexed corporate info 727 entries are different scope/time, don't claim entire market covered.
3. UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` exact original SGX filings unacquired; don't invent links. Material status follow-up 5WA (conditional privatisation) and P11 (Chapter11 update).
4. Dashboard Pages publication not verified live: owner must GitHub Settings → Pages → Source GitHub Actions. Preview ZIP pipeline exists and is smoke tested by previous v250 but should be rerun with v267 new files. No claim site is public until Pages job actually succeeds.
5. In future automatic execution prioritize concrete usable production functionality, actual primary original verification and meaningful external-source checks over repetitive version/status panels. Continue multiple steps per hourly run, commit tested changes and write checkpoint.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv267から継続。最新main/Actions/`docs/data/latest.json`/`docs/development-checkpoint-v267.md`をまず読む。v262原本SGXNet19/19 SHA検証、歴史的SGX30コード検索、v264財務7社との厳密結合（共通4社D05/O39/S68/U11）。v265で財務詳細 `#issuer=CODE` ディープリンク追加、v266で出典・除外理由を含む絞り込みCSVダウンロード、v267で除外理由の日本語・モバイル展開表示。CI #43658726050 65/65 PASS。財務7、ランキング適格0。次は実ブラウザ＋最新ZIP E2Eテスト、SGX全銘柄マスター・適法な時刻付き株価・UOB/OCBC公式原本・独立会計検証、Pages owner setup優先。1時間ごとの既存自動開発は有効、重複作成しない。
