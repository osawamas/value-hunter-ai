# VALUE HUNTER AI — v235 development checkpoint (2026-11-14 JST)

## Resume source of truth
- Read latest main, real GitHub Actions runs, `docs/data/latest.json`, `docs/development-checkpoint-v235.md` and then prior `docs/development-checkpoint-v232.md`. **Do not redo** v189–v235.
- Main before this checkpoint `7bdaf6a53085f86960126e16deb1b217e5b47729`.
- Latest `docs/data/latest.json` `2026-11-14T15:05:20.502940+00:00`: registered financial 7, ranking eligible 0, ranking disabled; candidate 182, official 11 security lot-change research and 82 dual-currency counters are different population scopes.
- Major new discovery: `mcp__GitHub__fetch` supports public REST collection `https://api.github.com/repos/osawamas/value-hunter-ai/actions/runs?per_page=...` and run subresources `/actions/runs/{id}/jobs` and `/artifacts`. Earlier checkpoints claimed Actions push-job status unavailable; **this is now resolved**. Do not revert to guessing from combined commit statuses or V8 shims.
- GitHub Actions run `43608551780` (commit `7bdaf6a53085f86960126e16deb1b217e5b47729`) completed SUCCESS. Actual Node20 evidence suite log `Evidence smoke suite: 37/37 passed`, all 37 test paths distinct, artifact upload successful. URL: https://github.com/osawamas/value-hunter-ai/actions/runs/43608551780

## v229–v232 recap from prior checkpoint
- v229 `scripts/audit-staged-sgx-universe-v229.js`: local, identity-only reference overlap and instrument classification for manually authorized SGX securities CSV without quote fields or public promotion.
- v230 `scripts/stage-sgx-issuer-directory-v230.js`: separate issuer/board/country/date manually transcribed SGX Corporate Information intake, no security code inference.
- v231 `docs/sgx-authorized-data-onboarding-v231.md`: safe process and commands.
- v232 `docs/test_offline_sgx_cli_v232.js`: **real Node child-process** integration test for three CSV commands and strict prevention of public docs output, validated by GitHub Actions.
- The 34-test real Node20 suite previously succeeded in Actions run `43607304518`: https://github.com/osawamas/value-hunter-ai/actions/runs/43607304518

## v233 — first real SHA256 evidence for SGX original financial PDFs
- Earlier v212/213 inspected PDF screenshot images but `source_pdf_sha256:null`; that historical absence has been superseded by a new source-provenance overlay.
- GitHub Actions v210 original-PDF probe run `43603411759` (job `132472814864`, artifact `14117450791`, 2026-11-14T14:10:05.273Z) executed against SGX PDFs and logged `H02:PDF digest, V03:PDF digest`. Downloaded artifact ZIP `sgx-issuer-pdf-v210-source-provenance` and inspected contained `sgx-discovered-issuer-pdf-v210.json`:
  - **H02 Haw Par**, source original `https://links.sgx.com/1.0.0/corporate-announcements/R2V7WFBB9WQMBBP4/876566_FY25%20Haw%20Par%20SGX%20Announcementl.pdf`, final approved SGX FileOpen URL, **706,174 bytes**, SHA256 **`94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5`**.
  - **V03 Venture**, source original `https://links.sgx.com/1.0.0/corporate-announcements/G8XZA2TO5M07X8S0/876221_Venture%20FY2025%20Financial%20Results.pdf`, final approved SGX FileOpen URL, **520,231 bytes**, SHA256 **`b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794`**.
- Independently downloaded an earlier different GitHub Actions artifact from **run `43598869441`**, artifact `14115445847`, observed `2026-11-14T13:15:56.855Z`, and compared full JSON. Both SGX PDFs had **identical SHA256 and byte sizes across two separate network fetches**.
- Created `docs/data/sgx-original-pdf-sha-v233.json` (commits `06bf98be`, `a767d80f`) with both exact hashes, runs, URLs, artifact identifiers, and explicit `external_independent_numeric_audit_completed:false`, `ranking_eligible_count:0`. Original PDF bytes are not committed to repository. Earlier v212/213 JSON remain historical snapshots, not changed/overwritten.
- `docs/test_sgx_pdf_sha_evidence_v233.js` cross-links exact official source URLs and v212/213 announcement IDs, hard pins hash/length, verifies two run IDs and absence of unaudited financial/ranking promotion; PASS.

