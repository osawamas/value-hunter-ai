# VALUE HUNTER AI — v201 checkpoint (2026-11-14 JST)

## Resume prerequisites
- Read main, Actions, `docs/data/latest.json`, `docs/data/sgx-bank-corporate-actions-v190.json`, `docs/data/sgx-official-batch-seed-v196.json`, `docs/data/sgx-independent-figure-research-v197.json`, `docs/data/uob-share-display-research-v201.json`, and this checkpoint.
- See `docs/development-checkpoint-v200.md` for work v195-v200. No completed steps should be repeated.
- Latest observed `docs/data/latest.json` `2026-11-14T12:12:03.616030+00:00`: financial registered 7, ranking eligible 0. Third-party incomplete candidate universe 182. v196 official lot-size subset exactly 11 securities, not full SGX master.

## v201 new issuer share-definition discrepancy evidence
- UOB's investor relations microsite `https://uob.listedcompany.com/stock_fundamentals.html` indexed a displayed **Issued & Paid-up Shares: 1,646,915,591**, while its quote panel said updated 2026-11-13 17:14 SGT. This is NOT evidence of the effective date/time of the displayed share count. The microsite detail subsequently returned 403 when opened via web, so content could not be independently inspected beyond indexed search.
- A syndicated SGXNet announcement of 2026-11-13 17:41 `SG261113OTHRHOAF` displays **issued shares excluding treasury AFTER purchase: 1,646,677,591** and 14,548,000 treasury, via `https://b.siasset.com/news/news.html?nid=515671689&source=regional_sgxnet`. Exact SGX original filing remains unacquired, no SHA. The arithmetic displayed difference 238,000 shares is **NOT reconcilable as an issuer transaction**, because the definitions and effective timestamps differ. Do not treat it as 238,000 purchased or cancelled shares, or infer up-to-date outstanding shares.
- Added research-only, unverified `docs/data/uob-share-display-research-v201.json` commit `952b6fda1e30bfcfbeebe18fbb366efac0ea4997`, then clarified quote license as 'permission not confirmed' in commit `3f75d6a9e271c74e8bb2207db37c16dda515e04f`.
- `docs/test_uob_share_display_scope_v201.js` commit `1843c39877782dc27de1220dc36602cd06ae2979` guards both figures, no equivalent basis, unavailable original, no share timestamp, no redistribution rights, and no ranking.
- Unified `scripts/verify-evidence-v198.js` now runs eight tests, commit `5ce4f5cc27589f47135c422b971106a5990f3b9a`; workflow path trigger updated `5cb9f905a24462a712995da16854f7c7a9f2f377`.
- All **eight JS test bodies** (v190/192/193/195/196/197/199/201) executed successfully with GitHub-fetched source in a dedicated V8 compatibility harness mocking Node fs/assert/Buffer/crypto; **8 / 8 PASS**. This does **NOT** mean GitHub Actions or full child_process Node CLI was actually run. GitHub push workflow results remain not observable with existing connector.

## What is not solved
- No UOB 2026-11-13 original SGX buyback filed form and no OCBC 2026-11-12 treasury-use original PDF. No official same-date adjusted shares or source hashes.
- No SGX-approved timestamped price feed and downstream redistribution rights. Investor microsite quote values are not licensed and share timing is unknown, so cannot derive P/E, P/B, market cap or ranking.
- No official exhaustive dated SGX securities/issuer master; official v196 11 securities only; manually supplied v199/v200 CSV staging remains untrusted and local, real SGX export schema and permission unverified.
- G13/S63 independent numerical audit unavailable, and published operating-income definitions differ from some third-party aggregates. v197 summary stays research only.
- GitHub Pages still not confirmed published; owner needs enabling if disabled. Actual workflow status only from jobs, not from combined commit statuses.

## Next priorities
1. Obtain GitHub Actions push workflow listing/job logs for eight-test unified suite, fix any actual CI issues; do not assert green without job.
2. Obtain original UOB Nov13 and OCBC Nov12 SGX announcement attachments / cryptographic hashes, with same-date ex-treasury shares.
3. Acquire officially authenticated dated SGX full security master and usage rights, run stage-sgx-csv-v199.js with actual authorized CSV and verify source bytes using v200.
4. Independent fiscal G13/S63 parent equity/operating profits using like-for-like definitions; prioritize actual issuer coverage and ranking data gaps.
5. Licensed timed SGX quote + contemporaneous adjusted shares for valuations.
6. Keep scheduled automated development task separate; this chat's synchronous work does not itself run after the response.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv201から続行。main、Actions、`docs/data/latest.json`、`docs/data/sgx-bank-corporate-actions-v190.json`、`docs/data/sgx-independent-figure-research-v197.json`、`docs/data/uob-share-display-research-v201.json`、`docs/development-checkpoint-v201.md`を読む。v195銀行財務FY/3Q、v196公式SGX売買単位変更11銘柄の限定台帳、v197 G13/S63外部会計数値研究（営業利益定義相違は比較不可）、v198一括テスト、v199正規SGX CSVローカル仮取り込み、v200 UTF8元ファイルSHA確認までGitHub保存済。v201ではUOB投資家向け画面の発行済払込株数1,646,915,591と、SGXNet転載の11/13自己株式控除後1,646,677,591の違いを定義・時刻不一致として隔離。差238,000株は買戻し数と断定禁止、公式原本未取得、株価利用許可も未取得。8種類のテストはV8互換実行で8/8 PASS（GitHub Actions本体未確認）。登録7社、第三者候補182社、公式限定11証券、投資ランキング0。全SGXマスター、原本PDF、許諾付き取引時刻株価、独立財務検証、Pages公開が残る。スキップ済みを再開してGitHubへ保存しながら続行。
