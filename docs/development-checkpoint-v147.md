# VALUE HUNTER AI — v147 checkpoint (2026-11-14 JST)

## Start next work here
Read current main and latest GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-fy2025-audit-assurance-v132.json`, `docs/data/sgx-first-issuer-gate-v137.json`, `docs/data/sgx-annual-arithmetic-v140.json`, `docs/data/sgx-boardlot-subset-v142.json`, `docs/data/sgx-ocbc-2026q3-manifest-v143.json`, `docs/data/sgx-ocbc-2026q3-links-v144.json`, `docs/data/sgx-ocbc-2026q3-pdfs-v145.json`, `docs/data/sgx-ocbc-2026q3-bank-profit-v146.json`, and THIS file. Refer to `docs/development-checkpoint-v139.md` for older v97-v139 history. Do not repeat completed work.

## v140 — FY2025 audited issuer accounting arithmetic
- Added `SGX_PDF_connection_probe/annual_statement_arithmetic_v140.py`, strict adversarial tests, `.github/workflows/value-hunter-v140.yml`; CI [#43566016132](https://github.com/osawamas/value-hunter-ai/actions/runs/43566016132) SUCCESS.
- Published `docs/data/sgx-annual-arithmetic-v140.json`; G13 group assets 9,185,799, liabilities 980,383, group/parent equity 8,205,416 SGD thousands; minority interest 0.
- S63 group assets 16,032,106, liabilities 13,110,861, group equity 2,921,245, parent-attributable equity 2,573,638, calculated minority interest 347,607 SGD thousands. Balance equations 0 differences.
- Same-issuer audited financial statement arithmetic only: independent third-party numerical checking **0**, current quote verification **0**, ranking **0**. Linked to v132 auditor sidecar, not a separate audit of 2026 figures.

## v141 — Japanese accounting disclosure
- Added `docs/annual-arithmetic-v141.js`, `docs/test_annual_arithmetic_v141.js`, Japanese UI section and Pages test; new `.github/workflows/value-hunter-v141.yml`; CI [#43566195604](https://github.com/osawamas/value-hunter-ai/actions/runs/43566195604) SUCCESS.
- Explains 2025 Group vs owner-attributable equity and NCI, not a verified PBR. UI refuses stale sidecars. v140 also automatically refreshes after successful v132 opinion-sidecar update.

## v142 — official SGX board lot subset probe: no actual HTML master acquired
- Official public SGX trading page publicly lists 11 historical 10-share board lot issuers effective 2026-10-05 (D05 G07 H02 C07 J36 BN4 O39 K6S S68 U11 V03). Program `sgx_boardlot_subset_v142.py` and tests directly fetched `https://www.sgx.com/securities/trading`.
- Runner received only ~15KB generic HTML without 2026 announcement rows; current `docs/data/sgx-boardlot-subset-v142.json` **status NOT_VERIFIED**, response 15,338 bytes SHA `82b50cdb6fe73c6dabed0f47c55e962780e73d971c18193e10a85f4b90addb76`. CI [#43566383117](https://github.com/osawamas/value-hunter-ai/actions/runs/43566383117) SUCCESS as *diagnostic* only; not 11 codes machine verified, not a complete SGX official universe. Never promote.

## v143–v146: OCBC 3Q2026 original SGX source pipeline ACTUALLY WORKS
- **v143:** Direct SGX original `https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/` parsed and verified OCBC O39, ISIN SG1S04926220, announcement ref SG261106OTHRI4L9, broadcast 2026-11-06 06:59:27 SGT, fiscal period ended 2026-09-30, three exact attachment names. Published `docs/data/sgx-ocbc-2026q3-manifest-v143.json`, source HTML SHA `002307b35ed58271c17d03c00319e02ae51599d24396de4e6f7785e0a496df86`. Initial strict title-uniqueness condition failed on repeated generic title; fixed, final CI [#43566560712](https://github.com/osawamas/value-hunter-ai/actions/runs/43566560712) SUCCESS.
- **v144:** Extracted REAL official PDF attachment hrefs from the same hash-validated SGX announcement, `docs/data/sgx-ocbc-2026q3-links-v144.json`. All 3 URL paths are under the exact SGX announcement prefix; CI [#43566677605](https://github.com/osawamas/value-hunter-ai/actions/runs/43566677605) SUCCESS.
- **v145:** Direct GET of original three OCBC 3Q PDF attachments via SGX. Attachment URLs legitimately HTTP-redirect to **same SGX official domain** `/FileOpen/*.ashx?App=Announcement&FileID=...`, not an error. Adjusted code to accept ONLY official same-domain /FileOpen PDFs with PDF content-type and %PDF magic. Actual `docs/data/sgx-ocbc-2026q3-pdfs-v145.json` status `SGX_OCBC_Q3_THREE_ORIGINAL_PDFS_VERIFIED`, CI [#43566948645](https://github.com/osawamas/value-hunter-ai/actions/runs/43566948645) SUCCESS. Press release 9p, 401,720 bytes, SHA `420c481ac3eb12a667ef25d7ba7b8fb7ef3d62fb048ad673712c50ce7b75af53`; CEO presentation 4p, 1,002,190 bytes, SHA `1a2a289b9fb6b59e9b49b1865abbde173332bbfe5569e975c21e6a236180ab12`; Results Highlights 20p, 1,298,232 bytes, SHA `1111632e69e5dd3fdacbab8c6febc21f723949b5240b2e7c7947e4a675dbde16`.
- **v146:** Extracted exact reported bank performance from original SGX OCBC 3Q PDF (SHA verified against v145): 3Q26 GROUP net profit **2.04 billion SGD**, **+3% y/y**; 9M26 Group net profit **6.24 billion SGD**, **+10% y/y**. Figures are *issuer rounded release values*, not independently recalculated, not audited 2025 FY, not ordinary industrial revenue/operating income, and not current PER. `docs/data/sgx-ocbc-2026q3-bank-profit-v146.json` status `OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED`; CI [#43567095750](https://github.com/osawamas/value-hunter-ai/actions/runs/43567095750) SUCCESS. OCBC issuer website 6-Nov release agrees, but same issuer not independent verification.

## v147 — OCBC bank-only Japanese UI
- Added `docs/ocbc-quarter-v147.js`, adversarial `docs/test_ocbc_quarter_v147.js`, Japanese bank quarterly research table in `docs/index.html` and Pages tests, dedicated `.github/workflows/value-hunter-v147.yml`.
- Displays OCBC 3Q/9M rounded issuer profit with official SGX original PDF link and explicit unverified/hold-for-market-data warning. Does NOT promote financial feed, bank PER/PBR, shares or ranking.
- CI [#43567250214](https://github.com/osawamas/value-hunter-ai/actions/runs/43567250214) SUCCESS on actual public JSON and original PDF-derived sidecar.

## Last verified published state
- Main immediately before this checkpoint `f53406df62f52830751df28da7bf7677fc5bb595`.
- Latest `docs/data/latest.json`, v117, v132, v137, v140 sidecar timestamps ALL matched `2026-11-14T06:24:47.869760+00:00` on last check; v29 refresh Action #43567217039 was IN_PROGRESS and may supersede those. Recheck before trusting.
- Financial registered companies **7**; third-party partial StocksSG stock candidates **182**; eligible ranking **0**. G13/S63 FY2025 audited, own system arithmetic verified but **NOT independently numerically reperformed**. OCBC O39 2026Q3 now primary SGX PDF source and banking profit known but financial feed still bank-specific partially unparsed.
- G13 2026-06-30 ex-treasury shares officially proven only to June30. S63 buyback 2026-11-13 official dated source known but current execution quote not authenticated. S63 Yahoo+EODData share same historical close but upstream independence unproven. No authenticated official SGX quote API or full official current security master.
- **Still missing:** OCBC 2026-11-12 treasury-use original `SG261112OTHRXH64` and `Anno_12Nov2026.pdf`, UOB 2026-11-13 buyback original `SG261113OTHRHOAF`. Secondary ShareInvestor displays are not official originals.

## Next priorities v148+
1. Extend OCBC bank original PDF pipeline to exact-precision tabular financial statement values as distinct bank schema; avoid using rounded 3Q/9M management headlines as FY2025 audited net profit or PER. Compare 3Q highlights vs press release with PDF source hashes as same issuer independent-capture crosscheck, not external verification.
2. Search original UOB 13-Nov and OCBC 12-Nov notices using source-origin evidence or permitted announcement search, never guess unverified URLs. Specifically OCBC Nov12 attachment `Anno_12Nov2026.pdf` is still NOT retrieved.
3. Improve actual independent numerically validated FY2025 parent equity for G13 and S63 and a legally authorized timestamped SGX market quote; keep strict 8-category ranking gate.
4. Research official dated full SGX security master; the known 11-codes webpage v142 didn't expose rows to the GitHub runner.
5. Continue run/sidecar timestamps and concurrent git push safety. Do not change `ranking_eligible_count=0` without verified conditions.

## Short handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv147から継続。まずmain、Actions、`docs/data/latest.json`、`docs/data/sgx-annual-arithmetic-v140.json`、`docs/data/sgx-ocbc-2026q3-manifest-v143.json`〜`docs/data/sgx-ocbc-2026q3-bank-profit-v146.json`、`docs/development-checkpoint-v147.md`を読む。v140でG13/S63のFY2025連結会計算術整合（S63非支配株主持分347,607千SGD）を確認、独立数値検証とは別。v141で日本語UI化。v142の公式SGX板単位ページ取得はHTMLに表がなくNOT_VERIFIED。v143-v145でOCBC O39のSGX公式3Q26発表・添付PDF3本を取得し各SHA検証、v146で3Q26グループ純利益2.04b SGD（前年同期比+3%）・9M26 6.24b（+10%）を原本抽出、v147で銀行専用の日本語UIに追加。各実取得最終Actions成功。第三者候補182、財務登録7、ランキング適格0。次はOCBC銀行財務テーブル精緻化、UOB11/13とOCBC11/12原本、SGX公式全銘柄マスター、独立財務数値と日時付き正規株価の確認。未検証値を時価総額/PER/PBR/ランキングに昇格せずGitHubに継続保存。
