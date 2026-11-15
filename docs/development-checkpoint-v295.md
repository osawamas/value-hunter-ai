# VALUE HUNTER AI — v295 checkpoint (2026-11-15 JST)

## Resume
- Always start by reading current main, latest Actions, `docs/data/latest.json`, and this checkpoint. Hourly automation is already enabled: no duplicate scheduling.
- v294: 2 original SGX-ST October IPO listing confirmations: Deluge 9DC ISIN SGXE96931105, Mi Material MIM ISIN SGXE49931863. 83/83 integrity PASS and Chrome ZIP successful.
- Formal finance feed still seven registered symbols and **ranking_eligible_count=0**. No full licensed SGX quote feed or complete active master.

## v295 implemented and committed
1. Inspected existing `docs/sgx-historical-code-search-v258.js` `buildExpanded` for **30 separate historical exchange-related codes** and `docs/data/sgx-universe-candidates.json` **182 unverified third-party candidate companies**. Neither 9DC nor MIM appeared in the third-party 182. Never count 182 as official.
2. New `scripts/build-sgx-ipo-candidate-union-v295.js` reuses real v259 historical 30-code builder, v294 original SGX-ST IPO verifier, 182-candidate feed and actual seven-record financial feed, strictly rejects code duplicates and source/ranking promotions, builds **32 distinctly identified historical SGX codes**, tags two IPOs as direct SGX-ST admission events with original source URL/ISIN/date, does not claim current active listing nor complete universe.
3. `docs/test_sgx_ipo_candidate_union_v295.js` validates 30+2, absence of 9DC/MIM in outdated third party 182, 32 unique codes, IPO URLs/ISIN, fails for duplicate/invalid source or accidental ranking promotion. Registered in `scripts/verify-evidence-v198.js`, workflow path watching.
4. CI integrity Actions **#43673923106 SUCCESS 84/84** and #43673920669 SUCCESS.
5. New workflow step in `.github/workflows/bank-corporate-actions-v191.yml` runs the actual staging CLI and retains generated JSON under GitHub Actions artifact `sgx-thirty-two-historical-candidate-stage-v295`. Workflow run **#43673969116 was in progress** at checkpoint creation; verify success / artifact before claiming it.
6. Earlier v295 HTTP ZIP #43673905910 SUCCESS, double-click file Chrome #43673905870 SUCCESS, dashboard publish workflow #43673905879 SUCCESS. These runs precede final artifact step, so do not imply newer code was tested for browser.
7. Commits: `0fad208dc89d69a6e25c8a68cf7486b90d61eb63` union builder, `d4406bde073603fe9874c040a63ee45112263073` negative test, `1310aa8d66eb01a66c6a48083f8863664fb4cd25` suite, `93da656a0553d727e1a41d0f4b05d79aee56a1e2` workflow path, `bbad3d05833568249a7358920df2f20b42ea1a91` artifact staging step.

## Not resolved
- This is **32 historical code identities**, not 32 independently audited current investable stocks; only 2 additional official October admissions. No change to `docs/data/latest.json` or 182 third-party candidate file.
- October 2026 official SGX Monthly Statistics PDF original (SG261112OTHREO8V) not downloaded; 605 October total only secondary report.
- Neither actual SGX current complete security master nor display/non-display market price permission acquired.
- Independent financial verification, ex-treasury share count original UOB Nov13 and OCBC Nov12 outstanding.

## Next
- Verify Actions #43673969116 actual artifact. If successful, use the stage as input for a Japanese-language 32-code searchable evidence explorer or review issuer financial filing for 9DC/MIM; do not imply 32 code list is official complete universe.
- Prioritize original SGX October statistics PDF, legitimate active SGX master/market license and independent financial evidence, rather than cosmetic release increments.
- Do not make formal ranking eligible without verified rights and accounting evidence.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v295から継続。main/Actions/latest.json/development-checkpoint-v295.mdを読む。v295で既存過去のSGX資料30コードに公式上場イベント2件 9DC/MIM を重複・ISIN・原本URL・日付検査付きで統合し、32件の歴史的コード調査台帳を生成するJSと負例テストを追加。旧第三者候補182にはIPO2社がいなかったが、182件ファイルは未改変。CI #43673923106 は84/84 PASS。統合JSONをActions artifactへ出力する追加workflow #43673969116は最後に結果確認。正式ランキング0/7、SGX全銘柄原本・株価利用許諾・独立財務検証は未完。既存毎時タスク有効。次はCSV/JSON成果物の実際の確認と原本財務・上場マスターの取得。
