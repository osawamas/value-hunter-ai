# VALUE HUNTER AI — v197 checkpoint (2026-11-14 JST)

## Starting point and completed through v196
- Read `docs/development-checkpoint-v196.md`, GitHub main, `docs/data/latest.json`, existing G13/S63 FY2025 audited issuer records.
- v195 has separate bank-only FY2025 and 3Q2026 issuer financial presentation; 4 historical bank tests executed in an independent V8 Node assert/fs-compatible harness PASS, but GitHub Actions job results not observed.
- v196 has 11 official SGX 2026-10-05 board lot change securities (only a small official subset), 4 already financially registered; test run via V8 compatibility harness PASS, not proof CI. No full SGX master yet.

## v197: cross-publisher historical financial research
- Public third-party StockAnalysis financial pages `https://stockanalysis.com/quote/sgx/G13/financials/` and `https://stockanalysis.com/quote/sgx/S63/financials/` show FY2025 rounded amounts (millions SGD).
- Observed G13 FY2025 source issuer revenue 2,452.053m SGD vs third-party 2,452m; parent profit 390.346m vs third-party 390.35m.
- Observed S63 FY2025 issuer revenue 12,346.426m vs third-party 12,346m; parent profit 462.770m vs third-party 462.77m.
- **IMPORTANT NOT COMPARABLE**: External operating income on StockAnalysis G13 450.46m vs issuer official operating profit 506.609m; S63 1,144m vs issuer reported operations profit 843.116m (2025). The definitions/methodologies are not demonstrated equivalent. Do not replace the audited original issuer operating profit with either external aggregator number. S63 corporate financial highlights also publish BOP adjusted amounts (e.g. net profit 850.8m) different from **reported** net profit 462.770m. Do not confuse BOP with reported or count that as arithmetic failure.
- Third-party web numeric correspondence is limited support for rounded displayed revenue/profit, **not independent audit, independent data pipeline verification, complete parent-equity verification, licensed market data, or ranking readiness**.
- Added `docs/data/sgx-independent-figure-research-v197.json` commit `b0e895c0761e54518e2908af7f2c6450caadcb30`.
- Added source/period-aware browser module `docs/fy-third-party-figure-v197.js` commit `85219634203cdc4a0c2b84cad51cd96e7450bbed`; adds reference-only comparison panel in `docs/index.html` commit `a01f075c34781a4338544c707683a281125e6591`.
- Added fail-closed regression `docs/test_fy_third_party_figure_v197.js` commit `e7244a92b857cf0924ea5e67a35dca8215142d56`; direct test body executed in an in-process V8 Node-style shim and PASS with all seven negative mutations rejected.
- Added independent CI `.github/workflows/fy-external-crosscheck-v197.yml` commit `a071e530e0ad45d80302a49efea61ac00f893f32`.
- **No GitHub Actions actual job success observed**. Do not claim executed by GitHub Actions.
- No ranking eligibility or financial feed mutation, zero ranking candidates, seven registered.

## New useful discovery
- SGX official `https://www.sgx.com/stock-exchange/company-announcements?ANNC=ANNC13` search engine had an indexed 13-Nov-2026 entry at 17:41 for UOB daily buy-back, validating that an SGX announcement index entry exists. Web open shows SGX browser unsupported fallback; it does NOT expose original announcement contents or exact Section D values.
- The official UOB issuer investor relations `https://uob.listedcompany.com/` has a 2026-11-13 buyback announcement link `sgx-announcements/news.html?id=2634252`. Web open of that detail failed. The third-party ShareInvestor mirror still gives 1,646,677,591 shares, but neither this nor the SGX index is the SGX original detailed form; keep UOB 13 Nov unverified. OCBC 12 Nov official attachment unverified.
- New source leads must not be presented as downloaded original PDF or a formally independently verified share-count update.

## Next priorities
1. Inspect actual Actions job results through authenticated GitHub Actions UI or a connector that can list push-triggered runs. Empty combined commit statuses are not evidence of pass or fail. Fix any CI failures.
2. Try UOB issuer investor relations announcement detail from link id 2634252 and SGX announcement index with browser capable of SGX site interaction; get original 2026-11-13 filed form and source digest. OCBC treasury document `Anno_12Nov2026.pdf` original similarly.
3. Continue to research SGX official full dated securities master vs mixed types, currency-specific counters and companies; v196 11 official board-lot batch is NOT exhaustive.
4. Independently verify G13/S63 reported financial figures and parent equity from appropriately licensed independent provider or auditor-sourced raw documents. External aggregators use incompatible operating-income definitions, must be scoped.
5. Legitimate timestamped SGX trade quote + same-date share count + usage rights before current valuations/rankings.
6. Owner's GitHub Pages setup / successful publishing job still not confirmed.

## Next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v197から続行。main・最新Actions・`docs/data/latest.json`・`docs/data/sgx-independent-figure-research-v197.json`・`docs/data/sgx-official-batch-seed-v196.json`・`docs/development-checkpoint-v197.md`を読む。v195で銀行3社のFY2025銀行専用財務と3Q2026を時期を分けて画面統合、UOB IRとSGX PDFのハッシュ相違は別原本同数値として修正し4種類のテストをV8互換環境でPASS。v196ではSGX公式の10株売買単位対象11銘柄の限定的公式コード台帳（4社が登録財務と一致）を追加、公式全銘柄マスターではない。v197ではStockAnalysis G13/S63のFY2025第三者表示を発行体と照合し、収益・純利益の丸め一致を研究用記録、営業利益の定義不一致を比較不可として明記。独立数値監査の合格には昇格せず、CI本体は未確認。UOB11/13 SGX公式発表一覧に掲載あり、原本詳細は未取得。OCBC11/12原本も未取得。株価利用許諾・公式全銘柄マスター・独立財務検証・Pages公開未完。財務登録7社、第三者候補182、投資ランキング適格0。新しい検証研究を正式PER/PBRへ使わない。
