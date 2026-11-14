# VALUE HUNTER AI — v238 checkpoint (2026-11-14 JST)

## Latest verified main and workflow
- Continue from **v238**, not from v189 or v235. Inspect current main, Github Actions run REST endpoints and this checkpoint before changing anything.
- Last observed main `8207c0424fc4aa9ad396ca5efa450f21a1ce9018` (other workflows may update main concurrently).
- Last observed `docs/data/latest.json` feed `2026-11-14T15:05:20.502940+00:00`: **7** registered financial symbols, candidate universe **182**, ranking eligible **0**, ranking disabled.
- Unified evidence suite contains **40 distinct** test paths. Real Node20 GitHub Actions run `43609852535`, job `132492270399`, commit `45bb998e91fdc56d8e303feba58e0aa53f292eab`, concluded **SUCCESS**, log literally `PASS docs/test_sgx_two_document_crosscheck_v238.js` and `Evidence smoke suite: 40/40 passed`.
- GitHub Actions push-run listing is accessible using connected `mcp__GitHub__fetch` with URL `https://api.github.com/repos/osawamas/value-hunter-ai/actions/runs?per_page=10` and `/actions/runs/{id}/jobs`. Use `mcp__GitHub__fetch_workflow_job_logs` with job id to check exact test outcome. Earlier claims that runs cannot be observed were superseded by v233–238 work.
- GitHub Pages deployment still **NOT ENABLED** in owner settings; v46 publishing workflow `.github/workflows/value-hunter-pages.yml` has job `pages-setup` successful but deployment job `pages` skipped, e.g. run `43608393865`. Owner must enable Settings → Pages → Build and deployment → GitHub Actions. Do not claim site live because validation passed.

## Recap v233–v237 original-file evidence
- Successfully obtained GitHub Actions artifacts from official SGX PDF downloads. Exact original FY2025 results PDF digests:
  - H02 results release: `94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5`, 706,174 bytes.
  - V03 results release: `b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794`, 520,231 bytes.
- 2 separate Actions runs (`43598869441`, `43603411759`) confirmed identical hashes and byte lengths for both financial release PDFs. Stored in `docs/data/sgx-original-pdf-sha-v233.json`.
- v236 dedicated annual original PDF probe GitHub Actions `43609080946`, job `132489927571`, successfully downloaded and hashed both separate issuer FY2025 annual reports:
  - H02 annual report: `75328b273799863390e35a626e8e3679fe79ab853ef0a00f2775dd159364cfb8`, 4,754,838 bytes.
  - V03 annual report: `eaebb6f4192ceb478c819b991eb18a3c34e43bf573388b9098b5e48b73b26a97`, 8,502,570 bytes.
- Annual hashes and original URLs stored `docs/data/sgx-annual-report-sha-v237.json`. Two files from one company are NOT independent financial sources. Original PDF bytes themselves were not committed, only SHA evidence and source links.
- Real Node20 CI through v237 succeeded, log `38/38 passed` at run `43609131743` and `39/39 passed` after v237 integration.

## v238 — same-issuer FY2025/2024 source comparison and arithmetic
- Added `docs/data/sgx-two-document-crosscheck-v238.json`, commit `fcb6e29f90aa103ca907aadfb9216875e2d62a6d`. Contains H02/V03 issuer annual report vs issuer FY2025 results research sidecar for FY2025 and FY2024:
  - H02 revenue 229,967 / 244,824 SGD thousands (2025 / 2024), group profit after tax 265,462 / 228,274, assets 4,417,906 / 4,277,008, liabilities 126,830 /128,474, total equity 4,291,076 / 4,148,534. Parent equity and NCI are NOT separately verified for H02.
  - V03 revenue 2,534,517 / 2,735,927, group profit 227,635 / 245,750, parent profit 226,958 / 245,029, noncontrolling profit 677 /721, assets 3,602,219 / 3,699,946, total equity 2,797,833 / 2,894,324, including parent equity 2,792,741 / 2,889,813, NCI equity 5,092 / 4,511.
  - Same issuer two-document figure comparison, not independent third-party numeric verification; original hashes attest byte identity but not accounting accuracy, and prices/current shares/licensed redisplay absent.
