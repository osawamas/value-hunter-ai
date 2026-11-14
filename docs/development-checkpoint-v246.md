# VALUE HUNTER AI — v246 checkpoint (2026-11-15 JST)

## Start here
- Repository `osawamas/value-hunter-ai`. Read latest main/Actions, `docs/data/latest.json`, `docs/development-checkpoint-v245.md`, and this file before editing; other tasks may update main.
- Before v246, main `68bceb0d8e995f6c9c5fcda50ac718c4bc198ab0`. Final v246 code SHA `df75a676ee8f8556ff13fb53ea52d20dac7dc42d` plus checkpoint commit. Do not revert v245 browser source verification.
- v245 was 45/45 CI success. Registered financial feed 7 companies, ranking eligible 0. Candidate universe 182 from incomplete third-party provider, not official master. SGX quote redistribution license not obtained, Pages public deployment not confirmed.

## Current missing originals
- UOB (U11) original SGXNet 2026-11-13 `SG261113OTHRHOAF`: exact official original URL still NOT found. Secondary mirror shows its figures but cannot be promoted to official latest shares.
- OCBC (O39) `SG261112OTHRXH64` `Anno_12Nov2026.pdf`: metadata from syndicated secondary only; exact original SGX PDF URL and bytes still NOT obtained. No invented PDF FileID, no copied share value.
- Internet search 2026-11-15 found only secondary ShareInvestor listings, links to UOB SGX disclosures index and member-gated filing viewers; no actual original for those two cases. Do not pretend missing data have been independently confirmed.

## v246 actual implementation and tested safeguards
- New `scripts/probe-sgx-original-v246.js`: explicitly provided SGX announcement PDF URL only, allow `https://links.sgx.com/FileOpen/...ashx?App=Announcement&FileID=<digits>` or `https://links.sgx.com/1.0.0/corporate-announcements/<id>/<filename>.pdf`. Reject unapproved domains, ports, credentials, unsafe paths, unexpected query arguments and redirects off SGX domain. Manual redirect cap 4, 20s timeout covering download, 12 MB size limit, PDF magic-header requirement. Compute SHA256 over actual response bytes, record original and final URLs and byte length under `build/research/sgx-original-pdf-v246-U11.json` or `...-O39.json`.
- Provenance record explicitly marks issuer announcement identity, extracted accounting, independent financial verification, latest shares, quote licensing, ranking as **FALSE**. Passing byte-provenance test does not identify issuer or imply financial truth.
- New workflow `.github/workflows/sgx-original-pdf-probe-v246.yml` provides `workflow_dispatch` manually supplied symbol and exact SGX PDF URL. Uploads the SHA metadata as a private Actions artifact retained 30 days; does not publish the PDF. **Not yet triggered for UOB Nov13 or OCBC Nov12** because original URL unknown.
- New `docs/test_probe_sgx_original_v246.js` checks valid/invalid URL scope, PDF header and size, disallowed issuer, and non-promotion. Added to `scripts/verify-evidence-v198.js` and `.github/workflows/bank-corporate-actions-v191.yml`.
- Commits: feature `19fa8476`, streaming timeout `65816166`, test `415ccf39`, strict URL query guard `b57a20cf`, test fix `12cf93cb`, manual workflow `593f510b`, suite `d123a793`, trigger `a89254a6`.
- First CI `43613575083` FAILED 45/46 due a JS regex escaped as `/^\\d+$/` instead of digit `/^\d+$/` for FileID; fixed commit `df75a676ee8f8556ff13fb53ea52d20dac7dc42d`. Real final Node20 Actions [43613649188](https://github.com/osawamas/value-hunter-ai/actions/runs/43613649188), job 132503900887 **completed SUCCESS**: log `PASS docs/test_probe_sgx_original_v246.js` and `Evidence smoke suite: 46/46 passed; rankings remain independently gated.`

## Priorities after v246
1. Identify real original SGX URLs for UOB Nov13 and OCBC Nov12 (no guessing FileIDs). Use v246 manual probe once authenticated links found; inspect PDF/HTML pages for actual share effects; only then amend source records and date-qualified views.
2. Official full SGX dated security master; the 11-name 10-share-lot subset from v241 and third-party partial 182 are not sufficient.
3. Obtain permissioned SGX executed-quote market-data feed with trade timestamp, currency, processing and redisplay rights; no unauthorized scraping.
4. Independent numeric financial audit and parent equity (e.g. H02), establish eligible ranking only when gates truly pass.
5. Confirm actual successful GitHub Pages deployment. Prior Pages jobs SKIPPED because owner settings.

## Copyable next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv246から続ける。main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v246.md`を読む。v245まで銀行株数の画面照合済み。v246でSGX原本PDF専用の手動取得器 `scripts/probe-sgx-original-v246.js` とworkflow `.github/workflows/sgx-original-pdf-probe-v246.yml` を実装。SGXドメイン限定/URLパターン/リダイレクト/12MB制限/PDFヘッダ/SHA256を検証、PDF本体は再配信しない。取得レポートは未検証判定を明示する。Actions #43613649188 46/46 PASS。UOB11/13・OCBC11/12原本の本物のURLはいまだ不明で、取得器未実行。財務7社、第三者候補182社、ランキング適格0社、正規SGX時刻付き株価許諾・公式全銘柄・独立財務監査・Pages公開は未完。推測で数字を登録しない。原本URL探索と実際のデータ取得を優先し進める。
