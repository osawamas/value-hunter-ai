# Android JPX日報 PDF応答検証（2026-11-17）

- 起点 main: 4ac859871ee57f6f1535ac9310798eba5f64bcae。直前の変更はAndroid 15 PDFによるJPX日報の手動プレビュー（1301・7203）。監視判定への接続は未実装。
- 既存CI: Android run 44014332713 の verify ジョブは completed/success（APK生成確認を含む）。これは今回の変更のCI結果ではない。
- 変更: android-private/app/src/main/java/jp/valuehunter/privatewatch/JpxDailyCheck.java。HTTP 200でもHTMLエラーページ等を返す場合があるため、取得ファイルの先頭5バイトが %PDF- であることを確認し、不一致ならPDFレンダラへ渡さず停止する。通信先・許諾・監視履歴・通知判定は変更なし。
- 実装コミット: 11ad3c6b0dd65033294b4db698c17ab039ca5688。
- 今回のCIと実機検証: 未確認。手動プレビューはAndroid 15以降限定で、日報の株価を候補判定や無音通知へ流していない。
- 次回: 最新mainの競合を再確認し、Android CIでビルドとJPX PDF試験を実行・照合。PDF形式のエラー応答に対する回帰テストを追加。原本の本人用定期取得条件を確認後、広範囲の東証銘柄・株数財務照合・監視候補判定へ安全に接続する。実機での通知確認は別途必要。
- Web版は変更なし。公開Artifacts/ReleaseへのAPK配布なし。