- Added `docs/test_sgx_two_document_crosscheck_v238.js` commit `fca75997`, fixed exact H02 selection `b318dd71`, includes source record existence, exact equality against prior H02 v208 and V03 v213 transcriptions, balance-sheet equations, parent/noncontrolling reconciliations, negative tampering tests and mandatory ranking false. **Note**: exact numeric equality of two repo datasets tests internal consistency; it does not by itself prove an independent re-extraction from annual report. Preserve caveat for further annual-page audit.
- Added test to `scripts/verify-evidence-v198.js` commit `11a17ddd`, workflow trigger `.github/workflows/bank-corporate-actions-v191.yml` commit `45bb998e`, true Node20 CI `43609852535` 40/40 PASS.
- New public search reconfirmed UOB Nov13 SG261113OTHRHOAF 34,000 repurchased, cumulative 6,878,600, reported ex-treasury 1,646,677,591 from **ShareInvestor syndicated secondary** only, `https://b.siasset.com/news/news.html?nid=515671689&source=regional_sgxnet`. OCBC Nov12 SG261112OTHRXH64 `Anno_12Nov2026.pdf` found only as secondary announcement without official original attachment. **Neither promoted as official**. SGX public search `https://www.sgx.com/stock-exchange/company-announcements` is a potential official discovery entry but official archive API may be restricted (Akamai). Avoid scraping circumvention and avoid inventing links.

## Next material work v239+
1. Strengthen actual annual PDF numeric attribution: visually compare original annual report financial statement page(s) with v238 numbers and mark page-specific evidence separately from consistency-with-previous-JSON, preferably by original PDF page/text inspection. Avoid claiming independent audit from two same-issuer docs.
2. Pursue SGXNet original primary UOB Nov13 and OCBC Nov12 documents; dated share counts and treasury changes only if original verified, with source and as-of time.
3. Official complete dated SGX issuer and traded security master and legal redistribution rights; v229 manual security CSV and v230 separate issuer CSV are offline safe staging, not actual complete source; see `docs/sgx-authorized-data-onboarding-v231.md`.
4. Licensed timestamped quotes; G13/S63 genuinely independent numeric finance validation; do NOT enable valuation/ranking until all gates satisfied.
5. GitHub Pages owner activation remains outstanding. The current source smoke, PDF integrity and CLI tests passing do not imply live publishing.
6. Do not repeat 40 finished tests manually; check true workflow status first and only add tests that protect new functionality.

## Copy to next thread
VALUE HUNTER AI `osawamas/value-hunter-ai` を **v238** から継続。最新main、GitHub Actions REST run、`docs/data/latest.json`、`docs/data/sgx-original-pdf-sha-v233.json`、`docs/data/sgx-annual-report-sha-v237.json`、`docs/data/sgx-two-document-crosscheck-v238.json`、`docs/development-checkpoint-v238.md` を読む。v233でH02/V03決算PDFのSHA実取得し2回のActionsで一致、v236〜237で別の年次報告書2本のSHA実取得、計4原本を識別。v238で両社のFY2025/FY2024財務転記を照合し貸借・非支配持分の算術テスト追加。**GitHub Actions run 43609852535 40/40 PASS**。ただし異なる資料でも同じ発行体であり、独立財務監査ではなく、年次報告書の頁別再抽出・第三者照合が次の実務。財務7社・第三者候補182・ランキング適格0。UOB11/13/OCBC11/12のSGX原本、公式全銘柄と利用権限、時刻付き正規株価、G13/S63独立数値検証、Pages設定が未完。GitHub Pages公開ジョブは所有者設定未有効のためスキップ。完了した実装を繰り返さず、まずソースの証明とデータ取得に進む。
