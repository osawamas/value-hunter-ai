# VALUE HUNTER AI — v228 development checkpoint (2026-11-14 JST)

## Current source of truth
- Resume from latest main and this file, rather than redo v189–v228.
- Main before this checkpoint: `b5685d223e4263e3207c3e02375890bd5229c470`.
- Latest observed `docs/data/latest.json`: `2026-11-14T14:34:12.489057+00:00`; 7 financially registered companies, 182 third-party candidate codes, formal ranking eligible 0, ranking disabled.
- 11 named official SGX board-lot reduction securities from `docs/data/sgx-official-batch-seed-v196.json` remain a SEPARATE limited scope; do not add the 82 currency-specific counters to that as 82 separate issuers.
- Unified `scripts/verify-evidence-v198.js` now lists **31** regression scripts through v228; GitHub Actions workflow `.github/workflows/bank-corporate-actions-v191.yml` has corresponding changes. Each new v223–v228 relevant regression was executed using a V8 Node-compatible harness against fetched GitHub source. Native full 31-test Node suite and actual push-triggered GitHub Actions job status have NOT been observed or independently verified; GitHub connector supports file reads/writes but not push-run listing and the public Actions pages returned cache misses.
- Local `git ls-remote` failed DNS for github.com, so no local checkout for native Node full-suite run.

## v223 financial-scope correctness fix (important)
- Found that `docs/primary-issuer-reconciliation-v214.js` incorrectly displayed H02 Haw Par FY2025 **group total equity 4,291,076 SGD thousands** in the column labelled parent-attributable equity, despite no separately verified parent vs noncontrolling allocation.
- Fixed H02 `parent_equity:null` and display `未分離`, retaining verified group total equity and balance arithmetic. V03 Venture parent equity and noncontrolling equity remain source-verified separately.
- New assertions `docs/test_primary_issuer_reconciliation_v214.js` require H02 parent equity=null, V03 parent equity 2,792,741, both proper total equity labels. Test PASS via V8 harness.
- Commits `ca230fea6a30deae8592a6f49418b34c783ec00f`, `a1ae8a0576bdd2eb2a516dc0e57c01e2aa19dbfa`.

## v224–v225 first expansion: static official SGX dual-currency trading-counter pairs
- Official static reference `https://www.sgx.com/securities/trading`, section `Securities with Dual Currency Trading`, has many traded security pairs. It is NOT the dated full official SGX listed-issuer/security master, and public market-data reuse/quote-redistribution rights remain unconfirmed.
- Added `docs/data/sgx-dual-currency-research-v224.json` with 18 new observed product pairs (36 counters) to augment earlier v220 three pairs (6 counters), totaling 21 pairs / 42 distinct codes. Includes business trust, potential equity, ETFs, stapled security, REIT.
- Added negative regression `docs/test_dual_currency_expansion_v224.js`; verified 21 groups, 42 unique counters and only AWX/BS6/CFA overlap in third-party 182. No evidence that 39 missing counters represent 39 missing corporations.
- Updated `docs/official-multicurrency-v221.js` to support backwards-compatible `validate` (3 groups), `validateExpanded` (21 groups), and dynamic table. Adjusted `docs/index.html`, added `docs/test_expanded_currency_ui_v225.js`.
- One V8 test failed because changed currency was accepted; tightened comparator to exact official code/currency/category for 18 new pairs; rerun PASS.
- Relevant main commits `5749639a`, `6cc9c57a`, `bc1e369d`, `13907a54`, `f7e1a46f`, `d024341d`.

## v226 SGX instrument taxonomy
- In `scripts/classify-sgx-counters-v202.js`, newly recognize `STAPLED SECURITY` and `STAPLED SECURITIES` as `STAPLED_SECURITY`, and `L&I PRODUCT` as `LEVERAGED_PRODUCT` rather than automatically labeling them unknown/equity. This preserves regulatory category differences.
- Added `docs/test_sgx_instrument_types_v226.js`, tested with synthetic paired FX counters and new product types. V8 standalone test PASS, existing v202 classifier regression also PASS.
- Relevant commits `15265efb`, `297fe862`.

