# 2026-11-17 Android JPX PDF幾何データの防御

- 再開時main: 0739d4734277947648f097ff66af2b0d6b41549b（JPX購入額・参考評価の検証）。
- docs/data/latest.json: SGX登録7、ランキング適格0。Web面の変更なし。
- Android `JpxCloseTable.acceptPage` がPDF抽出語のNaN座標、逆転した矩形、null要素を受けると、TreeMapの行索引や列抽出で不正動作する可能性を修正。有限かつ正常な矩形だけを索引・解析する。異常な1語で他銘柄を止めない。
- 追加テスト: `JpxCloseTableGeometryTest`（破損座標の隔離、ページ幅異常）。本変更のコミット: 17e56c2b5a3e3665e279d26b2d3ff53864231fae / 3b722e4189e5c67de39bb63c705b9d1acbda2873。
- CI実行成功・APKビルドは今回未確認。端末実機の無音通知、JPX終値の監視系統への結合、実株価2回更新、利用許諾の確定は未完了。公開APK配布なし。
- 次回: GitHub Actionsで上記SHAのAndroid単体テストとassembleDebugを確認。失敗時は修正。次にJPX終値と日付整合した財務・株数を端末内の候補判定に接続する。データ欠落で保留を解除しない。
