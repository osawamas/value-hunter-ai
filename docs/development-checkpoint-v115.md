# VALUE HUNTER AI — v115 checkpoint (2026-11-14 JST)

## Start from here
Read current GitHub main, latest Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-bank-secondary-quotes-v112.json`, `docs/data/sgx-bank-secondary-crosscheck-v113.json`, `docs/data/sgx-bank-intraday-v114.json`, `docs/data/sgx-bank-daily-intraday-v115.json`, and this checkpoint. Do not repeat v97–v115.

## Previously pending v29 / Pages status
- The v29 dashboard refresh actions #43558873439 and #43558880887 eventually completed SUCCESS. The earlier concurrent #43558877992 was cancelled. GitHub Pages validate #43559092917 and #43559001821 succeeded. These CI results do not establish live Pages access.
- At v112 start main was `1b57167755e8bbe96c570ade196191a2a9aa7541`, dashboard feed refreshed 2026-11-14T04:55:54Z. 7 registered companies, ranking eligible 0. Third-party StocksSG candidate count 182. S63 still has older 2026-06-30 share count in `latest.json` and an isolated warning via v110/v111.

## v112 actual secondary chart retrieval
- Created `SGX_PDF_connection_probe/sgx_yahoo_dated_v112.py`, negative tests and workflow. https://github.com/osawamas/value-hunter-ai/actions/runs/43559348724 **SUCCESS**.
- Actual direct Yahoo Finance daily chart JSON fetched by GitHub runner for D05, O39, U11; valid symbol `.SI`, SGD, Asia/Singapore, EQUITY and dated bar arrays. Saved `docs/data/sgx-bank-secondary-quotes-v112.json`. 2026-11-13 daily close research: D05 69.900002, O39 28.530001, U11 37.75 SGD, all same calendar day. Daily bar timestamp 2026-11-13 01:00 UTC corresponds to daily bar opening convention, **not an actual last execution time**.
- Data classified `YAHOO_UNOFFICIAL_DAILY_CHART`; `verified_exchange_quotes=0`; no market-cap/PER/PBR/ranking promotion.

## v113 actual research comparison
- Added `sgx_bank_secondary_crosscheck_v113.py` and regression tests. https://github.com/osawamas/value-hunter-ai/actions/runs/43559484853 **SUCCESS**.
- Published `docs/data/sgx-bank-secondary-crosscheck-v113.json`: Yahoo daily 2026-11-13 closes vs archived secondary website historical close research in `latest.json`. D05 69.90 / O39 28.53 / U11 37.75 matched to cent (3/3).
- **Not** official SGX original data or independently exchange-validated. D05 historical Investing.com 70.14 disagreement remains noted in `latest.json`. This test only checks selected values.

## v114 actual secondary intraday extraction
- Added `sgx_intraday_v114.py`, negative tests and GitHub Action. https://github.com/osawamas/value-hunter-ai/actions/runs/43559606808 **SUCCESS**.
- Direct Yahoo Finance 5-day, 5-minute chart acquisition succeeded 3/3; `docs/data/sgx-bank-intraday-v114.json` has 426 eligible daytime bars per bank.
- Last 5-minute bar timestamp 2026-11-13 09:00 UTC = 17:00 Singapore time. Last bar prices D05 69.900002, O39 28.530001, U11 37.75. **This interval timestamp is NOT authenticated actual SGX last trade time**, and Saturday 14-Nov means the prices are historical Friday bars, not a live Saturday quote.
- `official_exchange_trade_data_count=0`, `promoted_to_financial_feed=false`.

## v115 same-provider daily vs intraday consistency
- Added `sgx_daily_intraday_consistency_v115.py`, negative tests, and workflow. https://github.com/osawamas/value-hunter-ai/actions/runs/43559684541 **SUCCESS**.
- Actual v112 vs v114 captures show matching session date and rounded price on all 3 bank counters, published `docs/data/sgx-bank-daily-intraday-v115.json`: `matching_price_count=3`, `official_exchange_confirmed_quotes=0`.
- **Same Yahoo provider**, even though two distinct API captures. This is NOT independent market-price corroboration. Never infer official exchange price or current valuation from this agreement.

## Further official-source research still unresolved
1. UOB 2026-11-13 SGX filing `SG261113OTHRHOAF` original (secondary mirror only); official original not verified.
2. OCBC 2026-11-12 `SG261112OTHRXH64` original PDF `Anno_12Nov2026.pdf` not retrieved.
3. Dated and complete SGX official security master not retrieved. 182 candidates from StocksSG are third-party partial, not exchange verified; v105 master status `NOT_AVAILABLE`.
4. Exchange-authenticated timestamps and market quotes, independently verified current treasury-adjusted shares, and necessary independent financial checks must precede any valuation promotion. Ranking remains 0.
5. v104 fail-closed quote gate is an offline research input validator, not a live authorized exchange market data connector.

## Recommended next development (v116+)
- Add a durable freshness/regular-session UI or published diagnostic for the secondary intraday observations clearly marked historical/non-exchange; do NOT overwrite `latest.json`.
- Continue identifying actual SGX corporate announcement URLs from official search/link evidence, not by guessing.
- Seek authentic bulk SGX security master/download and adapt the schema to the real export, not the hypothetical v105 CSV headers.
- Build independent exchange-quote verification if a legal accessible reliable source is found. Do not mix same-provider multiple captures with independent confirmation.
- Check all preceding Actions and main before new commits.

## Short next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv115の続きから進める。まずmain、Actions、`docs/data/latest.json`、`docs/data/sgx-bank-secondary-quotes-v112.json`、`docs/data/sgx-bank-secondary-crosscheck-v113.json`、`docs/data/sgx-bank-intraday-v114.json`、`docs/data/sgx-bank-daily-intraday-v115.json`、`docs/development-checkpoint-v115.md`を読む。v112 CI #43559348724でYahoo Financeの日足をD05/O39/U11とも実取得、11/13終値69.90/28.53/37.75 SGD。v113 #43559484853で既存第三者過去終値と3社一致。v114 #43559606808で5分足3社実取得、11/13 17:00 SGT最終バー、約定時刻ではない。v115 #43559684541で日足と5分足の同一provider内部整合3/3。すべて第三者の研究値で公式SGX取引記録ではなく時価総額・PER/PBR・ランキングに使用しない。登録7社、第三者候補182社、ランキング0社。UOB11/13とOCBC11/12原本、SGX公式全銘柄マスター、独立したSGX株価と最新株式数の認証は未完。GitHubに実装/負例テスト/公開データとチェックポイントを保存して開発を続ける。