## v227–v228 second expansion to 41 official product groups / 82 currency-specific trade counters
- Added `docs/data/sgx-dual-currency-extra-v227.json`, 20 further official static product pairs (40 currency-specific counters). Did NOT include an ambiguous UPD/UPU row due to inconsistent instrument label on the source page. The file explicitly notes excluded row, no full master or market-data license claims.
- Combined v220 (3), v224 (18), v227 (20): **41 distinct instrument pairs / 82 trade counters**. Third-party incomplete 182-candidate source contains only **AWX, BS6, CFA and MXNU**. Therefore 78 counters from selected static pairs are absent; NOT 78 missing independently verified issuers.
- New `docs/test_sgx_dual_currency_second_batch_v227.js` tests expected code/currency/category, deduplication, no full-master assertion, no quote rights/ranking. Standalone V8 test PASS.
- `docs/official-multicurrency-v221.js` now exports `validateAll` (41 groups) and loads third dataset into the existing UI (no duplicate section). Existing `validate` and `validateExpanded` retained for prior tests. UI labelled 41 groups /82 counters; category counts 3 potential equity, 34 ETF, 2 REIT, 1 business trust, 1 stapled security.
- New `docs/test_dual_currency_ui_v228.js` tested 41 groups, 82 unique counters, category counts, four overlap codes and negative tampering. PASS via V8 harness; existing v221/v225 tests preserved by backwards compatibility.
- Relevant commits `f6145034`, `3e91674d`, `b22ea871`, `78ad8158`, `65e94970`, `06c9aa99`, `b5685d22`.
- The static official subset must not be conflated with the comprehensive historical SGX securities master, a guaranteed current-listed universe, an authenticated issuer identity, or legally authorized stock quotations. No investment ranking promotion occurred.

## Next tasks (v229+)
1. Inspect ACTUAL GitHub Actions push-run logs and machine-readable `sgx-source-integrity-v218-results` artifact, verify native Node 31-test result, fix any failures. Separate V8 compatible smoke tests are not Actions passes.
2. Obtain dated official full SGX listed securities/issuers master and reuse rights; v220/v224/v227 are merely a partial static dual-currency reference, with 41 groups observed and one ambiguous row deliberately omitted. Use already built v199 original CSV raw-byte staging, v202 classifier and v204 ISIN checks.
3. Secure original UOB Nov13 and OCBC Nov12 SGX buyback/treasury attachments; same-date issued ex-treasury shares, original bytes/hashes. H02/V03 official SGX financial reports visually inspected previously but SHA256 raw PDF extraction remains pending.
4. Independent numeric audit of G13/S63 reported financial source/parent equity/operating definitions; get lawful timestamped SGX quote redistribution rights and current shares before unlocking market cap/PER/PBR or stock ranking.
5. Confirm Pages actual deployment only when owner has enabled it; recent web status unknown.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv228から継続。最新main、Actions、`docs/data/latest.json`、`docs/data/sgx-official-multicurrency-subset-v220.json`、`docs/data/sgx-dual-currency-research-v224.json`、`docs/data/sgx-dual-currency-extra-v227.json`、`docs/development-checkpoint-v228.md`を読む。v223ではH02のグループ総純資産を親会社株主持分と誤表示していた問題を修正し親会社欄を未分離へ。v224–225でSGX公式複数通貨カウンターを21組42コードへ拡張し、画面・厳密な通貨検証を追加。v226でステープル証券とL&I商品を普通株から分離。v227–228で公式ページの限定調査を41商品82取引コードまで拡張、182第三者候補との一致はAWX/BS6/CFA/MXNUの4件のみで78コード不足（78社不足とは違う）。同じ比較画面へ統合し従来の検証関数も維持。統合回帰31テスト登録、追加分のV8互換個別テストPASS、実Node/GitHub Actions完走未確認。財務登録7、候補182、公式売買単位11証券（別の集合）、ランキング0。UOB11/13・OCBC11/12原本、公式全銘柄マスターと利用権限、時刻付き正規株価、独立財務照合、Pages公開は未完。完了済み作業を繰り返さずGitHub mainへ修正とチェックポイントを保存。
