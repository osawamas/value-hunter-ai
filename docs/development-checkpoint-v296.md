# VALUE HUNTER AI — v296 checkpoint (2026-11-15 JST)

## First steps next time
Read current main commits, latest Actions, `docs/data/latest.json`, this checkpoint and `docs/development-checkpoint-v295.md`. An existing hourly autonomous development automation is already active: never duplicate. Concurrent writes may advance main.

## v296 actual work committed
1. New `docs/sgx-32-research.html`: separate Japanese-language navigable source directory for 32 historical SGX source identities (original dated SGXNet 19, static SGX code disclosures 11, October 2026 IPO admission 2). Linked it from the existing 30-code search section on `docs/index.html`; original 30 UI remains unchanged so prior regression contracts stay intact.
2. New `docs/sgx-32-research-v296.js` reuses original source builder `SGX_SOURCE_DIRECTORY_READONLY.buildWithOriginalProof` with the actual 7 existing JSON snapshots plus `docs/data/sgx-october-ipo-listing-v294.json`. Strict checks on feed (seven, ranking 0), original historical codes (30), IPO original identity pair (9DC ISIN SGXE96931105, MIM ISIN SGXE49931863). No false current-active status, licensed quote or ranking promotion. Search across ticker/name/ISIN, filter by 3 source kinds and finance registered/unregistered, and download displayed CSV with formula-injection escaping. Links open exact original source URLs.
3. New `docs/test_sgx_32_research_v296.js` tests 32 unique rows, 19+11+2 type filters, finance registered 4, code/ISIN search, CSV sanitization, tamper rejections and actual HTML navigation. Registered in `scripts/verify-evidence-v198.js`; workflow trigger watches new page/test/JS. **GitHub Actions #43675416510 SUCCESS 85/85**; another suite #43675412294 also completed successfully.
4. Critical offline fix: `scripts/build-file-preview-v279.py` now injects the existing `offline-data-v279.js` public snapshot fetch shim into both `index.html` and new `sgx-32-research.html` inside packaged file:// ZIP; original docs not mutated.
5. New `scripts/e2e-sgx-32-research-v296.mjs` performs *real Chrome* on both packaged HTTP ZIP and file:// preview: loads all 32, verifies 9DC/MIM ISIN and original URLs, source filter, live input search, downloadable CSV only filtered matching row, finance registered count 4 and JS runtime error-free.
6. Modified workflows `.github/workflows/release-zip-browser-v270.yml` and `.github/workflows/file-preview-v279.yml` to run this E2E. **HTTP extracted ZIP run #43675553254 SUCCESS**, artifact `value-hunter-local-preview-zip-v271` ID `14146361965`. **Offline file:// run #43675549537 SUCCESS**, artifact `value-hunter-direct-open-v279` ID `14145109978`. These actions are *real Chrome tests*, not simply Node smoke tests.
7. Main source commits (in chronological order): `0b6b9271` JS browser, `5b717469` HTML, `94736394` main-page link, `a66dd1dc` test, `6d56a17b` evidence suite, `d0c67ef6` trigger, `272fc822` offline shim, `3ca46473` E2E, `7d44f935` file Chrome workflow, `62ba1658` HTTP Chrome workflow.
8. No edit to `docs/data/latest.json` or third-party 182-candidate JSON, and no claim of a full official active SGX master, real investment rankings or licensed market quote.

## Still blocked; highest priorities
- Source original **October 2026 SGX Monthly Statistics** SGXNet PDF from alleged `SG261112OTHREO8V`, calculate raw bytes SHA256 and verify month-end count/scope. Current 605 count is secondary-reported only.
- Obtain reusable current **complete SGX listed security master** and explicit license scopes for browser display, backend non-display analysis, and any redistribution; not granted.
- Independently verify additional issuer financial statements, ex-treasury shares, and bank Nov13 UOB/Nov12 OCBC original filings. Investigate 9DC/MIM actual IPO-prospectus audited past financial statements as source material, without implying outside independent financial audit.
- Registered financial records seven, formally ranking eligible **0 / 7**.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v296の続き。main・Actions・docs/data/latest.json・docs/development-checkpoint-v296.mdを読む。v296では原本19件＋SGX静的11件＋2026年10月上場原本2件の32銘柄を検索・出典種別/財務登録絞り込み・CSV保存できる日本語専用HTMLを実装し、メイン画面からリンク。オフラインZIPの新ページにも固定JSONを供給するよう修正。CI #43675416510 85/85 PASS、実Chrome HTTP配布ZIP #43675553254成功、file://ダブルクリックZIP #43675549537成功。配布artifactも存在確認。正式ランキング0/7、全SGX現行マスター・株価表示分析許諾・独立財務検証は未完。次は10月統計PDF原本・IPO2社監査済財務・正規フル台帳を優先。既存毎時自動開発タスク有効、重複設定不要。
