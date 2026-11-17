# v553 Android監視履歴の逆行防止

- 起点: v552 / de9bfb239cea93ba7cd33bdd9c4eced5dcccaa7d。最新main、docs/data/latest.json、AndroidワークフローとActionsを確認。
- 問題: 新規候補通知は過去日を抑制していたが、ScanWorkerはAPIから古い日付の結果が返ると保存済みの最新日と候補集合を上書きし得た。後の正常取得で重複・誤通知につながる。
- 修正: WatchTransitions.shouldStoreSnapshotで同日・過去日を拒否。ScanWorkerは候補履歴を保存する前に判定し、最新の基準日・候補集合を維持。破損した基準日は従来どおり通知せず再構築できる。
- コミット: 27ac9893583850f45bd3334dcf6e3e59bbe0802b、ddeb4ac8e66b626ed7435c11f8dcceae63a3ceb6、7b80625e67ce20d1bed0e0a2976210106040387d。新たな単体テスト2件を追加。
- CI: v552 JPX回帰は成功（run 43999310830）。今回Android Actions run 44006611433は確認時点でqueued。成功は未確認。Web版未変更のためWeb/ZIP再試験不要。
- latest.json: SGX財務登録7件、ランキング適格0件。公開ランキングは初期完成条件外。
- 残課題: 最新Android CI結果、JPX日報の直近終値利用条件と現物接続、株数・財務整合、2取引日連続更新、実機の無音通知、APKの非公開受け渡し。2026年1月と2025年9月のJPX月報解析も未完。
- 次回: 最新mainとActionsから再開。失敗時は修正。本人用Androidの現物接続→判定→通知を最優先し、無許可取得や公開APK配布を行わない。
