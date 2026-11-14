# VALUE HUNTER AI — v125 checkpoint (2026-11-14 JST)

## Next-session startup
Read current main and recent GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-g13-official-identity-v119.json`, `docs/data/sgx-g13-issuer-ir-market-v120.json`, `docs/data/sgx-g13-2026q3-v121.json`, `docs/data/sgx-g13-june10-shares-v122.json`, `docs/data/sgx-g13-share-date-gap-v124.json`, `docs/data/sgx-s63-9m2026-v125.json`, and this checkpoint. Do not repeat v97–v125 completed work.

## v120: unsuccessful HTML quote parsing (NOT data acquisition success)
- Added `SGX_PDF_connection_probe/g13_issuer_market_v120.py`, tests and `.github/workflows/value-hunter-v120.yml`. Workflows #43560976328 and #43561026781 both **CI SUCCESS** (unit tests / safe diagnostics).
- Actual `docs/data/sgx-g13-issuer-ir-market-v120.json` has `status=NOT_VERIFIED`, `record=null`; HTML returned by the issuer hosted `https://gentingsingapore.listedcompany.com/share-quote-and-chart.html` does **not** expose the expected trading quote fields as static text, likely dynamic rendering. Do **NOT** count the v120 quote scrape as working just because CI is green.
- Separate public web research showed G13 delayed quote 0.575 SGD at 13-Nov-2026 17:16 Singapore time and 12,063,642,274 shares tagged last updated 14-Aug-2026, but no stable authenticated machine capture. No quote or shares promoted.

## v121: SGX official Genting Singapore Q3-2026 PDF succeeded
- Discovered official SGX primary PDF: `https://links.sgx.com/FileOpen/Q3%202026%20GENS%20Quarterly%20Business%20Overview.ashx?App=Announcement&FileID=911200`; issuer announcement ref `SG261112OTHRSMFB` 12-Nov-2026.
- Added `SGX_PDF_connection_probe/g13_quarterly_sgx_v121.py`, tests, workflow. Initial workflow #43561159140 FAILED due missing PDF extraction utility; fixed workflow to install poppler. Further PDF layout fixes and tests completed. Final CI https://github.com/osawamas/value-hunter-ai/actions/runs/43561536883 **SUCCESS with real original parsed**.
- Published `docs/data/sgx-g13-2026q3-v121.json`: original PDF SHA256 `8ebef146c7b16cab1003fea562970cb554a43c3ba428dfadc291a577bfc32b9d`. 3Q ended Sep 30: revenue 566,096 thousand SGD vs 649,790 thousand SGD 3Q25 => **-12.88%**; net profit after tax 54,731 thousand SGD vs 94,618 thousand SGD => **-42.16%**.
- Issuer original explicitly states **management accounts not audited or reviewed**. Important: FY2025 PER is historical and not a current earnings multiple; do not recompute latest PER using only Q3 or assume independent financial verification. `ranking_eligible=false`.

## v122: SGX original Genting June 10 share buyback succeeded
- Exact primary `https://links.sgx.com/1.0.0/corporate-announcements/CHP29KEV0YJ4ZBNY/`, SGX ref `SG260610OTHRU53S`, 10-Jun-2026 17:55:09, G13 / ISIN SGXE21576413.
- Added `g13_sgx_buyback_v122.py`, tests/workflow. CI https://github.com/osawamas/value-hunter-ai/actions/runs/43561468165 **SUCCESS with original**.
- Saved `docs/data/sgx-g13-june10-shares-v122.json`: buyback 2,000,000 shares all treasury, 0 canceled, issued excluding treasury after June 10 12,063,642,274; treasury after 30,384,550. Original HTML SHA256 `89a2f83a284eceb02a6c4268164a34a6aad66b2b9418747ff24cad36a7de6b0f`.
- 10-Jun original cannot prove the same quantity on June 30 or November 14 without evidence of no intervening changes. No valuation promotion.

## v123: G13 Q3 risk appears in Japanese dashboard
- Added `docs/g13-quarter-warning-v123.js`, `docs/test_g13_quarter_warning_v123.js`; modified `docs/index.html`, `docs/app.js`, `.github/workflows/value-hunter-pages.yml`; added `.github/workflows/value-hunter-v123.yml`.
- CI https://github.com/osawamas/value-hunter-ai/actions/runs/43561722114 **SUCCESS** with actual `latest.json` + original v121 PDF derived JSON and adversarial tests. Shows G13 2026Q3 -12.88% revenue, -42.16% posttax profit with explicit unaudited warning and SGX PDF link in detail view.
- JS refuses to bind stale or conflicting financial record; neither PDF Q3 info nor Yahoo quote is promoted to price/PER/PBR/ranking. Pages validate CI succeeded, real live website browser inspection not claimed.

