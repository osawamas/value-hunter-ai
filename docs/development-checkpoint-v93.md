# VALUE HUNTER AI — v93 開発チェックポイント（2026-11-14 JST）

次回は GitHub `osawamas/value-hunter-ai` main、最新コミット、GitHub Actions、`docs/data/latest.json` を読み、このファイルを元に再開。完了済みの変更を繰り返さない。

## 直前 v91 までの状況
- 公式SGX原本3件: UOB 2026-11-10、11、12の自己株式控除後株式数 1,646,779,591 / 1,646,745,591 / 1,646,711,591。毎日34,000株減、自己株式残高14,548,000で固定。SGX原本URLとSHA256を `bank_primary_three_day_chain` へ保存。v91統合GitHub Actions #43525031088 成功。
- UOB 2026-11-13 SGXNet転載 SG261113OTHRHOAF に控除後1,646,677,591株、自己株式14,548,000、34,000株買戻し・34,000株取消しと記載。ただし本日時点で公式SGX原本のURLが特定できず、`bank_share_discovery` に未検証として記載。
- OCBC 2026-11-12 SGXNet転載 SG261112OTHRXH64 は treasury shares 利用のPDF `Anno_12Nov2026.pdf` 添付と分かるが、SGX原本の開示URLも添付PDF原本も未取得。数値はNULL。買戻しではなく自己株式利用なのでUOBのbuyback parserを安易に流用しない。

## v92 実装済み
- `SGX_PDF_connection_probe/u11_pending_buyback_v92.py` とユニットテスト `test_u11_pending_buyback_v92.py`。
- 11/12の公式SGX原本＋3日連続原本履歴の同一SHA256を確認し、11/13の別の二次転載ソースの記載数字との差34,000株が買戻し／取消し34,000株の主張と一致するかだけ算術照合する。
- `bank_pending_buyback_consistency` に `SECONDARY_NOV13_ARITHMETICALLY_CONSISTENT_PRIMARY_NOT_VERIFIED`、11/12の正式株数、11/13の未検証転載株数、転載の買戻し／取消し34,000株、差分を記録。13日原本URL・SHA256はnull。現在株式数・株価・時価総額・PER・PBR・ランキングは変更禁止。
- 日本語UIでは『算術は一致、SGX原本は未取得』と区別。ユニットCI #43528352368 成功。

## v93 実装済み
- `SGX_PDF_connection_probe/bank_market_readiness_v93.py` と `test_bank_market_readiness_v93.py`。D05、O39、U11の銀行専用財務解析済み状態を前提に、投資評価に必要な未検証項目を銀行別に表示。
- D05: 最新自己株式控除後株式数、タイムスタンプ・SGD価格、財務数値の第三者独立照合。
- O39: 2026-11-12自己株式利用通知のSGX原本添付PDF、最新株式数、時間付き価格、独立財務照合。
- U11: 2026-11-13買戻し通知のSGX原本、最新株式数、時間付き価格、独立財務照合。
- `bank_market_readiness.status=NOT_READY_PRIMARY_SHARES_AND_TIMED_QUOTES_MISSING`、全銀行 market valuation/ranking=false。日本語UIで未解消項目を説明。ユニットCI #43528596565 成功。
- `.github/workflows/value-hunter-v29.yml` にv92/v93の検証・発行を連結。GitHub Actionsの paths に以前混入していたテスト名連結の不正行を修正、v90-v93テストを本体へ追加。

## 検証状況
- 作業中のv93統合は #43528718261 が進行中、最終UI変更による #43528750367 がpending。次回最初に実行結果と `docs/data/latest.json` 反映を確認し、未実行・失敗なら対応。成功を確認するまではv93公開を断定しない。
- 本体データ最終確認は7銘柄、算術不整合0、ランキング対象0。銀行3社のprice_sgd、shares_outstanding、market_cap_sgd、PER/PBRは全てNULLのままが正しい。

## 次の開発：v94以降
1. UOB 2026-11-13 SG261113OTHRHOAF の本物の `https://links.sgx.com/1.0.0/corporate-announcements/...` を発見し、v84の原本解析器で発行体・購入日・Section Dの株数を実取得。転載値を原本検証済みに勝手に昇格しない。
2. OCBC 2026-11-12 SG261112OTHRXH64 のSGX原本と添付 `Anno_12Nov2026.pdf` を検索取得。自己株式利用／移転通知の構造がUOBの買戻し通知と違うため、原本から日付・前後残高・株式数を別パーサーで検証する。
3. DBS/OCBC/UOBの時刻付きSGX株価（取引日、遅延か終値か、SGD通貨、ソースURL）を独立に収集・照合。UOBの買戻し通知にある最高/最低買付株価を当日の市場終値や現在株価に流用禁止。
4. v93統合Actionsを確認し、問題があればfail-closedのまま修正。SGX全銘柄への拡張を継続。

## 次スレッド用コピペ
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）のv93の続きから開発。まずmain・最新Actions・docs/data/latest.json・docs/development-checkpoint-v93.mdを確認。v91までにUOBの11/10〜12 SGX原本買戻し株数を3日分直接照合し公開。v92で11/13のSGXNet転載株数1,646,677,591株と11/12公式原本1,646,711,591株の差34,000株が転載の34,000株買戻し・取消しと算術一致することを確認。ただし11/13のSGX原本未取得のため `bank_pending_buyback_consistency` は未検証として扱い、時価総額に採用しない。v93でDBS/OCBC/UOBの不足する原本株式数・株価時刻・独立検証を表示するbank_market_readinessを実装。v92 CI #43528352368、v93 CI #43528596565 は成功。v93の統合実行 #43528718261 と #43528750367 の結果を最初に確認すること。次はUOB 11/13 SG261113OTHRHOAF原本とOCBC 11/12 SG261112OTHRXH64の原本添付PDF探索、そして時間付きSGD株価ソースの検証。7社・不整合0・投資ランキング0、銀行市場指標はnullを維持。GitHubへ実装・テスト・原本照合し、最後に次スレッド用引き継ぎ文を付ける。
