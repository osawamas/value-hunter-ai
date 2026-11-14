# VALUE HUNTER AI — v219 checkpoint (2026-11-14 JST)

## Resume
- Continue after `docs/development-checkpoint-v216.md`; read main, GitHub Actions job run records (not just combined statuses), `docs/data/latest.json`, `scripts/probe-issuer-financial-pdf-v210.js`, `scripts/verify-evidence-v198.js`, and this checkpoint.
- Latest observed financial feed 2026-11-14T13:19:38.274864+00:00, 7 registered financial issuers, third-party 182 candidates, official partial batch 11 securities, ranking eligible 0 and disabled.
- Main head prior to this checkpoint: `72018c1641e979f8d81d3c6572027a5327db0e25`.
- Existing daily VALUE HUNTER AI automation is enabled, next 2026-11-15 14:00 JST. The separate four-run hourly short automation is **disabled**, despite having been created earlier; its last run reported `requires_user_action=true`. Do not claim unattended hourly work is active.

## v217: correct official issuer PDF redirect validation
- `scripts/probe-issuer-financial-pdf-v210.js` updated commit `9d4380238058a67eb6fef36da642bb465616fc61`. Previously used `redirect:"follow"`, allowing an HTTP client to request a disallowed host before its final URL was validated. Now uses `redirect:"manual"` with validation BEFORE each next request, exact SGX/Haw Par host allowlist, max 3 redirects, cycle rejection, strict Content-Length, bounded stream size, 30s timeout and PDF header test.
- `docs/test_issuer_pdf_probe_v210.js` updated commit `a79e6d28e842528e35583211f0200f44b5ead3e8` to check external redirect request is NEVER attempted, same-host redirect success, nonnumeric Content-Length rejection, oversized response, invalid MIME/PDF body, etc.
- v217 test body executed in in-process V8 compatibility harness using modeled URL/Buffer/crypto and async fetcher; **PASS**, but this is NOT real Node CI execution or actual remote PDF bytes.

## v218: per-test CI machine-readable report
- `scripts/verify-evidence-v198.js` added `build/research/evidence-integrity-v218.json` machine-readable per-test status, commit SHA if provided by GitHub, Node version and explicit false audit/market license/public deployment flags; report generation runs even when individual tests fail. Commits `e346367155bd9cdf5e58fba3ead34005e135ac86`, correction of newline formatting `de120e78317283c98340b829909e08a526e16bbf`. JSON is valid newline-terminated; markdown summary to `GITHUB_STEP_SUMMARY`.
- `.github/workflows/bank-corporate-actions-v191.yml` updated `3867778e13c592051200bf7a91e7caea082ff97f` to upload `sgx-source-integrity-v218-results` via `actions/upload-artifact@v4` even if tests fail, retention 14 days.
- Simulated 22-test process with 1 failed test: validated parseable JSON, correct failed test count, exit code 1 and markdown table. This does not establish GitHub Actions actual run success.

## v219: regression test reporting path
- Added `docs/test_evidence_suite_report_v219.js` commit `c2664fbb4c1fc60d6d867499975ac0aba8f95e5d`, using a vm sandbox / fake spawnSync to check all-pass and one-failure report generation, count, flags, JSON and GitHub job summary.
- Added v219 to unified suite commit `d11f68199bf083e79af331bba4d11bd9496253c7`; workflow trigger commit `72018c1641e979f8d81d3c6572027a5327db0e25`.
- v219 regression was executed with GitHub-fetched source through V8 Node vm/fs/path compatible shim: **PASS**, both all-pass and one-failure outcomes. Shared suite currently lists **23 tests**, but their **full real Node run/GitHub Actions job statuses remain UNCONFIRMED**.

## Further source search / blockers
- Searched SGX official ID for UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64`; public searches only gave syndicated ShareInvestor and member-only original filing viewers, not exact SGX original source path or OCBC PDF bytes. **No new official shares were promoted.** OCBC `Anno_12Nov2026.pdf` attachment remains unavailable.
- Tried direct original H02 PDF downloading with container downloader; failed. H02/V03 original PDF SHA digests remain unknown. Previously visually inspected PDFs and identified exact URLs v212/213, but byte-level proof requires source-probe artifact or successful direct download. Never fill in hypothetical SHA.
- Attempted public GitHub Actions run REST/UI via web; both unavailable/cache miss. GitHub connector only exposes PR-associated workflow runs (no push list), cannot confirm CI success. The new v218 artifact will be useful once a real run ID/UI is accessible.
- Official full SGX master, lawful timestamped quote redistribution rights, independently audited G13/S63 and latest shares still unresolved. Historical reference quotes or publisher matches MUST NOT trigger a ranking.

## Next v220+
1. Obtain actual Actions result for `sgx-source-integrity-v218-results`, and inspect per-test outcome; if needed correct failures. Check dedicated PDF probe v210 artifact and SHA before marking raw PDF obtained.
2. Obtain primary UOB 13-Nov and OCBC 12-Nov corporate action originals, enforce effective date and ex-treasury count. No secondary-only promotion.
3. Prioritize data coverage over adding duplicate guard layers: SGX official full security master and licensed quotes, independent issuer numerical verification / actual stock eligibility, with reviewed reporting basis.
4. Keep `docs/data/latest.json` and generated sidecars under existing automated pipeline, don't rewrite an ephemeral data snapshot manually or claim ranking eligible.
5. Note short hourly automation is now disabled; daily one remains enabled.

## Next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv219から続けて。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v219.md`を読む。v217でH02/V03正規SGX PDFダウンロード器の転送先検証を事前化（redirect=manual、許可ホストのみ、上限3回・サイズ上限、未知の転送は送信前拒否）。v218で22テスト結果をJSONとGitHub Actionsサマリーへ出す仕組み・失敗時も保存するartifactを実装。v219で成功/失敗両方のJSON出力回帰テストを追加、現在23テスト登録。v217/v219個別実行はV8 Node互換環境PASS、実GitHub Actionsジョブ結果とH02/V03原本PDF SHAは未確認。UOB11/13・OCBC11/12原本未取得、正規SGX全銘柄マスター・株価利用権限・独立財務検証・GitHub Pages公開は未完。財務登録7、第三者候補182、公式限定11、ランキング0。毎日14時の自動タスクは有効、別の短期Hourlyタスクは無効（requires_user_action）。既済作業をやり直さず次へ進める。
