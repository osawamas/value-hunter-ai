# VALUE HUNTER AI — v232 checkpoint (2026-11-14 JST)

## Start here
- Resume after `docs/development-checkpoint-v228.md`. Read latest main, Actions jobs, `docs/data/latest.json`, and this checkpoint before any work; do not repeat earlier steps.
- Latest observed feed `2026-11-14T14:40:55.478339+00:00`: 7 financially registered companies, 182 third-party company candidates, ranking enabled=false, eligible count=0. The official Oct-2026 lot-size subset (11 securities) and selected 41 multi-currency product groups /82 trade counters are different populations.
- Main after current work includes v229–232 changes; all new files on branch main.
- Unified `scripts/verify-evidence-v198.js` now lists **34 tests** and workflow `.github/workflows/bank-corporate-actions-v191.yml` triggers on v229/v230/v232 files.

## Critical discovery: official SGX issuer directory is NOT its securities-price table
- Found SGX `https://www.sgx.com/securities/corporate-information` and indexed `?page=24` issuer results. It exposes issuer company name, country, listing board and listed-date history, but is browser-dynamic; full export format and data redistribution permission are unknown.
- Official SGX `https://rulebook.sgx.com/rulebook/71-official-list` describes the Official List as issuers admitted to Mainboard, Global Listing Board and Catalist. The `securities-prices?code=stocks` view covers traded counters and market prices. A currency-specific security counter must not count as an additional issuer.
- Search also confirmed the official securities-price viewer has a Download control but displayed quote/volume/board data are not permissioned for public redistribution. Do not bulk scrape or promote to an official comprehensive master without source/rights checks.

## v229 offline security CSV intake end-to-end
- `scripts/audit-staged-sgx-universe-v229.js`: reads the private output of existing v199 raw-byte SHA CSV staging, invokes existing v202 instrument classifier, and compares only *code overlaps* with existing 182 third-party candidate codes and 7 registered financial symbols. It outputs a local audit JSON with number of counters by security class, duplicates across currency/type, unknown-type codes, code-overlap counts, original SHA and source provenance labels.
- Strict staging/evidence checks: expected schema and SHA, exact whitelisted identity fields only (rejects price/volume/extra JSON keys), no authenticated full-master/issuer identity/quote rights/ranking claim. No HTTP calls, no writes to `docs/`, output as a new file only.
- `docs/test_staged_sgx_universe_audit_v229.js`: synthetic CSV with AWX/XWA currency pair, GRN/GRE ETF pair, G13 registered code and stapled security. Validates strict quote exclusion, 3 potential equity counters, 2 ETFs, 1 stapled, and correct reference overlaps without treating code match as independent issuer verification. **PASS in V8 Node-compatible harness**.

## v230 separate offline issuer directory adapter
- `scripts/stage-sgx-issuer-directory-v230.js`: reads a manually normalized `Company Name,Country,Listing Board[,Listed Date]` UTF-8 CSV sourced from the SGX Corporate Information page. Raw original CSV SHA256 via existing v199 helper, validates official directory URL, names, country, board, exact ISO date when supplied and duplicate issuer names.
- Output contains only issuer name/country/board/listing date, **no inferred SGX trading code or ISIN**, no market data and no false official master/redistribution/ranking flags. Rejects accidental public output under `docs/`. No automatic fetch/scrape. The actual official export schema and permissions are NOT established.
- `docs/test_sgx_issuer_directory_v230.js`: synthetic issuer data verifies separate universe, strips Stock Code/Last columns, accepts Catalist and Mainboard, rejects duplicate/invalid dates/bad source link. **PASS in V8 Node-compatible harness**.
- Removed unused classifier import from v230. Official directory source currently indexed through web, but programmatic page fetch returned browser compatibility shim; issuer master data still not imported.
- New consolidated onboarding guide `docs/sgx-authorized-data-onboarding-v231.md` explains safe user-supplied authorized CSV inputs, output commands, raw evidence, and requirements before any promotion.

## v232 actual Node CLI integration regression staged in GitHub
- New `docs/test_offline_sgx_cli_v232.js` uses Node `spawnSync` on real three-step commands: `stage-sgx-csv-v199.js`, `audit-staged-sgx-universe-v229.js`, `stage-sgx-issuer-directory-v230.js`, against synthetic CSVs in a temporary directory.
- Checks raw input SHA256, exact counts, correct overlap, absence of quotes/unauthorized identifiers, no re-write of existing staging outputs (wx), and refusal to output under `docs/`. Cleans temporary files in a finally block.
- **Important**: v232 test file was syntax-checked with the V8 engine, but a native Node CLI subprocess test run / real Github Actions job **has NOT been observed**. The file is now included in the consolidated 34-test GitHub Actions suite for an eventual real run. Do not claim native Node success.

## Remaining blockers, prioritized
1. Actual GitHub Actions push-run logs and JSON result artifact `sgx-source-integrity-v218-results` are unavailable through current GitHub connector's PR-only commit-run wrapper. The 34-test CI result and v210 H02/V03 PDF-byte SHA probe remain unconfirmed. Local container cannot resolve GitHub/SGX hosts; attempted direct H02 original PDF download failed.
2. UOB 2026-11-13 official SGX share buyback `SG261113OTHRHOAF` and OCBC 2026-11-12 treasury notice `SG261112OTHRXH64` PDF `Anno_12Nov2026.pdf` remain unfetched. Syndicated UOB numbers and a UOB issuer IR alert exist, but cannot elevate to SGX official primary; v216 confirmed official UOB Oct20–Nov12 204,000-share buyback bridge.
3. Complete dated SGX issued-company list and security master, correct instrument/issuer mapping, public redistribution rights for downloaded identifiers and licensed timestamped quotes not established. Keep official static 41-group /82-code research separate from full master.
4. Independent numeric audit of G13/S63 profit/parent equity and historical corporate-action share count matching quote as-of dates; official H02/V03 PDF pages visually inspected but raw SHA missing. Formal stock ranking remains disabled.
5. GitHub Pages publication not verified/owner setting may be disabled.

## Next thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv232から継続。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v232.md`を読む。v223のH02親会社持分誤表示修正、v224〜228のSGX公式41商品82通貨別カウンター、v226ステープル証券分類まで完了。v229は手動で正規入手した証券CSVから株価を落として種類分類→第三者182候補・財務7社コードとの**仮照合**をローカルJSONで行う実装。v230はSGX公式Corporate Informationの発行体一覧向けに、会社名・国・上場市場・上場日だけを取る別の手動CSV取り込み器（証券コード推測禁止）、v231は手順書、v232は3コマンドを実Nodeで実行する結合テストを追加。v229/v230機能テストはV8互換環境でPASS、v232の構文検証PASS、実Node CLI/Actionsジョブは未検証。統合テスト34本登録、財務登録7・第三者候補182・公式限定11証券・ランキング適格0。原本PDF SHA、UOB11/13・OCBC11/12公式原本、SGX全発行体/全証券マスターと権利、時刻付き正規株価、独立財務検証、Pages公開が未完。済みの工程を繰り返さず、ソースと権利の確定・実データ拡張を優先し安全な変更のみmainへ保存。
