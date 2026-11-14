# VALUE HUNTER AI — v196 checkpoint (2026-11-14 JST)

## Continuation from v194, including previously skipped work
- Read latest main, v193 and v194 checkpoints, `docs/data/latest.json`, audited bank-only FY2025 internal fields, bank 3Q2026 original/IR interim fields, normalized big-three bundle, and latest G13/S63 source sidecars.
- The latest observed financial feed is `2026-11-14T11:45:17.566989+00:00` with seven financial records and zero eligible. Sidecars v137/v140/v161 linked to this timestamp at observation.
- **Key skipped/misunderstood work**: DBS, OCBC and UOB FY2025 annual issuer banking data and 3Q2026 banking data were ALREADY parsed within bank-specific namespaces of the feed, despite generic industrial revenues/asset fields being null and generic `REGISTERED_SOURCE_NOT_PARSED` labels. Do not overwrite generic bank fields with industrial-style metrics or call the bank-specialized evidence absent.

## v195 bank-only financial comparison now on main
- `docs/bank-fy-interim-bridge-v195.js`, initially `32bd62af5f816b25dee0ba7c77a78483ca7b535a`, fixed `2dc9234c5c7126d4bb357d8f0b1ce942540e2dec`.
- FY2025 audited issuer Group financial values (million SGD):
  - D05 total income 22,900; profit attributable parent 10,933.
  - O39 total income 14,614; parent profit 7,422.
  - U11 total income 13,808; parent profit 4,682.
- 3Q2026 standalone quarter group net profit, million SGD: D05 2,813, O39 2,042, U11 1,250.
- Important bug caught via **actual direct execution** of fetched validator: UOB's issuer investor-relations interim PDF SHA `47d3c789...` is different from SGX-hosted CFO slides SHA `d3b474aa...`. Initially v195 falsely required identical hashes. Corrected to verify BOTH individual 64-character source SHA/dates and matching net profit + NII amounts without assuming file identity. These are two issuer-origin PDFs, NOT independent third-party audit.
- Added HTML table via `d513075647b856c2a64add9bc1ed273c4b028ecb`, new test `docs/test_bank_fy_interim_bridge_v195.js` commit `04ebc177beef9e6193a541f0bab1d667153d33ee`, strengthened test for differing UOB PDF source digests `16cba9e8361ba5c1c2169ab7c2ff6eddc3e099f5`, and included in existing CI workflow `761303276d383af0ce7edb01823fd2f5e8bf3ea5`.
- Direct validator executed with fetched live JSON: 3/3 banks matched; 6 adversarial mutations were rejected. Four actual test-file bodies v190/v192/v193/v195 were executed using an in-process V8 compatibility shim for Node's fs/assert, ALL 4 PASS. **This is NOT an observed GitHub Actions CI run or a complete Node environment.** Actual Actions push jobs still unconfirmed.

## v196 first official SGX security code subset
- Official SGX `https://www.sgx.com/securities/trading` currently documents a first 2026-10-05 batch of **11** securities with board lot reduced to 10 shares. Captured code/company/trading currency and date as `docs/data/sgx-official-batch-seed-v196.json` commit `fcf0fa29f20b5c69b0aff5842e7dc5fcd5e49561`.
- Names/codes: D05 DBS SGD; G07 Great Eastern SGD; H02 Haw Par SGD; C07 Jardine Cycle & Carriage SGD; J36 Jardine Matheson USD; BN4 Keppel SGD; O39 OCBC SGD; K6S Prudential USD; S68 SGX SGD; U11 UOB SGD; V03 Venture SGD.
- Explicitly **NOT** the full official issuer/security list, no prices, no quote permission, no valuation eligible, no current outstanding shares. Source page describes 11-security lot-size batch only.
- `docs/official-batch-v196.js` (commit `9f051b5367d59525c36edffbb488fceb1d4409a6`) displays the 11-seed alongside whether each is already one of 7 financial records; four match D05/O39/S68/U11, seven are not finance-registered. `docs/index.html` edited `e9ba3052eabfcd06eb3ffc4000526011c32801f0` to add separate panel after third-party candidates.
- `docs/test_official_batch_v196.js` commit `e193858b81d8412ffaf84c970c0b0a1d764112d5`; dedicated Actions workflow `.github/workflows/sgx-official-seed-v196.yml` commit `de8cfcb0d2cfd88c37dabd5d49ab350c292f42dd`. Direct test body executed in V8 Node assert/fs compatibility shim and PASS including negative cases. Again **Actions workflow actual outcome not observed**.
- No changes to `docs/data/latest.json` or investment rankings.

## Still unresolved; don't make false claims
- UOB 2026-11-13 and OCBC 2026-11-12 current SGX original buyback/treasury notices were not fetched; third-party data cannot be promoted.
- No licensed timestamped SGX quote source or redistribution permissions. SGX official delayed viewer is not license to scrape and republish.
- SGX official whole-market dated issuer/securities master NOT obtained. A first batch of 11 officially sourced securities is not the entire SGX universe. Third-party 182 candidate securities are NOT official exhaustive coverage.
- G13/S63 independent numeric financial verification not complete. Main ranking eligible zero.
- Pages publisher status disabled/unconfirmed from prior v189; actual Github Actions CI run status still unverified. Connector lacks push workflow listing, and public Actions API/web access had cache errors.

## Next priority (v197+)
1. Verify actual GitHub Actions jobs through a workflow run listing (the connected commit-workflow API only supports PR-triggered results). Check v195/v196 latest jobs and fix actual logs.
2. Pursue SGX official full dated securities master and permissions, clearly distinguishing company issuers vs traded counters and duplicate currencies.
3. Acquire UOB Nov13 and OCBC Nov12 SGX original attachments and preserve cryptographic source digests.
4. Independent financial audit for G13/S63; maintain separate bank-specific annual & interim analysis, never use bank 3Q as FY profitability denominator.
5. Obtain licensed same-date SGX price and issued-ex-treasury share count before valuations/ranking.
6. User's existing daily automatic VALUE HUNTER AI continuation task can handle scheduled future sessions; do not claim this synchronous chat continues indefinitely after this turn.

## Next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv196から再開。main・Actions・`docs/data/latest.json`・`docs/data/sgx-big3-bank-research-v186.json`・`docs/data/sgx-bank-corporate-actions-v190.json`・`docs/data/sgx-official-batch-seed-v196.json`・`docs/development-checkpoint-v196.md`を読む。v195で銀行3社の既存FY2025専用財務データ（総収益/親会社帰属利益）と3Q2026利益を期間を混ぜず日本語画面に追加。UOB IR PDFとSGX PDFは異なるハッシュの正規資料なので数値と期間で照合する修正済み。v190/v192/v193/v195の4テストをV8互換実行環境で動かして4/4 PASS（Actions本体は未確認）。v196でSGX公式2026/10/5売買単位10株変更11銘柄のみを公式ソース付きで台帳・UI・テスト・CIとして追加（4社既存財務登録、7社未登録）。これはSGX全銘柄マスターではない。登録財務7社、第三者候補182社、ランキング適格0社。UOB11/13・OCBC11/12原本、SGX価格ライセンス、公式全銘柄マスター、独立財務検証、Pages公開は未完。コードをmainに保存済。新CI成功と公開稼働は未確認。
