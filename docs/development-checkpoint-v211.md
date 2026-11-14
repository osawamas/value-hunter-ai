# VALUE HUNTER AI — v211 checkpoint (2026-11-14 JST)

## Current state / must read on resume
- Read latest `main`, Actions actual jobs, `docs/data/latest.json`, and `docs/development-checkpoint-v211.md` first. Main head before writing this checkpoint: `796e1a5858c2449be5f1890c6aac02237c4bf6a8`.
- Latest observed feed `2026-11-14T12:53:28.295404+00:00`, financial records 7, ranking eligible 0, disabled. Third-party candidate list 182. Official SGX 2026-10-05 lot-size batch 11 securities only, NOT full official SGX security master.
- Avoid resetting or overwriting concurrent v29 and ranking sidecar refresh commits.
- Read prior `docs/development-checkpoint-v203.md` and v201 for history; DO NOT redo completed work.

## v204 ISIN/type identity
- `scripts/sgx-isin-linkage-v204.js`, `docs/test_sgx_isin_linkage_v204.js`: validates international ISIN checksum but never equates checksum validity with official issuer/entity proof or SGX listing status. Same ISIN may appear with multiple currency counters; no implicit financial ranking. V8 isolated test PASS. Included in unified suite and Actions path triggers.

## v205 three coverage sets, concrete omission found
- `docs/universe-coverage-audit-v205.js`, `docs/test_universe_coverage_audit_v205.js`, `docs/index.html`: compared registered 7 financial records, third-party 182 company candidates, and official limited lot-size 11 securities.
- **10/11** official symbols overlap third-party 182. **K6S** Prudential is missing from third-party candidate list; this is a concrete incompleteness example. Official subset 11 includes 4 existing financial records (D05/O39/S68/U11); 7 have no financial feed record.
- Fail-closed UI if data origin changed, counts or rankings falsely promoted. V8 test PASS, reverified after the 12:53 UTC feed refresh.

## v206–v207 official original issuer historical research for seven other official seed securities
- v206:
  - `docs/data/sgx-additional-issuer-fy2025-v206.json`
  - `docs/additional-issuer-research-v206.js`
  - `docs/test_additional_issuer_fy2025_v206.js`, HTML panel.
  - BN4 Keppel FY2025 continuing-operation revenue SGD 5,983m; reported profit including discontinued SGD 789m; **adjusted 'New Keppel' profit SGD 1,100m is distinct and NOT a reported net profit substitute**.
  - V03 Venture FY2025 revenue SGD 2,534.5m; reported attributable profit SGD 227m.
  - Source official issuer Keppel press/annual and Venture investor highlights/SGX release. PDF bytes/SHA independent confirmation NOT completed, ranking false.
- v207:
  - `docs/data/sgx-remaining-issuer-research-v207.json`
  - `docs/remaining-issuer-research-v207.js`
  - `docs/test_remaining_issuer_research_v207.js`, HTML panel.
  - G07 Great Eastern FY2025 attributable profit SGD 1,207.1m;
  - H02 Haw Par FY2025 revenue SGD 229.967m;
  - C07 Jardine Cycle & Carriage underlying FY2025 profit USD 1,110m (trading currency SGD, report USD);
  - J36 Jardine Matheson reported FY2025 net profit USD 1,109m, underlying profit USD 1,681m (DISTINCT);
  - K6S Prudential FY2025 IFRS after-tax profit USD 4,119m, adjusted operating profit before tax USD 3,306m (DISTINCT).
  - Different accounting regimes and currencies deliberately not combined in a single ranking. Source pages include Great Eastern official media, Haw Par issuer full-year PDF, Jardine 2025 annual website, Prudential 2026 half-year page with FY2025 comparator.
  - v207 test initially detected missing guard against duplicate research symbol, fixed in commit `11802dc6`; re-executed and PASS.
- Together research leads exist for **all seven limited-official-batch symbols not already financially registered**. These are a separate research sidecar, NOT addition of 7 certified feed issuers.

## v208–v209 official issuer group accounting deeper
- `docs/data/sgx-h02-group-statement-v208.json`, `docs/test_h02_group_statement_v208.js`:
  - H02 official full-year 2025 and 2024 income/balance statements, SGD thousands.
  - 2025 revenue 229,967, profit after tax 265,462, total assets 4,417,906, liabilities 126,830, net assets/equity 4,291,076.
  - 2024 assets 4,277,008, liabilities 128,474, equity 4,148,534.
  - Both balance identities verified internally, no verified parent-attributable profit line, no downloaded PDF SHA. Test PASS.
- `docs/data/sgx-v03-balance-v209.json`, `docs/test_v03_balance_v209.js`:
  - V03 official IR financial highlight rounded SGD millions FY2025: total assets 3,602.2, liabilities 804.4, parent equity 2,792.7. Derived group net assets 2,797.8, unexplained difference 5.1m, NOT authenticated NCI.
  - FY2024 assets 3,699.9, liabilities 805.6, parent equity 2,889.8. Derived net assets 2,894.3, unexplained difference 4.5m.
  - Both FY balance arithmetic tests PASS but no independent line-by-line audited original proof.
- v205/v206/v207/v208/v209 test bodies were rerun together with latest fetched `latest.json` timestamp 12:53 UTC, **5/5 PASS in V8 Node assertion/file compatibility harness**, not GitHub Actions.