## v234 user-facing evidence without mislabeling audit
- New `docs/pdf-sha-evidence-v234.js` and panel in `docs/index.html`: shows 2 issuer PDFs, actual byte lengths, shortened SHA with full value in tooltip and dataset, provenance '2 Actions runs consistent', and independent accounting audit not completed. Links to SGX originals and Actions run.
- New `docs/test_sgx_pdf_sha_ui_v234.js` verifies source/size/hash and prohibits change of ranking or numeric auditor evidence; PASS.
- v233/v234 tests added to `scripts/verify-evidence-v198.js` and workflow path triggers. This initially registered `docs/test_sgx_pdf_sha_evidence_v233.js` twice, causing the suite to report 37 test executions though 36 unique. All executions succeeded; test count was inflated until next fix.

## v235 unique test-path count remediation
- Removed duplicate v233 test from the unified suite and added `docs/test_evidence_unique_paths_v235.js`, which asserts all 37 test paths unique and exist. Test self-checks the suite without counting duplicates.
- GitHub Actions run `43608551780`, job `132488321994`, concluded **success**, log `37/37 passed`, JSON artifact upload successful; 37 unique filenames confirmed by reading current suite.
- Intermediate run `43608505621` at commit `450cc434` failed because it referred to v235 test BEFORE the new file was added; later complete commit `7bdaf6a5` passed. Do not misread intermediate failure as current CI failure.

## Remaining material blockers and best next work
1. Now that actual Actions runs/artifacts can be read, inspect other workflows' logs and actual GitHub Pages deployment. Owner settings may still be needed. Do not assert Pages live without a successful publish and working public URL.
2. H02/V03 original SGX PDFs **downloaded and byte-hashed reproducibly**, but this is **not external auditor numeric verification**. Continue independently validating financial figures, period/basis, parent equity and profitability before registering/qualifying as investable.
3. Obtain original official UOB 2026-11-13 `SG261113OTHRHOAF` and OCBC 2026-11-12 `SG261112OTHRXH64` treasury PDF `Anno_12Nov2026.pdf`. The UOB November 13 mirror and issuer IR alert are not equivalent to original.
4. Official exhaustive dated SGX issuer/security master and reuse permission; existing 41-group/82-counter static dual currency subset is not all. Licensed timestamped SGX quotes and matching ex-treasury share counts still absent. StocksSG free API reuse licence unverified/third-party terms require permission.
5. G13/S63 independent financial numerical verification and operating-profit source definition; ranking remains 0 until all conditions met.
6. Existing automatic daily development task is separate; do not claim this chat runs asynchronously.

## Next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv235から再開。main、GitHub Actions **REST runs (mcp__GitHub__fetch で `https://api.github.com/repos/osawamas/value-hunter-ai/actions/runs?per_page=10`)**、`docs/data/latest.json`、`docs/data/sgx-original-pdf-sha-v233.json`、`docs/development-checkpoint-v235.md`を読む。v229手動SGX証券CSVのローカル照合、v230手動公式発行体ディレクトリ別取込、v231手順、v232実Node子プロセスCLI検証を完了。Actions run 43607304518 34テスト成功。v233でHaw Par H02公式PDF SHA256 `94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5`（706,174 bytes）とVenture V03 `b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794`（520,231 bytes）を取得し、2件の別々のGitHub Actions実行run43598869441/run43603411759で完全一致を確認。v234で原本SHA証拠を画面に追加、会計独立監査とは区別。v235で重複テスト登録を削除し自己検証を追加、**run43608551780 GitHub Actions Node20実ジョブ37/37全種類PASS**。財務登録7、第三者候補182、公式限定11証券、ランキング適格0。次は得られたActionsの読み出し経路を活用してPages公開を調査、H02/V03数値の独立検証、UOB11/13・OCBC11/12公式原本、SGX全マスター・株価権利を進める。完了済みを繰り返さず安全な変更のみmainへコミット。
