# VALUE HUNTER AI — v191 checkpoint (2026-11-14 JST)

## Starting state
- Confirmed main at v190 checkpoint commit `e435a7b33120ff94907f1e2ac05ed7e518022a13`. Read v190 checkpoint and v190 JS test.
- `docs/data/latest.json` was re-read after changes: updated 2026-11-14T10:41:19.226478+00:00, 7 issuers, ranking eligible 0, ranking disabled.
- Existing bank 3Q/9M source sums remain preserved in v186; no financial feed modification.

## v191 implementation
- Added independent workflow `.github/workflows/bank-corporate-actions-v191.yml` to main, commit `47980a108457d2b9bab99c009568fb74dec891bf`.
- It triggers on main pushes touching the corporate-action JSON, v190 JS regression, or the workflow itself; also supports manual workflow dispatch.
- Runs Node.js 20 on Ubuntu, `node docs/test_bank_corporate_actions_v190.js`. The test protects UOB Nov 11→Nov 12 -34,000 ex-treasury shares, preserves unverified status of UOB Nov 13 and OCBC Nov 12, and blocks manufactured shares and unauthorized licensed-quote flags.
- Fetched the workflow file back from main and confirmed its content.
- **Do not assert CI SUCCESS yet.** GitHub connector `fetch_commit_workflow_runs` returned [] for the v191 commit but that operation only covers PR-triggered runs, not push. Public web UI/API could not be inspected in this session. Need obtain actual workflow run status via GitHub Actions UI or more complete Actions API.
- The independent workflow does NOT alter Pages publishing. Pages remains disabled/unconfirmed per v189.

## Remaining priority
1. Verify bank-corporate-actions-v191 push workflow run jobs and status; fix any failures.
2. Obtain authoritative UOB Nov 13 SGX original notice and OCBC Nov 12 PDF; verify exact historical ex-treasury count. No secondary-source promotion.
3. Acquire explicitly authorized, timestamped SGX quotes with permitted downstream usage, and date-matched share counts, before publishing PER/PBR/market cap rankings.
4. Obtain dated official SGX full securities master; third-party 182 company candidate list is not complete.
5. Independent financial audit of G13/S63 and banks. Rankings remain at 0 until all gates pass.

## Copyable next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v191の続き。main、Actions、`docs/data/latest.json`、`docs/data/sgx-big3-bank-research-v186.json`、`docs/data/sgx-bank-corporate-actions-v190.json`、`docs/development-checkpoint-v191.md`を読む。v190ではUOB11/11・11/12のSGX公式買戻し株式数1,646,745,591→1,646,711,591をJSONとテストに保存。v191では `.github/workflows/bank-corporate-actions-v191.yml` を追加してv190のテストをpush時に実行する設定にした（commit `47980a10`）。テストのCI実行結果は未確認なので最優先で実ジョブ確認。UOB11/13とOCBC11/12の原本未取得、株価ライセンス未取得、公式SGX全銘柄マスターと独立財務検証も未完。登録7社・候補182社・適格0社、Pages未公開。未検証の評価値を正式ランキングへ使わないこと。
