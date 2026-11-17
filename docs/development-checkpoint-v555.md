# v555 JPX日報の取引日整合性を検証

- 起点: main 6ce1c3cfac40fa8c7b0e579d2e40364cdbbb74c0。2026-11-17 08:09 UTCのAndroid Actions run 44044079588 は success。docs/data/latest.json はSGX登録7件・ランキング適格0件。
- AndroidのJpxDailyCheck.checkRecentに、要求した日付とReport.dateが一致することを必須とする検査を追加。古いキャッシュ・日付の取り違えを正常な直近終値として扱わない。比較日は必ず最新日より前であることも検査。
- 実装コミット: e02b10ee9385ce1d655a08b3020d2efee87cdc71
- 回帰テストコミット: c49842922d91248eeb11b812c3bce69f15d68df7。日付不一致拒否、正常な2営業日、未公表日のスキップを検査。
- 変更は android-private/ のみ。Web面とデータファイルに変更なし。APKを公開配布していない。
- 修正後のCI結果は未確認。CIが失敗すれば原因を修正すること。実機通知、JPX現物の自動監視、日次終値の許諾、財務・株数照合、実データ2回更新は未完了。
- 次回: 新しいmainとAndroid Actionsを確認。JPXの直近終値取得を候補判定と無音通知につなぐ実装を優先。J-Quants遅延データは直近として扱わない。
