# VALUE HUNTER AI — v105 checkpoint (2026-11-14 JST)

## Starting point
Read main, recent GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-provider-quality-v103.json`, `docs/data/sgx-master-reconciliation-v105.json`, and this checkpoint. Avoid repeating v97–v105.

## v105 completed
- Added `SGX_PDF_connection_probe/sgx_master_reconcile_v105.py`, `test_sgx_master_reconcile_v105.py`, and `.github/workflows/value-hunter-v105.yml` to main.
- Workflow #43548096491 **success**: https://github.com/osawamas/value-hunter-ai/actions/runs/43548096491.
- The v105 script validates the existing **third-party** 182-candidate sidecar and, only when separately supplied, a dated CSV with strong direct-SGX download provenance. For supplied CSV it checks code, ISIN syntax, trading name, Mainboard/Catalist/Global Listing Board, security type, duplicates, dates and SHA256. It outputs matches and discrepancies without ever claiming total official coverage, altering the verified financial feed, or enabling rankings.
- Actual live run had **NO official master file**, so `docs/data/sgx-master-reconciliation-v105.json` correctly says `official_master_status=NOT_AVAILABLE`, `candidate_count=182`, `official_confirmed_candidate_count=0`, `official_master_completeness_verified=false`, `ranking_eligible=false`. Fake test CSV results are NOT published as verified.
- Important limitation: provenance flags supplied alongside CSV are not independently established merely by passing the validator. A future official collector must validate download origin, authentic source and file schema; even a partial official export is not necessarily full market coverage.
- Financial feed `docs/data/latest.json` stays 7 registered companies and ranking eligible 0, bank prices/shares/valuations not promoted.

## Additional official source discovery
- https://links.sgx.com/1.0.0/corporate-information/1637 is SGX-hosted individual issuer page for Singapore Exchange Limited; shows ISIN `SG1J26887955`, mainboard listing, and information last updated 2026-11-11. This is **individual issuer evidence**, not a complete SGX master. Future v106 could implement conservative individual-issuer verification via SGX-hosted corporate-information pages, requiring exact issuer/code/ISIN reconciliation and dated source provenance. Avoid assuming links.sgx.com corporate-information numeric identifiers have a searchable or complete universe.
- SGX https://www.sgx.com/securities/securities-prices?code=stocks shows a Download control and board/code fields, but neither a stable official bulk CSV URL nor a verified complete download was recovered.
- SGXNet UOB 2026-11-13 `SG261113OTHRHOAF` and OCBC 2026-11-12 `SG261112OTHRXH64` originals still not retrieved. Secondary mirrors only; do not promote current shares.
- v104 quote validation is offline only, not working automated exchange market data ingestion.

## Next engineering tasks
1. Inspect the SGX individual corporate-information page structure and build a fail-closed single-issuer official evidence collector/test, never extrapolate to full universe.
2. Investigate official securities-price download and machine-readable schema (within access/terms constraints), and adapt the reconciliation CSV schema based on actual official files rather than assuming the placeholder headers.
3. Locate UOB Nov-13 and OCBC Nov-12 actual SGX-hosted originals, verify document identity and dates.
4. Implement actual timestamped bank quote acquisition, with secondary crosscheck before calculating market cap, PER/PBR or eligibility.
5. Keep candidate coverage partial, 7 registered, 0 ranking eligible until independently verified.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv105から継続。main、Actions、`docs/data/latest.json`、`docs/data/sgx-universe-candidates.json`、`docs/data/sgx-master-reconciliation-v105.json`、`docs/development-checkpoint-v105.md`を先に読む。v103で第三者API183件中除外1件は指数 `^STI` と特定、候補182社。v104では厳格な日時付き株価の検証ゲート（実株価取得は未実装）、CI #43547815940成功。v105ではSGX公式マスターCSVを入手できた際の銘柄・ISIN・市場区分突合器とテストを実装、CI #43548096491成功。公式CSV未取得につき公式照合0社、公開JSONに未入手と記録。SGX個別発行体ページ https://links.sgx.com/1.0.0/corporate-information/1637 を発見、次は個別SGX原本と実CSVの取得方法、銀行通知原本、実株価の日時付き自動取得を進める。財務登録7社・ランキング適格0社、未検証値は時価総額・PER/PBRに使用しない。テストしてGitHubへ保存。
