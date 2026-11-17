# v554 Android破損基準日による監視停止の修正

- 起点: main aedb8f2add37ba505c6307ca5a05023c5266cf76。最新のJPX回転月報解析コミットを確認。docs/data/latest.jsonはSGX財務登録7件、ランキング適格0件。
- 直前CI: main aedb8f2a の Android run 44013882101 と JPX run 44013882087 は成功。
- 不具合: WatchTransitions は破損した保存日付からの復旧を認めていたが、JQuants.scan は日付を文字列比較していたため、例えば latest_date=invalid のとき全候補日が古いと判定され、通信前に終了し続けた。
- 修正: WatchTransitions.shouldRequestSession で LocalDate.parse により比較し、破損日付の場合は取得を許可。newEntrants は既存どおり破損履歴からの通知を抑制し、正常取得で基準を再構築する。正常な同日・過去日の再取得は引き続き抑制。
- コミット: 4f37f8f553bdf33eac6f5158764b38ccd6f20ff3、fa2b6834c70918df4992967043e916cdecb3096b、fae314ad26513043938c5d6bb9516b6c8dac8fc9。
- 回帰: 破損日付・存在しない日付・同日・未来日・過去日・初回の各条件を確認するテストを追加。Android CI run 44014332713 はチェック時 queued。成功は未確認。
- Web版は変更なし。Web/ZIP回帰の追加実行は不要。APKの公開Artifacts/Release配布は行わない。
- 未確認: 新CI完了、JPX東証日報の直近終値と許諾、実株価2回連続更新、財務・株数照合、Android実機の無音通知、私的APK受け渡し。新規の正式ランキング適格判定なし。
- 次回: 最新mainとActionsの成否を確認し、失敗なら修正。Android実データ取得→株数・財務照合→通知を優先し、JPX公式日報と権利落資料の新規公開も追跡。