## v210 original issuer PDF source provenance probe
- `scripts/probe-issuer-financial-pdf-v210.js`, `docs/test_issuer_pdf_probe_v210.js`, `.github/workflows/issuer-pdf-source-probe-v210.yml`.
- Built bounded HTTPS issuer PDF retrieval for H02 and V03 original, URL allowlist, redirect validation, PDF header and SHA256 of raw bytes. Emits an artifact with either hash/size or explicit failure; **does not publish original PDF bytes or source-derived financial numbers**.
- Probe original PDF fetch has NOT been observed running successfully. V8 synthetic Buffer/URL/crypto tests for source module passed 3 rejection cases and successful sample download, but actual Node GitHub Actions and real original PDF bytes still unverified.
- Dedicated GitHub Action uses `continue-on-error` for source fetch, preserves JSON report even if fetch blocked. Do not interpret workflow overall success as original PDF proof. The shared evidence suite also runs its offline test.

## v211 independent publisher parent equity historic crosscheck (NOT independently audited)
- `docs/data/sgx-parent-equity-research-v211.json`, `docs/test_parent_equity_research_v211.js`.
- G13 Yahoo Finance FY2025 common equity SGD 8,205,416 thousand matches official issuer parent equity exactly; Yahoo balance assets 9,185,799 thousand and liabilities 980,383 thousand also match.
- S63 StockAnalysis FY2025 common equity SGD 2,574m rounds from official issuer SGD 2,573.638m; total equity 2,921m rounds from 2,921.245m; assets 16,032m from 16,032.106m. The common equity is distinct from minority-inclusive total equity.
- Numerical historical external aggregator correspondence is NOT an external independent auditor opinion nor independent original financial re-calculation. Strict issuer readiness gate remains blocked.
- v211 test executed in V8 compatibility harness PASS, with seven adversarial mutations rejected. Added to unified integrity suite and workflow trigger.

## Evidence tests & publication status
- Shared `scripts/verify-evidence-v198.js` now lists **18** test files through v211. New v204–211 individual/V8 smoke tests PASS as noted; **the complete 18-test Node suite and GitHub Actions push-triggered job success were not independently verified**. Public Actions web/API could not be inspected; connector exposes PR-associated run lookup, not push run listing.
- GitHub Pages `https://osawamas.github.io/value-hunter-ai/` still not accessible via the web tool; publish success unverified. Last known Pages publish SKIPPED because repository owner had not enabled Pages (Settings→Pages→GitHub Actions).
- Investment ranking eligible count **0**. No licensed timed SGX trade quote, no authorized redistribution rights, no latest complete same-date ex-treasury issuer share count. No true complete SGX dated securities/issuer master.
- UOB Nov13 primary detailed SGX buyback filing and OCBC Nov12 treasury PDF still not retrieved; secondary mirrors quarantined. Never promote their count to official.
- Existing daily scheduled VALUE HUNTER AI automation is enabled, scheduled next for 2026-11-15 14:00 JST (last checked). Earlier run_now returned `inline_run` (worked in current conversation, not an independent background cloud run). No changes to automation schedule.

## Next priority v212+
1. Check actual GitHub Actions run jobs for 18-test suite and v210 source-probe artifact. Obtain H02/V03 PDF SHA digests before elevating any original source evidence.
2. Advance G13/S63 parent equity beyond an unaudited independent-web-provider summary into independent raw-audited numeric re-calculation and verified accounting basis, without conflating operating-income definitions or adjusted net profits.
3. Obtain UOB 2026-11-13 and OCBC 2026-11-12 original corporate-action filings, reconcile date-accurate issued minus treasury shares.
4. Acquire full authorized SGX issuer/security master, its date and reuse permission; current v196 batch of 11 is limited. Use v199/200 bytes staging, v202 classification, v204 ISIN and v205 coverage auditing.
5. Obtain licensed timestamped exchange quotes with legitimate public redistribution rights and matching shares; only then activate valuations/rankings.
6. Confirm actual GitHub Pages deployment and link response after owner's settings.

## Copyable next conversation
VALUE HUNTER AI `osawamas/value-hunter-ai` のv211から続行。まず最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v211.md`を読む。v204 ISINチェック、v205公式11銘柄と第三者182候補の照合（K6Sが候補台帳に欠落）、v206 BN4/V03年度財務調査、v207 G07/H02/C07/J36/K6S年度指標の原通貨・会計定義別調査を追加。これで公式限定11銘柄のうち既存財務登録4、未登録7に調査ソースがあるが正式財務登録は7社のまま。v208 H02 FY2025/24資産・負債・純資産を算術照合、v209 V03グループ純資産と親会社株主持分の差を混同せず照合。v210はH02/V03原本PDFのバイトSHA取得プローブとGitHub Actions証拠artifact（実ジョブ未確認）。v211はG13/S63のFY2025親会社株主持分をYahoo/StockAnalysis掲載値と数値照合、独立監査完了には昇格禁止。18テストを一括実行するスクリプト更新済み、最近追加分のV8互換テストPASS、全18件の実Node/CI成功は未確認。ランキング0、登録7社、第三者182候補、公式限定11証券。UOB/OCBC原本、SGX公式全銘柄マスター、許諾付き時刻株価、独立財務検証、Pages公開が残る。完了工程を繰り返さずGitHubへ保存し開発を継続。
