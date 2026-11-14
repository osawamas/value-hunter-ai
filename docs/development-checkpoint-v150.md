# VALUE HUNTER AI — v150 checkpoint (2026-11-14 JST)

## RESUME
Read latest `main`, GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-fy2025-audit-assurance-v132.json`, `docs/data/sgx-first-issuer-gate-v137.json`, `docs/data/sgx-annual-arithmetic-v140.json`, all OCBC files v143-v150 below, and `docs/development-checkpoint-v150.md`. Previous history recorded in `docs/development-checkpoint-v139.md` and `docs/development-checkpoint-v147.md`. Do not redo finished v97–v150 tasks.

## v140–v141 completed
- Audited-issuer FY2025 statement arithmetic for G13 and S63: G13 assets 9,185,799, liabilities 980,383, group/parent equity 8,205,416; S63 assets 16,032,106, liabilities 13,110,861, group equity 2,921,245, parent equity 2,573,638, computed non-controlling interest 347,607 (all SGD thousands). Exact balance equations matched; **same issuer statement arithmetic, NOT independent third-party numerical check**. Saved `docs/data/sgx-annual-arithmetic-v140.json`; CI #43566016132 SUCCESS.
- Japanese explanation and tables in `docs/annual-arithmetic-v141.js` and `docs/index.html`; v141 CI #43566195604 SUCCESS. v140 auto reruns after v132; stale sidecar hidden safely.

## v142 research: official SGX boardlot page NOT machine retrieved
- SGX public `https://www.sgx.com/securities/trading` web view showed 11 2026-10-05 historical boardlot symbols (D05/G07/H02/C07/J36/BN4/O39/K6S/S68/U11/V03). Direct GitHub runner server HTML however contains no stock table nor date; `docs/data/sgx-boardlot-subset-v142.json` status NOT_VERIFIED; 15,338-byte HTML SHA `82b50cdb6fe73c6dabed0f47c55e962780e73d971c18193e10a85f4b90addb76`; diagnostic CI #43566383117 SUCCESS. NOT proof of 11 official securities in our app and NOT official complete master.

## v143–v147 OCBC authentic SGX 3Q2026 source pipeline SUCCESS
- v143 parsed genuine OCBC O39 announcement `https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/`, ISIN SG1S04926220, broadcast 06-Nov-2026 06:59:27, ref SG261106OTHRI4L9 and 3 exact attachment names, status `SGX_OCBC_2026Q3_PRIMARY_ANNOUNCEMENT_VERIFIED`, original HTML hash `002307b35ed58271c17d03c00319e02ae51599d24396de4e6f7785e0a496df86`; CI #43566560712 SUCCESS.
- v144 extracted all 3 original attachment links from the same SHA-verified SGX page; `docs/data/sgx-ocbc-2026q3-links-v144.json`, CI #43566677605 SUCCESS.
- v145 fetched all 3 PDFs direct; official SGX internal redirect to `links.sgx.com/FileOpen/*.ashx` legitimately serves PDF. Changed guard to require same official SGX host/path, MIME and %PDF. Press release 9 pages SHA `420c481ac3eb12a667ef25d7ba7b8fb7ef3d62fb048ad673712c50ce7b75af53`; CEO presentation 4 pages SHA `1a2a289b9fb6b59e9b49b1865abbde173332bbfe5569e975c21e6a236180ab12`; results highlights 20 pages SHA `1111632e69e5dd3fdacbab8c6febc21f723949b5240b2e7c7947e4a675dbde16`. `docs/data/sgx-ocbc-2026q3-pdfs-v145.json`, CI #43566948645 SUCCESS.
- v146 parsed Q3 2026 OCBC group profit about **2.04b SGD, +3% YoY**, 9M2026 **6.24b SGD, +10% YoY** from original SGX press PDF by hash. Same-issuer reported rounded figures, NOT audited FY2025, NOT independent check, NOT input to PER/PBR/rank. `docs/data/sgx-ocbc-2026q3-bank-profit-v146.json`, CI #43567095750 SUCCESS.
- v147 added OCBC banking quarterly research table to Japanese `docs/index.html`, `docs/ocbc-quarter-v147.js` and tests; CI #43567250214 SUCCESS, source link and warning retained.

