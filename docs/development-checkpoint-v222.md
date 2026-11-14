# VALUE HUNTER AI — v222 checkpoint (2026-11-14 JST)

## Starting main & current state
- Continued from `docs/development-checkpoint-v219.md`. Latest observed main head before checkpoint `e2b823ab8ce041738de67fcbadce06ef1df5d266`.
- Main `docs/data/latest.json` refreshed by existing asynchronous pipeline to `2026-11-14T14:23:24.025478+00:00` during the session. **Financial records 7, ranking eligible 0, ranking disabled**; candidate 182 and SGX official v196 lot-size subset 11 are distinct scopes.
- GitHub push-triggered Actions runs are still NOT independently retrieved by connected Github tool. Public GitHub Actions URL and public REST listing were cache misses. `scripts/verify-evidence-v198.js` now contains **26** regression tests, but full native Node run / actual Actions result was not observed. Do not mark CI green.
- Container git clone/ls-remote failed because external github.com DNS blocked; no local checkout. The new v220/v221/v222 JS test bodies were fetched and executed in V8 Node assert/fs compatibility harness, 3/3 PASS after the latest feed refresh for v220-v221. This is not a real Actions job.

## v220: official SGX multi-currency counter examples
- New `docs/data/sgx-official-multicurrency-subset-v220.json`, commit `6413aea9fe3adee82a50bdc4ec83b544496bcaeb`.
- Official source `https://www.sgx.com/securities/trading` explicitly lists same-instrument currency counter pairs:
  1. AEM HOLDINGS LTD, `AWX` SGD primary and `XWA` USD secondary — classified potential equity.
  2. UOB APAC Green REIT ETF `GRN` SGD and `GRE` USD — ETF, not ordinary stock issuer.
  3. NikkoAM-STC China EV ETF `EVS` SGD and `EVD` USD — ETF, not ordinary stock issuer.
- These are **3 official instrument groups / 6 traded counters**, NOT six separate verified corporate issuers and NOT official exchange full master. Avoid conflating currency counters with underlying issuer entities or listing board.
- Among these 6 codes only `AWX` appeared in existing incomplete third-party candidate list (182); 5 codes were missing. This is not evidence of 5 additional corporations, just a multi-currency instrument coverage gap.
- New `docs/test_multicurrency_subset_v220.js`, commit `0cfd68d5caed0dd1f6115803bf76139acee6fa45`, V8 compatibility test PASS.

## v221 browser-visible SGX multi-currency research
- Added `docs/official-multicurrency-v221.js` (`a707c2ed71636f2f0e7d5bf43c0d7d18c8c0f17a`) and a table in `docs/index.html` (`9f423a69996628f32a536b4a2b645a19d9f50842`) showing primary/secondary code and currency, stock vs ETF category, and whether each code occurs in 182 third-party candidates.
- Added `docs/test_official_multicurrency_v221.js` (`6bbae41aeddd636ba34fb8e0461c4d45c2b67c13`), V8 compatibility PASS against latest refreshed `latest.json`.
- Unified runner and main workflow trigger extended for v220/v221 `ceeea36e1825a5a92147f61640f6914d54586eaa`, `3352782389aa6cb02b8ec614dc633ebe1f9d2867`.

## v222: data reuse / licence sourcing barrier made explicit
- Browsed `https://stocks.com.sg/developers`: StocksSG documents a **free no-API-key tier 10 requests/min** and `GET /api/v1/companies` endpoint. But `https://stocks.com.sg/terms` states aggregated data may not be scraped, reproduced, or redistributed without permission. **Free API access does not authorize public replication of company directories or quotes.** Did not scrape/download the endpoint or copy third-party full list.
- Official SGX source `https://www.sgx.com/securities/trading` has examples and securities viewer, but use rights for downstream market-data redistribution and completeness of a dated full official master remain unverified. SGX data vendors publicly described at `https://www.sgx.com/data-connectivity/our-data-vendors`. Do not invent a free market-data redisplay licence.
- Created `docs/data/sgx-source-rights-review-v222.json` (commits `15eb42332d34b94ebcb217af8ad67ae30560c2b`, fix `64ba504b503335ba54c590ca6d3f65eb0594e644`) with separate official static examples, research-only StocksSG API, and unconnected licensed SGX feeds. All lack verified public-quote redistribution rights.
- Added regression `docs/test_sgx_source_rights_v222.js` (`6cbe49f39ed40d7941a2364efa17dff92ed6a437`). Initial V8 run found a manifest missing explicit `public_quote_redistribution_authorized:false` for StocksSG; corrected. V8 test PASS. Unified suite now 26 cases `1fad15bccd4fc48163f346f00d2adb1d7cf5f77e`; Actions trigger `e2b823ab8ce041738de67fcbadce06ef1df5d266`.

## Blockers / next practical steps (v223+)
1. Obtain ACTUAL GitHub Actions run IDs/results for the evidence suite (now emits per-test artifact `sgx-source-integrity-v218-results`) and v210 issuer-PDF download artifact; fix failing jobs. The GitHub connector has actions run-by-ID tools but no push-run listing, so cannot know result just by code commits. Do not fake CI success.
2. Recover official UOB Nov13 SGXNet filing and OCBC Nov12 `Anno_12Nov2026.pdf` attachment; no secondary-source share promotion. Original PDF byte SHA for H02/V03 remains unverified despite original SGX pages visually inspected in v212/213.
3. Pursue explicit permission/redistribution terms for a comprehensive official dated SGX securities/issuer master and timestamped quote. The source-integrity v199 manual CSV staging plus v202 instrument taxonomy and v204 ISIN checksum already exist, do not redo. StocksSG may provide a company-list research lead but terms currently prohibit unauthorized reproduction/redistribution.
4. Independent genuine financial numeric verification for G13/S63, reported-vs-adjusted definitions and parent-equity reconciliation. v212 H02 and v213 V03 original issuer statements have separate research sidecars and are not promoted into certified seven-company feed.
5. Confirm Pages enabled and published only after a successful workflow and working URL; ranked eligible remains 0.

## Next conversation handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv222から継続。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v222.md`を読む。v219までに23テスト、PDF取得安全化、JSON CI成果artifact設定。v220ではSGX公式の複数通貨カウンター例3商品6取引コード（AWX/XWA株、GRN/GRE ETF、EVS/EVD ETF）を収集して別台帳へ、第三者182候補にあったのはAWXのみ。これを企業6社と数えてはいけない。v221で対照表をブラウザ画面に追加しテストPASS。v222はStocksSG無料API10回/分の存在を発見したが、Termsで無許可の複製再配布は禁止と確認し、公開データ取得せず利用権限の未確認を資料化・回帰テストPASS。現在26個の統合回帰テストを登録、追加3テストはV8互換実行PASSだが実GitHub Actions本体の成功は不明。登録財務7社、第三者候補182、公式限定11証券、ランキング適格0。原本PDF SHA、UOB/OCBC最新原本、SGX正式全銘柄と価格権限、独立財務数値監査、GitHub Pages公開が未完。既存工程を繰り返さず、ソース・権限・実データの取得を優先してmainへコミットする。