## v124: G13 shares-as-of discrepancy documented
- Added `g13_share_source_gap_v124.py`, negative tests and workflow; CI https://github.com/osawamas/value-hunter-ai/actions/runs/43561855854 **SUCCESS**.
- `docs/data/sgx-g13-share-date-gap-v124.json`: public financial feed `G13.shares_outstanding=12,063,642,274` with date `2026-06-30`, primary SGX original same amount dated `2026-06-10` (20-day gap).
- Quantity matches, but **official record does not independently substantiate the public feed's later June 30 date**, let alone current treasury-adjusted shares; `ranking_eligible=false`. Do not rewrite published shares to pretend official current verification.

## v125: ST Engineering latest 9M26 official PDF succeeded
- SGX official 13-Nov-2026 deck `https://links.sgx.com/FileOpen/ST%20Engineering%209M2026%20Market%20Update.ashx?App=Announcement&FileID=911321`.
- Added `s63_9m2026_sgx_v125.py`, tests/workflow; first CI #43562105616 FAILED due synthetic test minimum string length, fixed; final CI https://github.com/osawamas/value-hunter-ai/actions/runs/43562167829 **SUCCESS with actual primary PDF**.
- Saved `docs/data/sgx-s63-9m2026-v125.json`, official PDF SHA256 `5100bd6dca4541a28fd813ee21aec7729b554148ccc1d82fd9507465698744cd`. Presentation reports rounded 9M26 revenue 10.0b SGD, reported +10% y-o-y, rebased +13%; contract wins 13.2b SGD, order book 37.7b SGD as of 30 September 2026. These are management presentation highlights, NOT a fully audited 9M income statement or independent PER validation.
- S63 13-Nov official share buyback snapshot remains independently stored in v109, 3,115,847,115 shares excluding treasury **as of Nov 13**, no current quote independently verified. No ranking promotion.

## Last operational check
- At checkpoint creation most recent verified main before this document: `671a848a688eac05ecc39195909555835db10369` (expect another commit for this checkpoint).
- Latest feed and readiness sidecar timestamps both `2026-11-14T05:30:23.787965+00:00`, 7 financial registered issuers, 182 third-party StocksSG candidates, **0 ranking eligible**.
- v29 data refresh #43561694553 and #43561688579 successful; Pages #43561914254 successful, v117 readiness #43561914127 successful. Future refreshes may run concurrently. Recheck current main and Actions.

## Remaining priorities v126+
1. Investigate actual independent financial validation of G13 FY2025 and S63 FY2025 including parent equity, and account for latest 2026 interim movements; avoid treating issuer-to-issuer agreement as third-party audit.
2. Source newer SGX treasury-adjusted G13 share count after June 10 and independently date-match it to a genuine exchange price; G13 Q3 unaudited decline could affect valuation materially.
3. S63 current price provenance and new 13-Nov shares; 9M deck does not provide audited earnings for PER.
4. UOB Nov13 SGX original `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` PDF remain missing. Secondary mirrors cannot promote the share changes.
5. Complete official dated SGX security master still unavailable. Third-party 182 partial candidates not exchange complete.
6. Safe data UI may additionally show S63 9M2026 highlights but keep source type and period explicit. Check Pages live URL only if accessible.
7. Do not bypass `ranking_eligible_count=0` without independent required financial and current-market evidence.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv125から継続。main・最新Actions・`docs/data/latest.json`・`docs/data/sgx-g13-2026q3-v121.json`・`docs/data/sgx-g13-june10-shares-v122.json`・`docs/data/sgx-g13-share-date-gap-v124.json`・`docs/data/sgx-s63-9m2026-v125.json`・`docs/development-checkpoint-v125.md`を読む。v120発行会社IRの静的HTML株価解析はNOT_VERIFIED（CI成功と実データ成功を混同しない）。v121でG13公式SGX PDFを解析しQ3売上-12.88%、税引後利益-42.16%（未監査）を確認、最終CI #43561536883成功。v122でG13公式6/10買戻し後株式数12,063,642,274、自己株式30,384,550を検証、CI #43561468165成功。v123ではG13詳細に直近減収減益警告を実装、CI #43561722114成功。v124で公開株式数6/30と公式原本6/10の20日基準日差を可視化、CI #43561855854成功。v125でS63公式9M26デッキを実解析、売上10.0b SGD +10%、受注13.2b、受注残37.7b、CI #43562167829成功。財務登録7社、第三者候補182社、ランキング0社。最新株式数/独立株価/財務検証は未完。未検証数値を時価総額・PER/PBR・ランキングに昇格させず、SGX原本の取得・テスト・GitHub保存を継続。