## v148–v150 further completed
- v148 fetched separate original OCBC Results Highlights PDF and compared rounded 3Q profit 2.04b SGD and +3% YoY with official press PDF. The 2 distinct SGX PDFs have different SHA256; values consistent. `docs/data/sgx-ocbc-two-pdf-crosscheck-v148.json` status `OCBC_3Q26_TWO_ISSUER_PDFS_ROUNDED_PROFIT_MATCH`; CI [#43567452456](https://github.com/osawamas/value-hunter-ai/actions/runs/43567452456) SUCCESS. **Both same issuer**, not third-party independence.
- v149 fetched original OCBC SGX press again with SHA and observed reported 3Q26 **net interest margin 1.66%**, **NPL ratio 0.8%**, **transitional CET1 CAR 15.5%**, **annualised ROE 13.1%**; `docs/data/sgx-ocbc-2026q3-bank-ratios-v149.json`; CI [#43567582782](https://github.com/osawamas/value-hunter-ai/actions/runs/43567582782) SUCCESS. These are issuer rounded textual public metrics, no independent source, no formal annualised PER, and no full detailed provision/credit-loss or bank balance table verification.
- v150 added a separate Japanese OCBC bank-health table and fail-closed checks in `docs/ocbc-bank-ratios-v150.js`, `docs/test_ocbc_bank_ratios_v150.js`, `docs/index.html`, plus dedicated workflow and Pages regression. CI [#43567738210](https://github.com/osawamas/value-hunter-ai/actions/runs/43567738210) SUCCESS with real original research data and without rank/valuation promotion. No live site browser screenshot confirmed.

## Last operational check
- Latest main before THIS checkpoint `8ef52bbdc90287d071294a407f1e7081efcc4fe6`.
- `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-fy2025-audit-assurance-v132.json`, `docs/data/sgx-first-issuer-gate-v137.json`, `docs/data/sgx-annual-arithmetic-v140.json` ALL matched timestamp `2026-11-14T06:37:30.913578+00:00` at last checked. v29 refresh #43567709881 was IN_PROGRESS and may advance feed; recheck timestamp coherence!
- Registered financial issuer records **7**; third-party StocksSG partial candidates **182**; ranking eligible **0**. G13/S63 FY2025 independent PwC auditor opinions exist, but our independent third-party numerical recalculation and authenticated current SGX prices still missing. O39 3Q26 bank-only metrics are separately sourced/rounded, NOT ranking eligible or generic industrial FY2025 annual metrics.
- SGX official complete current securities master remains unknown/unretrieved. SGX `sgx.com` shell returns HTML fallback on GitHub. No authenticated real exchange trade timestamp or licensed market price feed.
- Unresolved UOB 13-Nov SGX original `SG261113OTHRHOAF` and OCBC 12-Nov treasury-use original `SG261112OTHRXH64` / `Anno_12Nov2026.pdf`. ShareInvestor secondary announcements aren't exchange original.
- G13 official 30-Jun shares after treasury 12,063,642,274, NOT proven currently; S63 13-Nov official buyback 3,115,847,115, but not proven current market cap. 2026 interim earnings and prior annuals must not be blended into current PER.

## v151+ suggested priorities
1. Use authentic OCBC 3Q source attachment PDFs to extract precise banking income statement and balance table with subgroup/year columns, including provision and parent profit; classify separately from industrial earnings; do not declare independently validated until distinct third-party data.
2. Find UOB Nov13 and OCBC Nov12 authentic SGX corporate announcement originals, not only mirror pages; obtain treasury changes and active outstanding shares.
3. Seek complete SGX officially dated issuer/security master and authorized timestamped exchange quote; evaluate licensing. Do not invent current price.
4. G13/S63 independent FY2025 parent equity financial numerical verification and as-of-date compatible shares/quotes to satisfy strict v137 ranking gate.
5. Monitor concurrent v29→v117/v132/v137/v140 audit refresh and Pages test/actual live accessibility.
6. Preserve all guard flags: reference PER/PBR are unverified, `ranking_eligible_count=0` until proper evidence.

## Short next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv150から再開。main、最新Actions、`docs/data/latest.json`、`docs/data/sgx-annual-arithmetic-v140.json`、`docs/data/sgx-ocbc-2026q3-manifest-v143.json`〜`docs/data/sgx-ocbc-2026q3-bank-ratios-v149.json`、`docs/development-checkpoint-v150.md`を読む。v140でG13/S63のFY2025会計整合性（S63非支配株主持分347,607千SGD）、v141で日本語UI化。v142のSGX公式取引ページ自動HTML取得は表がなくNOT_VERIFIED。v143〜v145でOCBC O39のSGX公式3Q26発表と添付PDF3本をハッシュ検証。v146で四半期純利益2.04b SGD +3%、9か月6.24b +10%を原本解析、v147日本語表示。v148でプレスとハイライトの同一会社PDF2本の数値一致を照合、v149でNIM1.66%、NPL0.8%、CET1 15.5%、ROE13.1%をSGX原本より取得、v150日本語UI表示・テスト成功。財務登録7社、第三者候補182社、ランキング0社。次は銀行財務数値精緻化・UOB11/13・OCBC11/12 SGX原本、独立数値照合、最新自己株式控除後株数・正規の時刻付きSGX価格、公式銘柄マスターを優先。未検証値をPER/PBR/ランキングに昇格せずGitHubへ継続保存。
