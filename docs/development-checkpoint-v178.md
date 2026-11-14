# VALUE HUNTER AI development checkpoint — v178 (2026-11-14 JST)

## Resumption procedure
Check latest GitHub main, GitHub Actions, docs/data/latest.json, docs/data/sgx-ranking-readiness-v117.json, docs/data/sgx-fy2025-audit-assurance-v132.json, docs/data/sgx-first-issuer-gate-v137.json, docs/data/sgx-annual-arithmetic-v140.json, docs/data/sgx-share-quote-date-v161.json and this checkpoint. Read docs/development-checkpoint-v167.md for earlier v97–v167. Do not repeat finished work. Last main before checkpoint: ac4e8961b2c7dbdd23f127a1bd2a1cfbedfbf8e4.

## v168 — remove unsafe valuation comparisons in main sortable shortlist
- Previously G13 S63 S68 S20 displayed reference market cap/PER/PBR using Yahoo price quotes and historical shares from distinct periods; despite warnings, this was risky in the main ranking-like table.
- Added docs/reference-valuation-guard-v168.js and docs/test_reference_valuation_guard_v168.js. Main docs/app.js now uses referenceValuationDisplayPermitted() in listed cells and sorting; current unauthenticated values show "—（株価と株式数の基準日不一致）" or "—（基準日未確認）", rather than numerical comparative values. Historical figures remain in detailed RESEARCH disclosure and historical chart, clearly labeled not formal current valuations. No source data is modified; ranking count remains 0.
- GitHub Actions [#43581748246](https://github.com/osawamas/value-hunter-ai/actions/runs/43581748246) SUCCESS. Applied to all registered issuers with unverified quote/share matching, not only G13/S63. Feed v29 still contains reference numbers for historical research, not ranking.

## v169 — big three banking evidence coverage with period separation
- Added docs/bank-coverage-v169.js and test and a Japanese banking research table in docs/index.html. D05 FY2025 original issuer annual profit attributable to parent 10,933m SGD and parent shareholder equity 68,867m; O39 2026-09 Q3 original group net profit 2,042m and ordinary equity 60,899m. These are **different reporting periods/equity definitions**, never compare as a ranking or current PBR. U11 was initially unverified for 3Q. Finance feed rows all seven remain partial/ineligible.
- After modification to require additional direct original D05 and U11 source files, latest v169 workflow [#43582384911](https://github.com/osawamas/value-hunter-ai/actions/runs/43582384911) SUCCESS, older transient failed runs superseded by newer v171/v173/v176 successful dedicated workflows.

## v170 — DBS D05 original SGX 2026-11-05 Q3 official announcement and CFO PDF acquired
- Found and runner-verified original `https://links.sgx.com/1.0.0/corporate-announcements/PWUTJ371L9ASOMF8/3044419f7294ad033fa90ebb2386da5245d415e663ece3af98d4448469034599`.
- Issuer DBS GROUP HOLDINGS LTD, security SG1L01001701 / D05, announcement ref SG261105OTHRTOOX, broadcast 05-Nov-2026 06:30:36 SGT, period ended 2026-09-30.
- Direct official PDF `https://links.sgx.com/FileOpen/3Q26_CFO_presentation.ashx?App=Announcement&FileID=910441`, 22 pages, SHA `bd9351bfeef24f5345848c574017b25c3ff5b4e292c78d6950aebd7cde761695`.
- Observed issuer-rounded 3Q26 group net profit 2.81b SGD, 9M26 8.82b, 3Q group NII 3.71b, NPL 0.9%, transitional CET1 15.9%. Saved docs/data/sgx-dbs-2026q3-original-v170.json. Dedicated Action [#43582224014](https://github.com/osawamas/value-hunter-ai/actions/runs/43582224014) SUCCESS. This is not FY2025 auditor checking 2026 interim, no current pricing/ranking.

## v171 — DBS/OCBC quarter UI 
- Period-safe Japanese bank table now shows D05 Q3 profit approx **2,810m SGD (rounded)** vs O39 **2,042m SGD (precise)**. FY2025 D05 profit remains separate. Exact source status and SHA are mandatory. Negative tests reject pricing or audit promotions. Actions [#43582419218](https://github.com/osawamas/value-hunter-ai/actions/runs/43582419218) SUCCESS.

## v172–v175 — UOB U11 direct ORIGINAL SGX CFO slides and exact table
- Unlike unresolved Nov13 buyback, official 3Q SGX result attachment **was found**: `https://links.sgx.com/FileOpen/3Q26%20CFO%20presentation%20slides.ashx?App=Announcement&FileID=910319`.
- v172 `sgx_uob_q3_v172.py` downloaded/verified original 20-page SGX PDF, SHA `d3b474aa87a2f2741bf68754a2f38b7189d905a8ff2bf6c51f88b758c867ec18`; source annual comparison/buyback independence flags FALSE. docs/data/sgx-uob-2026q3-cfo-v172.json Action [#43582546304](https://github.com/osawamas/value-hunter-ai/actions/runs/43582546304) SUCCESS.
- v173 bank research coverage now includes D05/O39/U11 issuer 2026 Q3 original numbers. Initial U11 Q3 **1,250m** net profit was observed anywhere in PDF, but not table column verified. Dedicated Action [#43582680298](https://github.com/osawamas/value-hunter-ai/actions/runs/43582680298) SUCCESS.
- v174 `sgx_uob_table_v174.py` extracted exact printed UOB PDF page3 bank financial table lines and 8-column contexts, saved docs/data/sgx-uob-quarter-table-rows-v174.json; Action [#43582769529](https://github.com/osawamas/value-hunter-ai/actions/runs/43582769529) SUCCESS.
- v175 `sgx_uob_exact_table_v175.py` verified original hash and unique table row labels and exact **9M26 / 9M25 / 3Q26 / 2Q26 / 3Q25** columns:
  - Net profit: **3Q26 1,250m**, 3Q25 443m, 9M26 4,165m, 9M25 3,271m.
  - Net interest income: 3Q26 **2,278m**, 9M26 **6,900m**.
  - Net fee income: 3Q26 **733m**, 9M26 **2,035m**.
  - Total income: 3Q26 **3,381m**, 9M26 **10,398m**.
  - All SGD millions, original PDF page3; saved docs/data/sgx-uob-exact-bank-table-v175.json, Action [#43582889192](https://github.com/osawamas/value-hunter-ai/actions/runs/43582889192) SUCCESS. Source document itself (not UOB Nov13 treasury notice) is verified. Independent third party annual audit, current SGX quote and buyback original still NOT verified.
- v176 bank UI requires both v172 original PDF hash and v175 exact quarter table, and labels UOB results "原本表の列まで照合" without claiming third party independence. Dedicated Action [#43583016620](https://github.com/osawamas/value-hunter-ai/actions/runs/43583016620) SUCCESS. Older v169/v171 regression tests updated to require the added source.

## v177–v178 — all three banks 3Q26 net-interest-income subtotal
- DBS **more precise original trading-update PDF** `https://links.sgx.com/FileOpen/3Q26_trading_update.ashx?App=Announcement&FileID=910439`, SHA `c8d55126a0ad0702771ac74ab2f2b79a0f7721223de53faae1197974eca617d6`; original PDF includes 3Q26 exact NII 3,711m SGD and 9M26 10,786m. The extraction confirms original full-text values, but single precise DBS table row/column alignment still FALSE, unlike UOB.
- v177 joins 3 original source SHA-checked records: DBS **3,711m**, OCBC **2,313m**, UOB **2,278m**, calculates **8,302m SGD** Q3 total, in docs/data/sgx-big3-nii-v177.json. SGX's editorial market update `https://www.sgx.com/research-education/market-updates/20261106-sti-banks-report-16th-consecutive-quarter-s8b-nii` also reports that total and per-bank values (observed through public web search), but the GitHub runner did NOT fetch its HTML, recorded explicitly `sgx_editorial_update_html_fetched_by_pipeline: false`. Cannot mark it an independently audited financial result.
- v177 Action [#43583144417](https://github.com/osawamas/value-hunter-ai/actions/runs/43583144417) SUCCESS with direct actual DBS primary PDF and previously verified O39/U11 originals.
- v178 adds bankNiiRows and bankNiiStatus in the same Japanese bank coverage panel, with source/quarter/SHA validation via docs/bank-nii-v178.js and tests, plus Pages regression. Dedicated Actions [#43583339043](https://github.com/osawamas/value-hunter-ai/actions/runs/43583339043) SUCCESS. Displays DBS 3,711 / OCBC 2,313 / UOB 2,278 / total 8,302 million SGD. Ranking remains 0.

## Latest operational checks
- Latest observed main before saving this checkpoint: `ac4e8961b2c7dbdd23f127a1bd2a1cfbedfbf8e4`. Checkpoint commit will supersede.
- `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-fy2025-audit-assurance-v132.json`, `docs/data/sgx-first-issuer-gate-v137.json`, `docs/data/sgx-annual-arithmetic-v140.json`, and `docs/data/sgx-share-quote-date-v161.json` all matched update timestamp **2026-11-14T10:02:20.731740+00:00** after latest v29 refresh. Recent cascaded GitHub Actions v29 #43583288715, v132 #43583413841, v117 #43583413848, v137 #43583440078, v140 #43583440083, v161 #43583440155 ALL SUCCESS.
- Financial registered issuers **7** (S68/G13/S20/S63/D05/O39/U11), third-party partial StocksSG candidate list **182** (NOT all SGX), ranking eligible **0**. No authenticated current SGX execution tape quotes; current company shares after treasury not validated as-of quote trade date; no independent numerical reperformance of all key valuation metrics.
- **Unresolved** UOB Nov13 buyback original `SG261113OTHRHOAF` and OCBC Nov12 treasury shares original `SG261112OTHRXH64`, attachment `Anno_12Nov2026.pdf`. UOB issuer IR direct page returns 2,183-byte shell to GitHub runner (v163), does not certify the Nov13 transaction. Do not promote ShareInvestor mirror.
- Official dated current complete SGX security master not obtained. `sgx.com` SPA HTML not directly machine verifiable via current GitHub runner.
- No true user-browser screenshot of live GitHub Pages checked; Actions success proves build and internal test not that all client devices render.

## v179+ priority
1. Seek true original Nov13 UOB buyback and Nov12 OCBC treasury use (announcements above), and obtain current validated ex-treasury shares. Distinguish from original result presentations.
2. Find suitable authorized/legally usable SGX quote/tape with timestamp and correct currency; independent price and share effective-date consistency.
3. Improve DBS 3Q primary NII table row-and-column validation (currently original value observed), then compare SGX bank editorial page in actual runner if SGX blocks allow it; maintain truthful publisher attribution.
4. Extend original SGX current complete security universe list beyond third-party 182 names, respecting public access constraints.
5. Independently verify G13/S63 FY2025 owner equity and earnings numbers against independent accounting work, not just issuer documents and auditor existence; v137 strict rank gate 1/8 remains.
6. Reuse v166 OCBC, v175 UOB, v170 DBS bank research components for annual- vs interim-period-safe comparison; don't conflate ordinary equity vs full attributable equity, or 2025 audit with 2026 interim.

## Short copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv178から続行。最新main/Actions、`docs/data/latest.json`、`docs/data/sgx-dbs-2026q3-original-v170.json`、`docs/data/sgx-uob-exact-bank-table-v175.json`、`docs/data/sgx-ocbc-bank-research-v166.json`、`docs/data/sgx-big3-nii-v177.json`、`docs/development-checkpoint-v178.md`を読む。v168で株価/株数の基準日不一致から未検証時価総額・PER・PBRを一覧非表示にし詳細研究値は維持。v169で銀行3社の期間別研究表を追加。v170でDBS公式SGX11/5発表と22p CFO PDFを実取得、3Q純利益約2.81b/9M約8.82b SGD。v171画面連携。v172でUOB公式SGX20p CFO PDFを取得、v173画面連携、v174実表の行配置発見、v175でUOB3Q純利益1,250m/9M4,165m SGD、3Q純金利2,278mを正しい列から抽出、v176画面更新。v177でDBS公式SGXの精密NII3,711mとOCBC2,313m/UOB2,278mを突合し3社合計8,302m SGD、v178日本語画面へ追加。専用実データGitHub Actions最終版すべて成功。登録財務7社、第三者候補182、ランキング適格0。SGX正規の時刻付き市場価格・最新自己株式控除後株数・公式完全銘柄マスター・独立財務数値検証は未完。次はOCBC11/12・UOB11/13買戻しSGX原本、現在の株式数と価格、DBS財務表精密値の検査を優先。GitHubにコード、テスト、引き継ぎを保存して続ける。
