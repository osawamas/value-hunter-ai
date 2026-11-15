# VALUE HUNTER AI — v298 checkpoint (2026-11-15 JST)

## Resume
Start with latest main, Actions, `docs/data/latest.json`, this checkpoint and prior v297. The existing hourly automation must not be duplicated. Finance registered seven, official ranking eligible 0/7.

## v298 substantive new financial numbers from original IPO documents
- SGX original PDF byte SHA preserved and rechecked. 9DC Deluge audited combined annual statements *for FY ending 31 March*, reporting currency **SGD**, financial figures in thousands:
  - FY2024 113199 revenue, 33591 gross profit, 11753 profit for year, 23015 total equity
  - FY2025 139755 revenue, 42477 gross profit, 17896 profit for year, 38320 total equity
  - FY2026 116662 revenue, 38774 gross profit, 11800 profit for year, 49443 total equity
  - This is the **audited combined** table (Prospectus section SELECTED COMBINED FINANCIAL INFORMATION). Distinct separately presented **UNAUDITED PRO FORMA FY2026** revenue 116567, gross profit 38738, profit 11489 must never substitute for audited figures. 2026 annual revenue YoY against FY2025 ~-16.5%.
  - Historical original PDF SHA256 `6472db7e48bc45db8a056d196157d03589bf4ef880ee94eba3fd837b53c028de`.
- MIM Mi Material audited annual statements *for FY ending 31 December*, reporting **USD thousands**:
  - FY2023 revenue 39829, gross 14352, profit 4112, equity 87080
  - FY2024 revenue 46821, gross 19189, profit 8172, equity 86088
  - FY2025 revenue 65335, gross 23685, profit 10008, equity 95533.
  - MIM **UNAUDITED interim H1** comparison: 2025 H1 revenue 25617, gross 9560, profit 2879; 2026 H1 revenue 53655, gross 24634, profit 14284, equity 109052. H1 sales YoY about +109.5%; do NOT compare half year to prior full year.
  - Original PDF SHA256 `d6b49948af8167e6d2443ae22f7538907c46e94d62b414843e8444abc05f342c`.
  - 2026 9M issuer press release remains separately classified, not independent audit.
- Financial statements are historically audited by the firms named in original prospectuses; **app itself does not independently re-audit or certify current figures**. No SGX price licensing, no ex-treasury current shares, no formal investable rankings.

## Actual implementation
1. `docs/data/sgx-ipo-audited-historical-v298.json` contains audited financial values/date/currency/unit/source PDF SHA, explicit separated Deluge unaudited pro forma and Mi Material H1 interim.
2. `scripts/discover-sgx-ipo-statement-tables-v298.py` downloads original SHA-pinned PDF sources and locates financial table rows, producing research JSON in `build/research/`. GitHub Actions `.github/workflows/sgx-ipo-financial-table-v298.yml` first failed due to missing pdftotext, fixed; actual source discovery **#43677937335 SUCCESS** and annotated table contexts **#43677999500 SUCCESS**. Key find: Deluge audited FY2026 116662 differs from unaudited pro forma FY2026 116567.
3. `scripts/verify-sgx-ipo-statement-values-v298.py` re-downloads exact SGX original PDFs (strict SHA, size), runs pdftotext, checks fiscal heading audit status, exact revenue/gross/PAT/equity multi-column sequences, distinguishes 9DC proforma, handles MIM wrapped profit line (the source prints 'Profit for the financial' then 'year/period ...'), and writes verification artifact. `.github/workflows/sgx-ipo-audited-values-v298.yml` executes real network verification. Several fail-closed test runs during development were repaired; final **#43678630364 SUCCESS**: both 9DC and MIM all audited/interim rows matched, artifact `sgx-ipo-historical-audited-values-v298` ID `14147441532`.
4. `docs/sgx-ipo-financial-v298.js` exposes audited annual row table with within-issuer YoY revenue/gross margin + source and H1 revenue YoY separate, denies ranking and cross-currency blending. `docs/sgx-32-research.html` includes audited 9DC/MIM financial comparison table, without changing ranking feed.
5. `docs/test_sgx_ipo_financial_v298.js`: negative data mutation checks, exact finance values, source hashes, YoY chronology and HTML UI. Registered into `scripts/verify-evidence-v198.js`; observed source evidence suite **#43678361478 SUCCESS 87/87** and #43678359270 success.
6. `scripts/e2e-sgx-32-research-v296.mjs` extended real Chrome tests: six audited annual rows, no 9DC pro forma in rendered rows, MIM FY2025 revenue, filter/search/CSV behavior. **HTTP extracted ZIP Chrome #43678586660 SUCCESS** and **file:// double click Chrome #43678586603 SUCCESS**. These runs include 9DC/MIM new audited data table, produced ZIP artifacts.
7. Key commits v298: `c67e5a30` table discovery, `eaf53d46` workflow, `547db665` pdftotext fix, `18011d13` context, `5029028b` data, `80749e1f` verifier, `5e305f78` live verifier workflow, `a8d998ef` interactive table, `edf40a27` UI, `71d94f4a` test, `9fd1b24c` 87-test suite, `38b05f91` CI watch, `597b684b` browser E2E, `43b0b442` final wrapped MIM-profit parser fix.

## Remaining real blockers and next v299 work
1. Add audited equity ratio and operating result only if explicitly supported by original statement rows. Need period-safe annual operating-profit definition: 9DC other administrative/finance items, MIM audited operating income may not be presented with same standardized label. Never estimate missing operating income as net profit.
2. MIM 9M2026 update is not audited; separately reconcile 9M2025 if official source has actual comparable figures. Never treat 'adjusted PAT' as IFRS net income or annual comparison.
3. SGX October 2026 Monthly Statistics original PDF allegedly SG261112OTHREO8V still missing; 605 stock count based on secondary repost, not official original.
4. Current complete SGX active security universe, market price browser DISPLAY and backend NON-DISPLAY licenses, independent original latest share count and UOB/OCBC November notices missing. Formal ranking remains 0 / 7.
5. Existing hourly automation active. No duplicate.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v298から継続。最新main/Actions/latest.json/development-checkpoint-v298.mdを読む。9DC監査済み3月期FY2024/25/26のSGD千単位売上113199/139755/116662、純利益11753/17896/11800、自己資本23015/38320/49443。未監査プロフォーマFY2026売上116567は混同禁止。MIM監査済み12月期FY2023/24/25のUSD千単位売上39829/46821/65335、純利益4112/8172/10008、自己資本87080/86088/95533。MIM未監査H1 2025/26売上25617/53655は別比較。二社のSGX原本PDFを再取得してSHA固定＋年度表・監査区分を直接照合したActions #43678630364 成功、87/87既存全体CI #43678361478 PASS、ブラウザHTTP #43678586660 とfile:// #43678586603 成功。詳細はSGX32件ページに財務表を追加。正式ランキング0/7で許諾株価/全SGX現在台帳なし。次は出典が明確な営業利益と財務健全性指標を正しい期間で追加する。毎時自動タスク維持。
