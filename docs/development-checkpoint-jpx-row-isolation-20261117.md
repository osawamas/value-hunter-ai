# JPX終値行の局所破損を安全に隔離（2026-11-17 14時台 JST）

- 起点: main 1baa9ef403d4bccca240b838f6c83b6be16b72ac。v554以降のJPX日報・月報取得とJava終値照合の4コミットを確認。
- docs/data/latest.json: SGX財務登録7件、正式ランキング適格0件（変更なし）。
- 実装: JpxCloseTableの同一銘柄行で終値欄が二重に抽出された場合、従来はIllegalArgumentExceptionで日報全体の照合が停止していた。対象銘柄だけをambiguousに入れ、以前の同銘柄価格も削除し、他銘柄の処理を継続するよう変更。
- 回帰: JpxCloseTableCheckに、同一行の二重終値・正常な別銘柄の維持・後続ページでも競合銘柄が復活しないことを検査するケースを追加。
- 実装コミット: 1c0f8f153d47614adde131936a8fc3f13b2c9d17、0a6b2e116e45a43596a37d1a5e6bffa09d7452c9。
- CI: pushによりjpx-daily-probe.ymlの対象パスに該当。GitHub combined statusには確認時点でチェックなし。成功とみなさず次回ログを確認する。
- 原本経路: JPX公式東証日報 https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/ 。今回新たな実データの取得・許諾検証は実施していない。
- 未確認: CI成功、Android APK最新ビルド、JPX日報の端末内自動取得と利用条件、財務・株数の同日照合、実データ2回連続更新、実機無音通知、APK私的配布。
- 次回: mainとActionsを確認し、失敗を修正。JPX Java抽出結果をAndroid端末内の取得・候補判定につなぐ工程を最優先。Web版は未変更のためWeb/ZIP回帰は追加不要。
