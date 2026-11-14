# VALUE HUNTER AI development checkpoint — v166 (2026-11-14 JST)

## Next thread startup
Always read current GitHub `main`, recent Actions, `docs/data/latest.json`, sidecars v117/v132/v137/v140/v161, `docs/data/sgx-uob-issuer-ir-nov13-v163.json`, `docs/data/sgx-ocbc-bank-research-v166.json` and THIS checkpoint. Previous v97–v160 in `docs/development-checkpoint-v160.md`. Do not repeat completed work. Latest `main` observed prior to checkpoint: `563bcf08f57890dd6eda6e6dc698c49cd31da034`.

## v161 — explicit G13/S63 reference share-price date mismatch
- Added `SGX_PDF_connection_probe/share_quote_date_coherence_v161.py`, tests, workflow; published `docs/data/sgx-share-quote-date-v161.json` (latest refresh timestamp matching current feed).
- G13 finance feed share snapshot **2026-06-30** (SGX primary H1 verified 12,063,642,274 ex treasury); unofficial Yahoo share quote dated **2026-11-13**; gap **136 calendar days**. No evidence shares unchanged since June30, even though share freshness indicator called RECENT (180 days).
- S63 finance feed shares **3,119,304,988** as of 2026-06-30, unofficial quote **2026-11-13**, gap **136 days**. More recent SGX official corporate buyback original dated **2026-11-13** shows **3,115,847,115** ex treasury; no genuine trade-tape execution price or latest complete chain verified. Historic finance feed market cap/PER/PBR NOT independently time coherent.
- Hard guards: zero eligible, no source feed mutation, same-date verification FALSE, official quote FALSE. Initial original CI [#43571112430](https://github.com/osawamas/value-hunter-ai/actions/runs/43571112430) SUCCESS.
- **Later bug fixed:** v164-like change allows a newer genuine future *trade date* (e.g. Nov16) without accidentally treating June30 shares as latest, while rejecting improbable dates. A test initially failed because Nov16 was future relative to Nov14 runner; inject `today` in testing for deterministic simulation; after repair Actions [#43572001505](https://github.com/osawamas/value-hunter-ai/actions/runs/43572001505) **SUCCESS**. Older failed test runs #43571841526, #43571961666, #43571977536 superseded. v161 regenerates after successful v132 sidecar job with bounded main update push retries.

## v162 — user-visible share-price source date mismatch
- Added `docs/share-date-v162.js`, adversarial test, `docs/index.html` section, Pages test, `.github/workflows/value-hunter-v162.yml`.
- G13/S63 show actual share date, quoted day, 136-day gap, latest independent SGX snapshot date/share number and obvious NOT eligible warning. If feed timestamp differs from v161 sidecar, stale data fail-closed and hidden.
- Dedicated UI GitHub Actions [#43571266213](https://github.com/osawamas/value-hunter-ai/actions/runs/43571266213) SUCCESS, subsequent v162 #43571672763 SUCCESS. Browser-deployed visual not independently screenshot checked.

## v163 — UOB official issuer IR source research
- Found UOB corporate IR homepage `https://uob.listedcompany.com/` advertising issuer Nov13 share buyback announcement page `https://uob.listedcompany.com/sgx-announcements/news.html?id=2634252`. Secondary ShareInvestor ref `SG261113OTHRHOAF` and 13-Nov repurchases are *not* official SGX original.
- `SGX_PDF_connection_probe/uob_ir_nov13_v163.py` checks exact UOB IR URL identity; actual GitHub runner received only **2183-byte** noninformative HTML page, sha `4b3cb1259863506ca6bddbdc941bbe9ef7c5cf3d5ca35e71a6c245d389ac680a`, no announcement reference, buyback title or 13-Nov date, no SGX original links. `docs/data/sgx-uob-issuer-ir-nov13-v163.json` status `UOB_ISSUER_IR_PAGE_PARSED_IDENTITY_NOT_VERIFIED`. Actions [#43571458451](https://github.com/osawamas/value-hunter-ai/actions/runs/43571458451) SUCCESS *as negative diagnostic*; **do not claim UOB Nov13 original obtained or shares verified**.
- UOB secondary sources suggest 34,000 purchased/cancelled and 1,646,677,591 ex treasury on Nov13; must NOT promote until official genuine primary link verified. OCBC Nov12 original ref SG261112OTHRXH64 and attachment Anno_12Nov2026.pdf still pending.

## v165 — consolidate UI layout without deleting evidence
- Previously OCBC had SIX separate large visible 2026Q3 panels. Wrapped them in one accessible expandable `<details id="ocbcResearchGroup">` group in `docs/index.html`, summary shows year/quarter and explicit source/independence caveat. CSS in `docs/style.css`; all SIX original ID targets, scripts, and financial detail tables intact. Separate share-date risk table still remains outside accordion.
- `docs/test_ocbc_group_v165.js` verifies all unique panel and tbody IDs and keyboard focus CSS, older bank-source negative tests and ranking. GitHub Actions [#43571742306](https://github.com/osawamas/value-hunter-ai/actions/runs/43571742306) SUCCESS. No new market-data claims.

## v166 — one source-hash-bound OCBC bank research bundle
- `SGX_PDF_connection_probe/sgx_ocbc_bundle_v166.py` aggregates **SEVEN** existing issuer-data sidecars: v145 original three attachment proofs, v146 rounded, v149 bank ratios, v152 exact profit, v154 income components, v156 allowances, v159 balance. All nonoriginal values compared against the exact **same original SGX OCBC issuer PDF SHA** `420c481ac3eb12a667ef25d7ba7b8fb7ef3d62fb048ad673712c50ce7b75af53`. Original PDF `https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/910569_OCBC_3Q26_Results_Press_Release.pdf`.
- Strict cross-source arithmetic/units/periods:
  - 3Q26 group net profit 2,042 million SGD, 3Q25 1,978, net interest income 2,313, noninterest 1,420, allowances 52.
  - 9M26 group net profit 6,237 million SGD, 9M25 5,677, net interest 6,798, noninterest 4,933, allowances 424 (190 impaired +234 nonimpaired).
  - 3Q26 bank NIM 1.66%, NPL 0.8%, CET1 15.5%, ROE annualised 13.1% (all issuer rounded).
  - 2026-09-30 ordinary equity 60,899 million SGD versus equity attributable to Bank equity holders 63,347 million; total assets 731,689; net loans 366,929; nonbank deposits 461,462.
- Consolidated separate JSON `docs/data/sgx-ocbc-bank-research-v166.json` confirmed real; **not** injected into generic industrial financial feed or current PER/PBR/ranking. Sidecar marks independent third-party numbers FALSE, FY2025 auditor scope cannot certify 2026 interim, authenticated SGX quote FALSE, current treasury shares FALSE.
- Dedicated CI [#43571925799](https://github.com/osawamas/value-hunter-ai/actions/runs/43571925799) SUCCESS on exact real source sidecars and adversarial tests. All 7 input files remain available separately. This is same issuer evidence, not independent verification.

## Last operational state (recheck after latest v29)
- Before checkpoint GitHub main `563bcf08f57890dd6eda6e6dc698c49cd31da034` (checkpoint advances).
- `docs/data/latest.json`, v117, v132, v137, v140, v161 sidecars all had **identical timestamp** `2026-11-14T07:36:25.472621+00:00`. V161 latest Actions success #43572001505.
- Registered full financial records **7**; third-party StocksSG partial candidate names **182**; eligible ranking **0**. Full official current SGX securities master unavailable. Pricing sources Yahoo/EODData not authenticated SGX execution tape. G13/S63 independent FY2025 auditor opinions confirmed, independent numerical reperformance & compatible current quote/share state NOT confirmed.
- Do not confuse 180-day freshness heuristic with exact price/share date coherence. Do not treat a fresh JSON pipeline run as fresh original balance sheet, quote or shares.

## Next priorities v167+
1. Locate **actual** SGX corporate original for UOB Nov13 ref `SG261113OTHRHOAF` and OCBC Nov12 ref `SG261112OTHRXH64` and attachment `Anno_12Nov2026.pdf`. Avoid guessing FileID or promoting ShareInvestor secondary.
2. Investigate SGX official current master and lawful time-stamped trade/quote service (may be licensed), rather than copying inferred prices.
3. Existing v166 consolidated bank source bundle can be used in a future comparative bank-only summary to reduce redundant UI sections, keeping period/audit/independence labels.
4. Independent G13/S63 FY2025 parent equity and numerical crosschecks to satisfy strict v137 rank blockers; do not lower gates to force a rank.
5. Validate deployed Pages browser display and monitor v29→v117/v132/v137/v140/v161 sidecar timestamp propagation and source date logic after November trading resumes.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv166から継続。main、Actions、`docs/data/latest.json`、`docs/data/sgx-share-quote-date-v161.json`、`docs/data/sgx-ocbc-bank-research-v166.json`、`docs/development-checkpoint-v166.md`を読む。v161でG13/S63の6月30日株式数対11月13日株価の136日差を実データ検証、S63の11月13日公式株数3,115,847,115と公開JSON古い株数3,119,304,988が不一致。v162で基準日差を日本語画面に追加。将来の取引日テストが11月14日実行で失敗した問題は基準日注入で修正し最新CI #43572001505成功。v163でUOB 11月13日IRリンクを調べたが実HTMLから原本取得に失敗、未検証のまま。v165でOCBCの6つの調査表を1つの折りたたみに整理、全データは維持、専用CI成功。v166でSGX原本ハッシュに紐づくOCBC 2026Q3銀行財務の7原本データを一つの検証JSONに統合、専用CI成功。財務登録7社、第三者候補182社、ランキング0社。次はUOB11/13・OCBC11/12公式SGX原本、正式SGX全銘柄マスター、正規時刻付き株価、独立財務数値検証、v166銀行データの比較UIを優先。未検証値はPER/PBR/ランキングに昇格させずGitHubにコードとテストを保存。
