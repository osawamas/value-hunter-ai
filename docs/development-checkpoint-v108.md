# VALUE HUNTER AI — v108 checkpoint (2026-11-14 JST)

## Start here
Read current main, recent GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-master-reconciliation-v105.json`, `docs/data/sgx-d05-primary-code-link-v107.json`, `docs/data/sgx-bank-code-isins-v108.json`, and this file. Do not redo v97–v108.

## v108 completed and verified
- Added `SGX_PDF_connection_probe/sgx_bank_isin_v108.py`, `test_sgx_bank_isin_v108.py`, and `.github/workflows/value-hunter-v108.yml` to main.
- GitHub Actions https://github.com/osawamas/value-hunter-ai/actions/runs/43558415769 **SUCCESS**: offline tests and two actual live direct HTTP fetches from SGX official announcements, validating issuer name, security name, ISIN, ticker code, exact announcement reference and broadcast time. Both succeeded, published `docs/data/sgx-bank-code-isins-v108.json` by Actions.
- UOB: `https://links.sgx.com/1.0.0/corporate-announcements/EVZ7PV6QP0P5BMW5/e2580790f6fa4d225394e792ccd026674a9ed767eddb6a18355f1d4b3dadeb22`, UNITED OVERSEAS BANK LIMITED, U11, ISIN SG1M31001969, SG261015OTHR6VTS, 15-Oct-2026 17:24:00.
- OCBC: `https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/50dad2d3f2e1374d94921a9cad3497846885577d0c43cf2e1fe14c8c7f4764a6`, issuer OVERSEA-CHINESE BANKING CORPORATION LIMITED, security OVERSEA-CHINESE BANKING CORP, O39, ISIN SG1S04926220, SG261106OTHRI4L9, 06-Nov-2026 06:59:27.
- v107 already independently confirmed DBS D05 <-> SG1L01001701 historical SGX announcement, CI #43548766668 success. Thus D05/O39/U11 all now have *historical* SGX-hosted exact ticker–ISIN evidence. Not proof all three are currently actively tradable, nor a complete official exchange master.
- Safety: v108 official historical links 2/2, `official_master_complete=false`, `financial_feed_modified=false`, `ranking_eligible=false`. Unverified prices, current share counts, market caps, PER/PBR remain absent in public feed. SGX candidate list is 182 partial third-party candidates; financial feed still registers 7; ranking 0.

## Still open
1. UOB 13-Nov-2026 notice ref `SG261113OTHRHOAF` official primary document remains unverified, only secondary mirror. Do not promote 13-Nov buyback or current shares.
2. OCBC 12-Nov-2026 notice ref `SG261112OTHRXH64`, SGX-hosted PDF `Anno_12Nov2026.pdf` remains unverified, only secondary mirror. Do not promote shares.
3. Complete and dated downloadable official SGX master still not found. v105 reconciliation published status NOT_AVAILABLE; cannot call 182 complete SGX-listed or official verified.
4. v104 time+identity quote gate succeeded offline, but automatic actual trade-time quote fetching, symbol authentication and cross-source validation remain unfinished. Do not calculate valuations or ranking from researched quotes.
5. To extend issuer linkage, require exact SGX-hosted announcement URLs, individually observed matching issuer/ISIN/ticker, timestamp and source hash, never infer from third-party candidate metadata alone.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv108から継続。main、最新Actions、公開JSON、`docs/data/sgx-bank-code-isins-v108.json`、`docs/development-checkpoint-v108.md`を読む。v108でSGX公式発表のUOB U11/SG1M31001969、OCBC O39/SG1S04926220を実HTTP解析し、CI #43558415769成功。v107でDBS D05/SG1L01001701も公式発表を検証済み。3銀行のコード・ISIN対応は歴史的原本で確認できたが、現在の上場・株式数・株価の検証ではない。候補182社は第三者StocksSG、財務登録7社・ランキング0社。次はUOB11/13とOCBC11/12のSGX原本、公式マスター実取得、時刻付き実株価と独立照合を進める。未検証の数値を時価総額・PER/PBR・ランキングに入れず、CI成功までGitHubに保存。
