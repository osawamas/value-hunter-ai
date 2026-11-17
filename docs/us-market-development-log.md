# VALUE HUNTER AI 米国株の開発ログ

無料・APIキーなしで、NYSE・Nasdaq上場の普通株を広く扱う個人用Androidアプリの開発記録。ダウ平均は構成銘柄の確認対象として扱う。各回の結果を新しい順に追記する。

## 2026-11-17 22:19 JST — Dolt終値の入力検証を強化

- 開始時main: [3ac9ba5](https://github.com/osawamas/value-hunter-ai/commit/3ac9ba518ca16cdbf6a4d8bbec1302dd69511efe)。直近のAndroid private preview Actions [44089075788](https://github.com/osawamas/value-hunter-ai/actions/runs/44089075788) は成功。並行する日本株の更新は触れていない。
- [us_public_files_probe.py](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_public_files_probe.py) のDolt CSV読取りでNaN・無限大・ゼロ・負値・壊れた日付を拒否し、NULL/空欄は「終値なし」として保持するよう変更。無効な値を網羅率の正規終値として誤集計しないための前処理。
- [テスト追加](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/test_us_public_files_probe.py)。コミット [4d91188](https://github.com/osawamas/value-hunter-ai/commit/4d911882956340b711c19b13b73b8c5ec4e8d412)、[b169a42](https://github.com/osawamas/value-hunter-ai/commit/b169a4275aca28f231b03f85f341b62adf16d90f)、[b8ad575](https://github.com/osawamas/value-hunter-ai/commit/b8ad575b23b0228a9fb3fa2bc5bd7d4ea43a7d13)。最初のテスト追加は改行エスケープに誤りがあり修正した。最終コミットの[Actions](https://github.com/osawamas/value-hunter-ai/actions/runs/44091732869)は記録時点で待機中、成功未確認。
- 対象取引日: 2026-11-16。前回実測のNYSE 1,875/1,896、Nasdaq 3,102/3,190を引き継ぐ。今回は新規の実データ同期・件数再測定なし。DoltHub [公開DB](https://www.dolthub.com/repositories/post-no-preference/stocks)のHTTP 429、全件同期、ライセンスと終値基準は未解決。
- 次回: Actionsの結果を確認し、失敗時は修正。Doltの同期失敗時に既存ローカルDBを保持する安全な再試行・キャッシュ手順を追加する。株数や正式PER/PBRへの採用は引き続き保留。

## 2026-11-17 22:01 JST — 毎時開発の開始点

- 開始時点のコードは [221273b](https://github.com/osawamas/value-hunter-ai/commit/221273b71dd3198a25c084a08e30c89d7bf97933)。
- 11月16日取引分の公開DBとの照合では、普通株候補に対してNYSE本市場は1,875 / 1,896、Nasdaqは3,102 / 3,190の正の終値を確認した。基準は11月17日観測のNasdaq Trader銘柄一覧。
- ローカルDoltの読取りはテストデータで確認済み。公開DBの浅いクローンはHTTP 429で止まり、全件同期と日次更新は未確認。Apple・NVIDIAの分割前後で未調整の水準を確認したが、市場全体の基準は未検証。
- SECの原本処理はBerkshire HathawayのA株・B株とSouthern Companyの親会社分を確認済み。取引日時点の株数、未調整終値、正式なPER・PBR、Android上の一連の動作は未検証または未実装。
- 次の作業は、Doltの公開資料と利用条件を確認し、HTTP 429の再試行制御と同期済みデータの再利用を優先する。同じ取引日の上場一覧・終値・分割情報の照合へ進む。
