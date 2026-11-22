# VALUE HUNTER AI 米国株の開発ログ

- 2026-11-22 13:18 JST | PR #107 のUsDailyWorkerで通知待ちを新しい判定・保存より先にcommit削除していたため、削除直後の中断で待機通知が消える危険を確認。早期削除を廃止し、従来の最終 `MarketUpdate.US_FINANCE.completed(update).commit()` でベースライン・通知待ち・送信集合をまとめて更新する修正 c8c42ade407c0c1fb244fb3e80d716dd161d69a7 をPRブランチへ保存。既存の同日SEC訂正時の文面再生成は維持。実際の保存失敗注入テスト・変更後CIは未確認、main未統合。新規実データ取得0・正式判定増0・参考予算確認増0・保留変動未測定。次に実装: SharedPreferencesのcommit失敗を注入し、古い通知待ちが残ることと再試行で新SEC画面から正しい通知1件・重複0件になることをWorker入口で検証。理由: 通知漏れの実害を防ぐ。完了条件: 保存失敗/再起動/同日訂正の回帰成功、関連CI成功、最新mainとの競合なしで統合。実機/APKなし。 [PR #107](https://github.com/osawamas/value-hunter-ai/pull/107)

- 2026-11-22 09:15 JST | main 6a6bab9772a7418b3746494c08e1acee5284621e とPR #107の通知処理を照合。前回の次工程として、実際のreference_screen JSON保存形式をread()で再構築し、同じ終値SHAのままSEC訂正でAAA参考候補が消えBBB優先候補へ変化するケース、配信済みBBBの重複除外、Nasdaq→NYSE市場変更の保留を検査する回帰テストを追加（34166fac786f722094b79c923b0c1ff920b269cf）。本番形式のJSON変換を通す単体テストであり、SharedPreferences→Worker→通知送信までの統合試験ではない。今回の新SHAのCI実行結果は未取得、ローカルJVM実行なし。PRはmainに対してahead 8 / behind 2で未統合。新規市場原本取得0、正式判定増0、単日参考予算確認増0、保留変動未測定、実配信未検証。次に実装: SharedPreferencesに通知待ちを保存してからSEC同日訂正→Worker再起動→許可後の無音通知を1回だけ発行する統合回帰。理由: 旧文面の誤送信と通知漏れを本番入口で抑止するため。完了条件: 旧文面0、正しい新通知1、重複0、失敗後再試行と設定変更を含む関連JVM/Android CI成功、最新mainとの差分解消後に統合。APK・実機・生株価公開なし。 [PR #107](https://github.com/osawamas/value-hunter-ai/pull/107)

- 2026-11-22 08:15 JST | PR #107 継続。前回のclose SHAだけでは、同日終値が不変でSEC財務判定だけ訂正された場合、許可待ちの旧文面を先に送信する問題が残るとコード経路から判明。実装 d17d32a: 保留文面は送信前に毎回破棄し、保存済み前取引日baselineと現行SEC ledgerから再生成。PRIVATE_SENTの配信済み集合は維持し、旧pendingの送信を防止。回帰 aeaebd0: 同日SEC訂正でAAA参考候補→対象外、BBB対象外→優先候補、配信済みBBBの重複防止を検査するJVMケース追加。前回head 8dcd616のAndroid unit CI #44955469056 は成功、エミュレーター #44955469024 はAPI 28/35成功・API34失敗（初回通信案内が見えないJPX_PDF_GEOMETRY_FAILED、US固有の失敗ではない）。今回変更後CIと本番SharedPreferences統合再生は未確認。新規市場データ0、正式判定増0、参考予算増0、保留変動未測定。次に実装: 本番SharedPreferencesで許可待ち→SEC同日訂正→再起動→1回送信を通す統合テストと、最新headのUS/Android CI確認。理由: 旧文面の誤通知防止と送信済み扱いによる漏れ防止。完了条件: 修正後の通知本文のみ1回、旧本文0、同日再試行重複0、関連CI成功後にmain統合。実機/APK配布なし。 [PR #107](https://github.com/osawamas/value-hunter-ai/pull/107)

- 2026-11-22 07:15 JST | main 02d11d7f を基準に、US財務通知の同日終値訂正時の誤通知経路をコード上で特定。通知許可待ちのPRIVATE_PENDINGが取引日と設定世代だけで再送可能で、close_sha256が変わっても旧文面を先に送信する危険があった。US専用のpending close hashを永続化し、同日再試行で一致しない旧pendingと銘柄集合を破棄、現行ledgerから再生成する変更を実装。旧バージョンから移行したhashなしpendingも安全側で破棄。送信成功時のhash消去と5条件のJVM回帰テストを追加（e92e873, 4814cb4, 9955a8f）。今回は実データ取得0・正式判定増0・参考予算増0、保留変化未測定、模擬テスト実行とAndroid CIは確認待ち。次に実装: 本番SharedPreferencesと実ledgerで通知許可待ち→同日終値訂正→再起動→送信1回の統合回帰を追加し、関連Android CI成功を確認。理由: stale pendingによる誤通知を防ぐため。完了条件: 旧pendingを送信せず新ledgerだけ通知、同日再試行で重複0、CI成功、最新mainと競合なしで統合。実機・APKなし。 [作業ブランチ](https://github.com/osawamas/value-hunter-ai/tree/us-pending-close-hash-20261122-0715)

- 2026-11-22 06:15 JST | PR #105 の専用US監査CI #44945590797 はsuccess、audit job内の監査実行ステップもsuccess。最新mainとの差分は監査Python4件・専用workflow・USログの3ファイルだけで、ahead 3 / behind 0、Android本体変更なし。PR #105 をsquash統合 SHA 6352fec8445d52d139e41ba99f94c950c7913e86。Android CIはこのPRで起動・成功を確認できず、実機配信も未検証。新規実データ取得0、正式判定増0、参考予算確認増0、保留変動未測定。次に実装: SEC入力→市場/CIK/銘柄付き保存→判定→無音通知の本番保存形式を用いた再生テストを追加し、同日訂正・再試行・設定変更・再起動で誤通知/通知漏れ/重複を再現して修正する。理由: 試用前の実害を直接減らすため。完了条件: 再現ケースが修正後に通り、既存通知の回帰なし、関連US/Android CI成功、main統合。APK/実機/株価原本公開なし。 [PR #105](https://github.com/osawamas/value-hunter-ai/pull/105)

- 2026-11-22 05:18 JST | main 3912eef4（#103/#104のUS通知修正を含む）を確認。旧PR #98はmainより6コミット遅れ・5コミット先行でmergeable=false。#98の専用US監査CI #44934239572 はsuccess、ただしAndroid CIは未確認。旧PRの監査Python4件と専用workflowのみを最新mainから新branch us-audit-main-20261122-0518へ移植（9e12a1b、7617a0d）。#103/#104の通知修正・JPX共通変更は巻き戻さない。今回新規実データ0、正式判定増0、参考予算確認増0、保留変化未測定、通知実配信未検証。次回は新PRのUS監査CI・関連Android CIとmain差分を確認し成功なら統合、旧#98/#95を重複整理。理由は上場・日付・市場の誤照合の再発防止。完了条件は監査4件成功、共通通知回帰なし、競合なしでmain統合。その後、SEC→保存→昇格→無音通知で同日訂正・再試行の回帰を追加する。実機/APKなし。公開株価原本なし。

- 2026-11-21 22:15 JST | 最新mainの直近コミット6cad0b9（JPXログ更新）と米国ログ・11/17監査2本・未統合PR一覧を接続済みGitHubで確認。#94は前回統合済み、今回の米国株新規コード編集0。過去監査の母数5,082・一次判定4,997・保留85、参考終値24件の同日上場ペア検証0・採用0・保留23・対象外1を再照合（新規実測ではない）。Git CLIはDNS失敗、GitHubコード検索も対象関数の特定に至らず、一部照会はタイムアウト。新規実データ取得0、正式判定増0、参考予算確認増0、保留変化未測定、通知候補未測定。次回は日付別上場一覧の訂正・欠損・市場移動をオフライン再生して参考予算キャッシュの失効と再計算をテスト追加する。理由は誤った参考値の残存を防ぐため。完了条件は3ケースで参考表示が再計算または保留に戻り、正式判定・通知候補不変、US/Android CI成功。実機・APKなし。GitHubには株価原本・認証情報を保存していない。

- 2026-11-21 21:15 JST | PR #94 のUS CI #44898013994・Android CI #44898013940 がともに成功（SGX CI #44898013989 は担当外で失敗）。main 9f4d132 の差分がAndroid共通の検証コードとJPXログだけであることを確認し、競合なしでPR #94をsquash統合 0f006826。両上場原本の対象日・市場重複・欠落を保存前に拒否し、空の中断保存先も上書きしない。既存PRの統合で新規コード編集0、今回新規実データ取得0・正式判定増0・参考予算増0、保留変動未測定・通知候補未測定・実配信未検証。次回は同じ日付の一覧を後から訂正した場合の再計算と古い参考予算表示の失効を、オフライン再生で検証・修正する。理由は誤った参考予算を残さず、正式判定・通知を変えないため。完了条件は訂正/欠損/市場移動のケースで参考予算が再計算または保留に戻り、正式判定・通知候補が不変、US/Android CI成功。APK・実機なし。 [PR #94](https://github.com/osawamas/value-hunter-ai/pull/94)

- 2026-11-21 20:15 JST | main 6d8bdf7を起点に日付別上場一覧保存の欠陥を修正（PR #94、32435ad・2886af6）。保存前に両原本の有無・対象日・重複を検証し、空の中断済み保存先をPOSIX renameで上書きしない。2件の回帰テスト追加、ローカル実行0・CI未確認。新規実データ取得0・正式判定増0・参考予算確認増0・保留変動未測定・通知候補未測定・実配信未検証。次回はPR #94のUS CIと既存スナップショット再生を確認、成功・競合なしなら統合。理由は誤った上場原本の永続化を防ぐため。完了条件は混在日付・欠損・中断保存先を拒否し正常保存と既存完全保存の再利用を維持すること。APK・実機なし。 [PR #94](https://github.com/osawamas/value-hunter-ai/pull/94)

- 2026-11-21 19:15 JST | PR #92 のUS CI #44889131634・Android CI #44889131641成功、SGX CI #44889131681失敗（担当外）を確認。main df9e9b5から競合なしでsquash統合 7509781。当日終値あり・前日なしの参考予算チェックに、両日同一証券の確認済み銘柄を重複追加しない修正と4ケース回帰を反映。今回の新規コード編集0、CI既存実行2件成功、新規実データ取得0・正式判定増0・参考予算増未測定・通知候補未測定・実配信未検証。次回は日付別上場一覧の訂正・欠損を模擬再生し、参考予算を安全に再計算する。理由は古い単日参考判定の残存防止。完了条件は訂正後の再計算で別日・別市場・既確認銘柄が混入せず、既存の正式判定・通知が不変であること。APK・実機なし。 [PR #92](https://github.com/osawamas/value-hunter-ai/pull/92)

- 2026-11-21 18:19 JST | main df9e9b5 を起点に、当日終値あり・前日終値なしの参考予算チェックが、両日同一市場・同一証券として検証済みの銘柄を再追加する問題を修正。全経路でpaired除外を共有し、PAIRED/CURRENT/OLD/GONEの4ケースを追加（282b205、fc32a9d、40d065b）。コード変更あり、ローカルテスト0件・CI確認待ち。実データ取得0・正式判定増0・通知候補未測定・配信未検証。次回はUS/Android CI成功を確認して競合なしなら統合。理由は参考予算と正式な二日照合の二重表示防止。完了条件は回帰成功と参考予算へのpaired再混入0。APK・実機なし。

- 2026-11-21 17:44 JST | 米国株の保留銘柄に当日上場・DoltHub参考終値・当日USD/JPYだけで100株10万円の内外を表示する経路を追加。別枠の表示とし、終値本体・割安判定・通知には反映しない。11/17の未判定85銘柄中、参考終値の記録がある24件を当日条件で再集計。上場の当日原本がなく、予算内0・予算外0、保留23・対象外1。残り61銘柄はこの24件の再検証には含めていない。取得可能資料の組み合わせを模したテストでは、前日資料とSEC財務なしで予算内・外各1件、当日為替がないと両方保留。

- 2026-11-21 16:58 JST | 11/17（米東部）の監査対象をJVM上で再検証するCLIを追加。比較日と当日の上場資料の照合にAndroidと同じ処理を使い、補完前後の終値・割安判定・通知候補の件数と保留理由を出す。保存済み監査24件では23保留・1除外。取引日別の上場原本が揃わず、補完・判定増・通知候補は0件。テスト資料では終値・判定・通知候補が各1件増え、株式クラスが変わった銘柄は保留、同じ通知候補の再生成0件。株価原本は非公開の入力として扱う。

- 2026-11-21 16:06 JST | 上場確認後の終値補完を日付指定で再試行し、追加入力した銘柄を終値スナップショットと一緒に保存。米国株画面で終値補完数と補完対象の割安判定完了数を分離した。旧テストに加え、一度の終値通信失敗→再取得→Android再起動→取得済み終値を使ったSEC照合→無音通知1回・再実行で重複なし、の検証を追加。実データの判定増は未確認。

- 2026-11-21 15:54 JST | Androidに米国上場一覧専用の定期処理を追加。米東部16:05〜20:45前の取引日に両市場の一覧を取引日別に保存し、未取得／再試行を表示する。終値・財務の処理から独立し、比較日と当日の上場資料が揃った場合だけ、保存済みの同日終値で保留中の銘柄を再照合する。既存の通信停止・Wi-Fi設定を適用。11/16・17想定のテストでは日付不一致を拒否し、再起動後に保留3件のうち1件を補完対象へ戻す。実データの11/17記録は別途調査し、第三者の一覧はファイル原本の時刻と比較日を確認できず採用0。

- 2026-11-21 15:24 JST | 11/17のDoltHub参考終値が得られた24件のコード・取引所・種類をSEC・上場一覧・発行体資料で照合し、[銘柄別監査](us-dated-listing-audit-20261117.json)に保存。比較日と当日の上場確認不足18、単独取引の根拠不足2、株式クラス別資料不足2、分割と株数の基準待ち1、クローズドエンド型ファンド除外1。補完終値・割安判定・追加通知候補の採用0。Androidは取引日と比較日の市場・名称・クラスが一致した銘柄だけ補完終値を再取得する。次回は17日当日または比較日の発行体・公式取引記録を探し、まず日付・市場・同一証券が検証できたものから価格・財務を再照合。

- 2026-11-21 15:09 JST | 11/17米東部取引分を11/16と比較。11/20時点の上場一覧・SEC登録と一致した7銘柄を対象に、INTCの終値とCSCOの財務を初回入力から意図的に外し、DoltHub 1回とSEC 2回（HTTP 200、4.77秒／4.33秒／5.15秒）で再取得。実データ再生で終値6→7、照合済み財務5→7、割安判定5→6、追加通知候補0。INTCは財務取得後も利益または自己資本がゼロ以下で判定保留のため、為替などの確認待ちから表示を分けた。別途、既存監査85件の同日参考値を確認してDoltHubに24件の終値があったが、同日上場・証券クラス・比較日まで照合できておらず、公式カバー増としては未計上。次回はこの24件の同日・同一銘柄照合を優先し、根拠が揃った分だけ判定増へ計上する。実通知・実機は未検証。

- 2026-11-21 14:12 JST | PR #82 の US CI #44865603398 と Android CI #44865603445 は成功、SGX dashboard CI #44865603443 は失敗（担当外）。#65 の旧Doltキャッシュ保護を維持し、NYSE/Nasdaqの日次比較で不正件数・欠損一覧を拒否する #82 を main へ squash 統合 f3ddbe6。旧 #70 は重複のため未統合で閉鎖。今回コード変更は既存PRの統合（新規編集0）、新規実データ取得0、正式判定再測定0、通知候補未測定、実配信未検証。次回は同一米東部取引日でPR #80の再試行前後の終値・SEC財務・正式判定数・リクエスト数・エラー・通知候補を再生比較し最大欠損を修正。完了条件は実測差分と回帰テスト成功、価格原本を公開せず保存すること。APK・実機なし。 [PR #82](https://github.com/osawamas/value-hunter-ai/pull/82)

- 2026-11-21 13:19 JST | main d4307bd と #65統合済み・#70競合を確認。#70の件数整合性・欠損一覧ガードを#65の旧Doltキャッシュ保護を残した新ブランチへ移植、5種類の不正件数と一覧欠損・回復銘柄の回帰を追加（実装 ba1a42d、テスト 080a72d、PR #82）。テスト実行0件・CI結果未確認、実データ取得0・正式判定再測定0・通知候補未測定・実配信未検証。次回は#82のUS/Android CIとmain競合を確認し、成功なら統合、#70を重複として整理。完了条件は不正件数を比較せず、正常回復を保持し、#65の429/timeout退避を壊さないこと。APK・実機なし。 [PR #82](https://github.com/osawamas/value-hunter-ai/pull/82)

- 2026-11-21 12:18 JST | PR #65 の US CI #44854655568 と Android CI #44854655458 の成功を確認し、古いDoltキャッシュ（429・timeout・OS error）で日別集計を上書きしない変更をmainへsquash統合 b4a7cb6。PR #70 は US CI #44835295873 成功だが、#65統合後にmerge競合で保留（未統合）。今回の追加実データ取得0、正式判定再測定0、通知候補未測定、実配信未検証。次回は #70 を最新mainへ移植して回帰CI成功後に統合する。完了条件は不正な件数・欠損一覧で回復銘柄を誤集計せず、#65の古いキャッシュ保護が維持されること。APK・実機テストなし。 [PR #65](https://github.com/osawamas/value-hunter-ai/pull/65) [PR #70](https://github.com/osawamas/value-hunter-ai/pull/70)


- 2026-11-21 11:12 JST | main fafd75a、PR #65（open/US CI失敗）・#70（open/US CI成功）・#80（統合済み）・#56と監査JSONを確認。#65のUS CI 44827031561 は115テスト中3エラー、原因は回帰fixtureの改行が文字列のままでNasdaq上場一覧時刻を読めないこと。fixtureの14箇所を実改行エスケープに修正（ac65b0b、PR #65）、変更後CI未確認、main未統合。新規終値取得0・財務再判定0・通知候補未測定・実配信未検証。次回は#65のCI成功を確認し、main競合を解消して保護処理を統合する（旧キャッシュで日別集計を上書きしないことが完了条件）。APK・実機なし。 [PR #65](https://github.com/osawamas/value-hunter-ai/pull/65)

- 2026-11-21 07:12 JST | main 4986981・未統合PR #56/#58/#60/#62等と米株監査を確認。Dolt同期が429・タイムアウト・OSエラーで旧キャッシュに退避した際、日別レポートを古い価格で上書きする経路を停止し、保留取引日を返す修正と3状態の回帰テストをPR #65に保存（実装3f4632a、テスト7102f4b）。ローカルGitHub DNS失敗のためテスト実行0・CI未確認、main未統合。新規取得0・追加一次判定0・保留81の追加原本照合0・通知候補未測定・実配信未検証。次回はPR #65のテスト実行と初回/差分同期時間実測、81銘柄の公式原本照合。APK・実機なし。 [PR #65](https://github.com/osawamas/value-hunter-ai/pull/65)

- 2026-11-21 03:52 JST | PR #61の一覧ハッシュ・銘柄コード・重複検証を統合。保留82銘柄をSECの現行市場一覧と照合し、同一市場で一意に紐づいた75銘柄の提出履歴を確認。ANTのNasdaq初日は11/19と取引所資料で確認し、11/16〜17の比較調査から除外。残り81銘柄は別の公開日次履歴を参照し、両日あり0、片日のみ41、両日なし24、その他16。追加判定0件。11/20一覧基準の既存参考集計4,997/5,082（98.33%）。JVM125件・関連Python200件に合格。実機・APK未実施。 [ANTのNasdaq原本](https://www.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-28) [PR #61](https://github.com/osawamas/value-hunter-ai/pull/61)

- 2026-11-20 23:02 JST | Nasdaq Traderの上場一覧を米東部の日付ごとに保存。両取引日の一覧が揃うと同一市場で両日上場していた銘柄の集合で比較する。過去11/16・17の正確な一覧は取得できず、既存の11/20一覧を使った参考集計4,997/5,082（98.33%）を記録。継続調査の82銘柄をChartExchangeで検証し、両日1、片日41、両日なし34、404が6。両日が見つかったLFACはNasdaq公開履歴とは両日不一致。Nasdaq公式終値は5日・1カ月版とも11/16欠損。補完0。通知直後に履歴保存前の中断を模擬し、同じ通知がまだ表示中の再投稿を防止。通知が消えたケースでは既配信と判別できない。JVM124件・関連Python196件成功。APK生成・実機検証なし。 [LFAC公開履歴](https://chartexchange.com/symbol/nasdaq-lfac/historical/)

- 2026-11-20 22:41 JST | 終値裏付け待ち84銘柄を別の公開履歴でも照合。両日の参考終値2、片日のみ46、両日なし28、404が8。両日の参考終値が見つかった2銘柄のうち、GUERは対象日にはOTCでNasdaqの取引開始は11/18、TXRは11/17にNYSEの取引を開始したため11/16のNYSE終値がない。SENEBはNasdaq公式の分割日が11/17と再確認。新規採用0、一次判定4,997/5,082（98.33%）。照合できなかったNasdaq公式終値を次回の定期更新で再確認できるよう修正。11/13・16・17のDoltHub実データと日別為替で再生。株価のみの経路で為替遅延時0件、照合後に予算入り26件・19件、取りこぼし・重複0件。JVM121件・関連Python196件成功。APK生成・実機検証なし。 [公開履歴の出典](https://stockanalysis.com/data-sources/) [GUERのSEC開示](https://www.sec.gov/Archives/edgar/data/1832487/000143774926037477/ex_1047287.htm) [TXRのSEC開示](https://www.sec.gov/Archives/edgar/data/1561540/000106299326006170/exhibit99-1.htm)

- 2026-11-20 21:09 JST | 11/16→17を上場リスト2026-11-20 06:00 ET版で再検証。NYSE 1,866/1,894（98.52%）、Nasdaq 3,131/3,188（98.21%）、合計4,997/5,082（98.33%）で一次判定。Nasdaqの欠損151銘柄の公式日次を取得し、財務判定済み・分割等を除く補完92銘柄は再現できた。1カ月の公式終値でも新たな採用0件。Nasdaqの保留57銘柄は公式終値の2日分が揃わない56銘柄と分割除外1銘柄。NYSE28銘柄ではNasdaq公開履歴から22銘柄の参考終値は取れたが、対象日のTAQ公式無料サンプルは未掲載で、未調整終値を確認できず。取得元が切り替わった場合の同一銘柄・同日の予算入り通知を重複除外。実データ再生では予算入り17件を照合し、履歴保存後の重複0件。JVM117件とPython196件を実行し成功。APK生成・実機テストなし。 [銘柄別の照合ステータス](us-market-audit-20261117.json)

- 2026-11-20 19:15 JST | コード変更0。main 31ba244以降の差分はJPX権利データ1ファイルのみ、米株未統合PR #44/#47/#48/#49等を確認。85銘柄の個別原本調査はNYSE0/28・Nasdaq0/57、追加取得0・追加一次判定0、通知候補未測定・実配信未検証。ローカルGitHub接続はDNS解決失敗、代替としてGitHub接続機能からmain・PR・US判定コードを照合。既存判定4,999/5,084は今回再測定なし。次回は85銘柄の実銘柄一覧・価格原本とSplit/併合を取得して市場別理由を記録、PR重複統合前にCI実行を確認。APKなし。

- 2026-11-20 15時台 JST | 11/17のDoltHub欠損を、両日ともNasdaq公式未調整終値で確認できた92銘柄で補完。米株一次判定4,999/5,084、今回の補完での新規予算入り0件。NYSE28・Nasdaq57銘柄は保留。SEC全市場候補で3日分の差分更新・再起動を再生し、全件再取得と結果が一致。

- 2026-11-20 14時台 JST | 財務判定でも同日為替を必須にし、遅れて届いたレートで再計算するよう修正。実データで11/18の一次判定4,903/5,084を再計測。SEC原本の10銘柄を3取引日再生し、5銘柄を財務判定、重複保存0件。補完171銘柄は当時の未調整終値の裏付け待ち。JVM全111件成功。

- 2026-11-20 13時台 JST | PR #38・#40・#42の米株補完検証用コードと為替・銘柄照合テストを統合。関連Python18件を通過。追加通知対象は計上せず、Nasdaqで回復した171銘柄は欠損日の未調整終値照合待ち。

- 2026-11-20 05時台 JST | 分割・併合の銘柄コードがドットとハイフンで異なっても同じ株式クラスを照合対象から除外。不正な銘柄コードのカレンダーは保留。JVM106件に合格。Nasdaq原本を再生すると39銘柄を除外。欠損補完171銘柄は未調整終値の追加照合待ち。 [実装 0001a95](https://github.com/osawamas/value-hunter-ai/commit/0001a951d9930ac44f8b8c3e1193bb73778cdbef)

## 2026-11-20 03:15 JST — US市場別集合突合の二重計上防止

- 開始時main: 6f10055217700d6f8ce4543813f9616a97253ac8。USログ、最新Actions、JPXとの分離を確認。直近US CI #44574722120 は SHA 93d3b40 で success（2026-11-20 02:13 JST頃）。今回の変更後CIとは別。
- NYSEとNasdaqの上場集合に同一銘柄コードが現れた場合、財務集合と価格集合の二重計上・誤った除外を避けるため、集合突合を保留するガードを追加。[本体 15c5656](https://github.com/osawamas/value-hunter-ai/commit/15c565655a36ad1316465c0c4f254d77e7e1c71e)、[回帰テスト b42c8d6](https://github.com/osawamas/value-hunter-ai/commit/b42c8d63957ccf021c3d9bbf3c13a09cef80c81b)。JPX・Android・APK・原本には変更なし。**追加テストの成功・変更後Actions完走は未確認**。
- 11月16・17日の保存済み過去実測: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、合計4,909/5,086 (96.5%)。2日欠落177。予算入り候補19、財務判定済み重複2、残17は正規未調整終値・企業イベント等の証跡待ち。今回の新規取得0、財務再照合0、全4,194銘柄との集合突合後の正味簡易判定可能数未測定、確定通知候補未測定、Android端末の通知実測なし（確認済み0）。過去単日4,958・判定可能1,472とは基準が異なる。
- 次回: 最新Actions完走確認、保存原本の市場別実集合と財務4,194銘柄を突合、17候補の正規終値・公式イベント・日別FXを検証。PriceOnlyScreen/WorkManager接続とAndroid 15無音通知を検証。APIキー・追加費用・手動CSV・Mac不要、APKと株価原本は公開しない。


## 2026-11-20 02:15 JST — US集合突合で非正規銘柄キーを拒否

- 開始時main: 7456fe4b38b54a119b82f43376de1f00a34665d7（別担当の「US financial and price monitoring coverage replay」記録）。最新USログ・US CI #44553023487 success・JPX担当との競合を確認。JPX側は変更なし。
- 集合突合で前後に空白を含む銘柄コードが集合一致を壊し、財務重複を誤って非重複にする危険を抑止。非正規コードを入力時点で拒否する変更 [bacf898](https://github.com/osawamas/value-hunter-ai/commit/bacf8981c44a77d66bed135f5e87c4a43898086a)、回帰テスト [93d3b40](https://github.com/osawamas/value-hunter-ai/commit/93d3b4009ca5e25a2e81f88443ca1d8c2ecbfcda)。新規テスト実行と変更後Actionsの結果は未確認。
- 11月16・17日保存済み実測: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、計4,909/5,086 (96.5%)、欠落177。予算入り19候補、財務重複2、残17は独立正規終値・企業イベント等の検証待ち。今回は新規取得0、財務再照合0。全市場4,194財務集合との正味突合は未測定、通知確定0、Android実機通知未検証（通知ゼロを実測したわけではない）。過去単日4,958と通知可能1,472は別基準。
- 次回起点: 別担当の最新US coverage replayコミット内容を再確認して保存原本と4,194集合を突合、19候補の正規未調整終値・企業イベント・日別FX証跡を検証。PriceOnlyScreen/WorkManager・Android 15の無音通知は未検証。APK・株価原本は公開しない。

## 2026-11-20 01:15 JST — 変更後US CIの成功を確認

- 確認時main: de696467397867bb6d91f34074a607289596d6ca。JPX担当のコードは変更しない。
- [US daily market coverage probe tests #44553023487](https://github.com/osawamas/value-hunter-ai/actions/runs/44553023487) は2026-11-20 00:16 JSTごろ完了、結論 success。対象SHA 437f1445d4e3dc56ee96e1290a423e56b1abaa0c。前回の失敗 #44541936208 に対して、欠落取引日と不正形式を区別する回帰テスト追加後のCI成功を確認した。ログ保存コミット de69646 は skip ci であり、同コミット自体のCI結果ではない。
- 11月16・17日の保存済み観測値: NYSE 1,868/1,896、Nasdaq 3,041/3,190、計4,909/5,086 (96.5%)。今回新規取得0、財務再照合0。予算入り19候補中、財務判定済み2を除き17候補は未確定。市場全体の財務4,194銘柄との集合突合・未調整正規終値・公式企業行動検証は未完了。追加簡易判定可能数と確定通知対象は未測定、実機通知の検証済み件数0（実際の通知がゼロだった証明ではない）。
- 次回起点: 保存原本の市場別集合突合、17候補の独立価格原本と分割・併合照合、PriceOnlyScreen/WorkManager接続とAndroid 15での無音通知検証。APKと株価原本は公開しない。


## 2026-11-20 00:16 JST — 19候補のSEC重複照合結果を引継ぎ、CI失敗を調査

- 開始時main: d09f0eecc4459b202d5632cdb4026f0016b38281。JPXファイルは変更せず、US価格のみ判定の回帰テストを追加: [437f144](https://github.com/osawamas/value-hunter-ai/commit/437f1445d4e3dc56ee96e1290a423e56b1abaa0c)。欠落した取引日（invalid_trade_dates）と不正な行形式（invalid_observation）の違いを明示的に検査する。
- GitHub Actions [44541936208](https://github.com/osawamas/value-hunter-ai/actions/runs/44541936208) は失敗。android-private/toolsの113件は成功、scriptsの14件中1件が失敗。原因は None の日次観測に対する期待理由 invalid_trade_dates と実際の invalid_observation の不一致。現在mainの scripts/us_price_only_guard.py は None を先に検査し invalid_trade_dates を返すコードになっているため、過去の失敗SHAと現在mainを区別する。今回の追加テストと変更後Actionsの完走は未確認。
- 最新の11月19日付実データ照合記録では、11月16・17日の2日分NYSE 1,868/1,896（98.5%）、Nasdaq 3,041/3,190（95.3%）、合計4,909/5,086（96.5%）。照合前予算入り19（NYSE 7、Nasdaq 12）。SEC単一クラス照合でEVCM・RWAYの2銘柄は従来財務判定へ移行、残17は財務符号条件保留5、クラス・財務等の照合待ち12。分割表で対象2日内のイベント行なし、Nasdaq履歴と価格一致だが、独立した未調整正規終値の市場全体保証にはならない。価格のみ確定通知対象0、実端末通知未検証。
- 今回の新規取得0、財務再照合0、Android通知実測なし。財務4,194銘柄の市場別実集合と全4,909銘柄の正味簡易判定可能数は依然未測定。2日分不足177（NYSE28、Nasdaq149）。過去単日4,958/5,085と通知判定可能1,472は別基準。
- 次回: 新規US CIを確認し、失敗時修正。17保留候補の公式企業イベント・未調整終値・日別FX原本・SECクラス照合、全市場の財務集合突合、PriceOnlyScreen/WorkManager無音通知とAndroid 15検証。APIキー・手動CSV・追加費用・Mac不要、APK/株価原本は公開しない。


## 2026-11-19 — 予算入り19候補の終値・SEC財務を実データで照合

- 11月16・17日のDoltHub終値を同じ固定版から再取得。普通株候補4,909銘柄に日別USD/JPYを適用し、100株の購入額が10万円超から10万円以下へ移った候補19銘柄（NYSE 7、Nasdaq 12）を再現した。Nasdaq公開履歴と比較し、19銘柄で両日の終値が一致した。
- 最新の上場一覧・SECの取引所付きCIK一覧を突合。単一クラスと照合できた17社分のCompany Facts原本を取得し、Androidと同じJava財務処理を実行。EVCM・RWAYは従来の財務判定で評価可能だったため価格だけの対象から除外。両方とも従来の割安条件は対象外。残る17銘柄の内訳は、財務数値の符号条件で保留が5銘柄、上場クラス・必要財務等の照合待ちが12銘柄。
- DoltHubの分割表では、候補19銘柄に対象2取引日の分割行はなかった。Nasdaq公開履歴には過去の分割へ遡って調整する事例があるため、今回の二つの終値の一致だけでは独立した正規未調整終値の証明にならない。価格だけの追加通知は17銘柄を検証待ちとし、実機通知済みとして計上しない。APK未作成。 欠損観測を従来の日付不正として扱う判定の回帰を修正し、米株の判定・突合テスト14件成功。

## 2026-11-19 23:15 JST — 不正な価格観測データを通知前に安全拒否

- 開始時main直近SHA: c8a8f905c097241d4b36eb671e3303e54f462299。USログ、価格のみ判定本体・テスト・US CI、JPXの c31fed1（急変通知再試行・同日理由別重複排除）を確認。JPXファイルは変更なし。
- 価格観測行が文字列・配列・整数等の場合に、日付参照が未捕捉例外になり得る問題を修正。通常判定・期待取引日判定・証跡付き判定の入口で Mapping を要求し、不正行は通知不可とする。[本体 0cb8cbb](https://github.com/osawamas/value-hunter-ai/commit/0cb8cbb0e1d14d60df401bf7029c791a579d63e4)、[回帰テスト f027576](https://github.com/osawamas/value-hunter-ai/commit/f027576f27897d5637f4de9ebff1ed1fb325f520)。既存の正常な2日比較・証跡条件は変更なし。
- **追加テストの実行成功・変更後Actions完走は未確認**。今回の実Dolt取得・SEC財務照合・保存原本再生・Android通知実測は未実施。CI実行状態はこの回で取得できていない。
- 2026-11-16/17の保存済み過去実測: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、計4,909/5,086 (96.5%)。2日分不足177 (NYSE28/Nasdaq149)。照合前の条件入り19。今回新規取得0、財務再照合0、正味簡易判定可能数未測定、確定通知候補未測定、実通知確認0（端末実測なし）。財務4,194銘柄との重複、企業行動・独立正規終値・日別FX証跡による保留内訳は未測定。過去の単日4,958/5,085、通知判定可能1,472は別基準。
- 次回起点: CI完走確認、11月17日保存原本と財務4,194の実銘柄集合突合、19候補の公式イベント・独立未調整終値・日別FX・普通株クラス照合。PriceOnlyScreen/WorkManagerの無音・同日重複なし通知とAndroid 15を検証。APK・株価原本は公開しない。


## 2026-11-19 22:15 JST — 米国株の市場別集合突合ユーティリティ追加

- 開始時main直近: c31fed1b66c2eff868aeeabf970e193e66c7a6e2（JPXの急変通知再試行・同日理由別重複排除テスト）。USログ、US判定本体・テスト・CI、JPX直近コミットを確認。JPXコード未変更。
- [集合突合本体 724b26e](https://github.com/osawamas/value-hunter-ai/commit/724b26e9514b50693bb124226c7f3b04270c48ee)、[テスト 8f5b142](https://github.com/osawamas/value-hunter-ai/commit/8f5b1427d66fc0cdc49d68bbf16fc8b437abbef0)、[CI組込 753ef0f](https://github.com/osawamas/value-hunter-ai/commit/753ef0ff21bc2a92bfc1d1059f26a176b05e1933) を保存。NYSE/Nasdaq別の上場普通株・2日終値・財務登録済み・予算入り候補の**実銘柄集合**を要求し、財務重複を除いた簡易判定可能数、全上場母数比率、候補重複除外を計算。件数だけや市場不一致の集合は拒否。通知可能の最終確定は原本検証が必要なためnullとする。
- **今回の実データ再生は未実施**。集合原本が揃っておらず、財務4,194との重複排除実測・19候補の原本照合は未測定。追加テストと変更後Actionsの完走は未確認。Android 15無音通知未検証。コードは保存済みだが通知への接続は完了していない。
- 2026-11-16/17の保存済み過去観測: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、合計4,909/5,086 (96.5%)。2日不足177 (NYSE28、Nasdaq149)。照合前の条件入り19。今回新規取得0、財務再照合0、正味簡易判定可能数未測定、確定候補未測定、実通知確認0（端末実測なし）、保留内訳は2日終値不足177以外未測定。
- 次回: 11月17日保存原本の銘柄集合と財務登録済み4,194集合を実際に読み込み突合し、19候補の未調整正規終値・日別FX・SEC普通株クラス・分割併合原本を照合。CI完走とPriceOnlyScreen/WorkManager無音通知を検証。APK・株価原本は公開しない。

## 2026-11-19 21:16 JST — US未調整終値・日別FXの通知前証跡ゲートを追加

- 開始時最新mainの直近コミット: e2fc7d3827a3ae863a322126012637b91b90afc8（JPX担当の企業イベント証跡テスト）。USログ・US CI定義・US価格のみ判定本体とテストを確認。JPXファイルは変更していない。
- US判定に `evaluate_verified_budget_entry` を追加。2取引日とも `price_basis=raw_unadjusted_regular_session`、同日 `fx_date`、空でない `close_source`/`fx_source` を要求。分割調整済み終値、FX日付違い、原本参照欠落を通知前に保留する。[本体 59155f8](https://github.com/osawamas/value-hunter-ai/commit/59155f821bbaa180a2e29b157eacbceb89f28ec9)。
- 通過例、調整済み・価格基準欠落・FX日付違い・参照欠落・セッション違いの回帰テストを追加。[テスト 60c7472](https://github.com/osawamas/value-hunter-ai/commit/60c7472e9be8ae7fbd293164ea95201d60448892)。**新関数は既存Android通知へ未接続**。GitHub保存確認済みだが新規unittest・変更後Actions完走・Android 15エミュレータは未確認。ソース参照文字列の実在性も別途照合が必要。
- 2026-11-16・17の**過去保存ログ値**: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、計4,909/5,086 (96.5%)、2日分不足177 (NYSE28/Nasdaq149)。照合前の予算入り19。今回新規終値取得0、財務照合0、正味簡易判定可能数未測定、確定候補未測定、実端末通知未検証（確認できた新規0）。財務4,194銘柄との重複、19候補の正規未調整終値・企業イベント・日別FX原本、保留理由別内訳は未測定。過去単日4,958/5,085、財務2,746、通知可能1,472は異なる基準で今回再測定なし。
- 次回起点: 19候補と財務4,194集合の保存原本突合、公式企業イベントと独立正規終値を個別検証し、証跡ゲートをPriceOnlyScreen/WorkManagerに接続。US CI実行結果とAndroid 15の無音・重複なし通知を確認。APIキー・手動CSV・追加費用なし、APKと株価原本の公開なし。


## 2026-11-19 20:15 JST — US価格のみ通知の未照合財務状態を安全側に固定

- 開始時の最新main: 773ab70a652c93346888ea207d75963995388049。JPX担当の同日急変重複排除テストと予算通知理由の分離を確認。US独立モジュール以外は変更なし。
- US予算入り判定で financials_verified=None/0/空文字などが従来の false 扱いで通過し得る条件を修正。財務未照合が明示的に False の場合だけ価格のみ通知の候補に進める。ordinary_share_verified/corporate_actions_verified/source_verified は厳密に True、stale_cache は厳密に False を要求。[本体 9f5dbbf](https://github.com/osawamas/value-hunter-ai/commit/9f5dbbf10a67660034c088a4f2ef47dbe8d48994)。
- 未照合状態と曖昧な証跡フラグの回帰テストを2件追加。[テスト 54675b0](https://github.com/osawamas/value-hunter-ai/commit/54675b0838659384bb2a46447a4decc1e7190f0c)。実行と変更後Actions成功は未確認。Android無音通知の実機検証は未実施。
- 2026-11-16・17保存ログの過去実測: NYSE 1,868/1,896 (98.5%)、Nasdaq 3,041/3,190 (95.3%)、合計4,909/5,086 (96.5%)。未取得177 (NYSE28/Nasdaq149)。照合前予算入り19。今回新規取得0、財務照合0、正味簡易判定可能数未測定、確定候補未測定、実通知未検証（確認できた新規0）。財務4,194集合との重複排除、独立正規終値と企業イベント照合、保留理由別集計は未実施。
- 次回起点: CI完走確認、財務集合と保存原本の突合、19候補の正規未調整終値・企業イベント・日別FX・普通株クラスの原本確認、PriceOnlyScreen/WorkManager接続とAndroid 15での無音・重複なし検証。APK・株価原本は公開しない。


## 2026-11-19 19:17 JST — US価格のみ判定テストをCIに組み込み

- 作業前の最新mainは [b4f670a](https://github.com/osawamas/value-hunter-ai/commit/b4f670a7474e7b474964e5c1209b2c7f3426a443)。JPX担当の配当落ち証跡不足時の急変保留テストを確認し、JPXコードは変更なし。USログ、既存US CI、US価格のみ判定テストのコミットを確認。
- 既存US CIは android-private/tools のunittestのみ実行し、scripts/test_us_price_only_guard.py（11月19日追加のセッション境界・古いキャッシュ拒否を含む）を実行していなかった。push/PRのpath対象に scripts/us_price_only_guard.py と scripts/test_us_price_only_guard.py を追加し、scripts作業ディレクトリで独立した unittest ステップを追加。[CI変更 19b7234](https://github.com/osawamas/value-hunter-ai/commit/19b7234dd150b5a1aac53a8ae347dfd140f27f48)。JPXコード・APK・原本は未変更。
- CIの実際の完走・テスト成功は未確認。今回のコード改修はCI設定のみであり、保存原本の再生、SEC/財務4,194銘柄との集合突合、公式企業イベントと正規未調整終値の検証、Android 15無音通知実行は未実施。
- 11月16・17日保存ログの過去実測: NYSE 1,868/1,896（98.5%）、Nasdaq 3,041/3,190（95.3%）、計4,909/5,086（96.5%）、2日分欠落177（NYSE28/Nasdaq149）。照合前予算入り19銘柄。これは今回の再取得ではない。過去の単日4,958/5,085、SEC財務2,746、通知判定可能1,472も別基準の過去値。
- 今回の新規終値取得0、財務再照合0、簡易判定可能増分未測定、確定通知候補未測定、確認できた新規通知0（端末通知実測ではない）、保留のうち2日終値欠落177、その他の財務重複・価格基準・企業イベントによる保留内訳未測定。財務4,194集合の原本がないため正味数は算出不可。
- 次回起点: 追加したUS CIステップの完走結果を確認。11月17日保存原本と財務登録済み集合を突合し、19候補の正規終値・分割併合・日別USDJPY・普通株クラスを独立照合してから、PriceOnlyScreen/WorkManagerの無音通知を検証。APIキー/追加費用/手動CSVなし、APKと株価原本の公開なし。

## 2026-11-19 18:19 JST — 米国株2取引日の古い終値へのすり替わりを拒否

- 開始時main: [cc8af255](https://github.com/osawamas/value-hunter-ai/commit/cc8af25556592465f5c0abc1f6c5115a5bc29a3f)。JPX担当の財務登録済み除外（90c1bb5, 82ecf1a, cc8af25）と重複通知ゲート（e2758f4, 63e5eb4）を確認。JPX側は未変更。
- 米国の価格のみ予算入り判定に、取引所カレンダーから呼び出し側が指定した前回・今回の取引日と観測日が完全一致しない場合は保留する `evaluate_budget_entry_for_sessions` を追加。[本体 df7152c](https://github.com/osawamas/value-hunter-ai/commit/df7152cd10cc8d6988848240dd3afda020f5f8a1)。前営業日終値が欠落して古いキャッシュに置換された場合の誤通知防止。週末を含む日付間隔は許すが取引日カレンダーの正しさは呼び出し側責任。
- 欠落・古い終値・正常2日分・非連続日付・逆順セッションの回帰テストを追加。[テスト 61089bf](https://github.com/osawamas/value-hunter-ai/commit/61089bf44961baf5e669c6dcb7ead2ac1ccf8ba0)。**追加テスト実行と変更後Actions完走は未確認**。Android側の呼び出し・無音通知接続は未完了。GitHubへの保存のみ確認。
- 11月16・17日保存ログの過去実測: NYSE 1,868/1,896（98.5%）、Nasdaq 3,041/3,190（95.3%）、合計4,909/5,086（96.5%）。2日分未取得177（NYSE28、Nasdaq149）。予算入り19銘柄は財務重複・企業行動・正規未調整終値の照合前。過去の単日4,958/5,085、SEC照合2,746、通知判定可能1,472は別基準の過去値。
- 今回の新規実データ取得0、財務再照合0、正味簡易判定可能数未測定、確定候補未測定、実通知未確認（確認済み新規通知0）、企業行動・財務重複・価格基準による保留内訳未測定。財務4,194銘柄の集合と価格原本がなく、正味の母数と通知数を確定できない。Android 15/WorkManager/US CIの新規完走も未確認。
- 次回起点: 保存原本と財務4,194の集合を突合し、19候補の企業行動・未調整終値・各日USDJPYの原本照合、US AndroidのPriceOnlyScreenと無音通知接続、CI実行結果を検証。APK・株価原本を公開しない。


## 2026-11-19 — DoltHubの終値取得で最後のページを回復

- 最後の昇順ページがタイムアウトした場合に限り、Androidは同じDoltコミットから末尾を降順で取得する。既に取得した行との重複部分を照合し、日付・銘柄・終値が一致する場合だけ不足行を補う。
- 固定したコミットの11月16・17日のデータを取得。実データをJavaで再生し、17日の最後のページをタイムアウトさせても欠落604行を回復した。16日は12,639行、17日は12,604行で配信元の件数に一致した。
- 11月18日21:31米東部時点の上場一覧と突合。2日分の終値を取得できた普通株候補はNYSE 1,868/1,896、Nasdaq 3,041/3,190、合計4,909/5,086（96.5%）。前回の4,717銘柄から192銘柄増。両日のドル円で計算した100株10万円以下への移行は19銘柄。価格基準や財務判定済みとの重複を再照合する前の参考数。
- 関連JVMテスト4件成功。Android実機での取得、無料経路での無音通知、追加の通知対象数は未検証。APKは作成していない。

## 2026-11-19 16:15 JST — 調整済み終値による誤通知を防ぐ回帰条件

- 作業前mainの直近コミット: [7f4dfe8](https://github.com/osawamas/value-hunter-ai/commit/7f4dfe81828c73af4a9bfe3dfde868d80d34b33b)。JPXの急変判定2コミットとUSのAndroid接続 [13c3c64](https://github.com/osawamas/value-hunter-ai/commit/13c3c6439f74d1cb96f87884a95339e348002d33)、Nasdaq履歴の分割調整問題 [0211571](https://github.com/osawamas/value-hunter-ai/commit/02115716b020f5c445f57f7448d56195f9ed9467) を確認。JPX側は未変更。
- [回帰テスト 61c09ef](https://github.com/osawamas/value-hunter-ai/commit/61c09ef178955290e498e3ba27c91ef126c22575) を追加。前日が調整済み、または当日の調整有無が欠落している場合、予算入り比較を参考表示できても通知用の価格基準を検証済み扱いにしない条件を固定。実装本体の変更なし。追加JUnitの実行と変更後Actions成功は未確認。
- 既存ログの11月16・17日2日分普通株候補はNYSE 1,803/1,896（95.1%）、Nasdaq 2,914/3,190（91.3%）、合計4,717/5,086（92.7%）。**これは保存ログの過去観測で、今回の再取得・全上場に対する財務重複排除ではない。** 11月17日単日4,958/5,085も過去の別基準。SEC照合2,746、通知判定可能1,472も過去値。財務4,194銘柄の市場別突合表と正規原本がこの回では得られず、簡易判定可能の正味数・候補・実端末通知数は未測定（実際の新規通知を確認できた件数0）。新規終値取得0、財務再照合0、割安判定可能増分0。保留は2日分不足NYSE93、Nasdaq276（合計369）を過去ログから算出、財務・企業行動・価格基準の保留内訳は未測定。
- 次回: 11月17日保存原本と財務4,194の銘柄集合を安全な実行環境で突合、価格基準・分割併合の証跡を個別に照合。US CI、WorkManagerとAndroid 15の実動作、2日分正規未調整終値・日別USDJPY・重複通知防止を確認。APK・株価原本は公開しない。


## 2026-11-19 — 無料の2日分終値と併合前後の価格基準を照合

- Nasdaqの公開履歴から11月16・17日の終値をAAPL・IBM・MSFT・SPWRの4銘柄で取得した。日時・銘柄・重複および欠損を検査する `android-private/tools/us_nasdaq_close_probe.py` を追加した。関連単体テスト14件成功。
- [発行会社の8-K](https://www.sec.gov/Archives/edgar/data/1838987/000121390026120226/ea0312352-8k_sunpower.htm) でSPWRが11月18日の寄り付きから35株を1株に併合したことを確認。併合前の11月16日、17日はNasdaq履歴の終値がDoltHubの約35倍。18日は両者が一致した。この事例ではNasdaq履歴は遡及調整済み、DoltHubは当時の株数基準だった。全銘柄の未調整終値を検証した結果ではない。
- DoltHubの件数照会は16日12,639行・17日12,604行を返した。件数には普通株以外も含む。ピン留めした版で16日は12,639行、17日は12,000行を取得。17日の最後604行は再試行後もタイムアウト。18日21:31米東部時点の上場一覧と突合し、2日分の普通株候補を少なくともNYSE 1,803/1,896、Nasdaq 2,914/3,190、合計4,717/5,086銘柄で取得した。両日のドル円も取得した。Androidの無料経路での無音通知と新規通知可能数は未検証。APKは作成していない。

## 2026-11-19 15:15 JST — 米株2営業日予算入り判定の安全ガードを追加

- 開始時main: [6513442](https://github.com/osawamas/value-hunter-ai/commit/6513442df3a03e7d7303e9cc2e6038a11355490c)。JPX担当が価格のみ予算入り通知を追加したことを確認。JPXコードは変更せず、米国株独立モジュールを追加。
- [判定ガード 6be1305](https://github.com/osawamas/value-hunter-ai/commit/6be130598da9d54b059d565f6c3c675d7d568b5c) と [6件のテスト 83f501e](https://github.com/osawamas/value-hunter-ai/commit/83f501e17b9f757cede875b052c148967f2457a7) を保存。2営業日それぞれの終値・USDJPYから100株円換算し、10万円超から10万円以下への入りのみ抽出。財務照合済み、普通株未確認、企業行動未確認、原本未確認、古いキャッシュ、欠損・不正日付・NaNは判定対象外。これは独立ガードであり、既存PriceOnlyScreen/WorkManagerへの接続と急変通知は未実装。
- テストコードは保存済みだがリポジトリ内での実行・変更後Actionsは未確認。Dolt実同期、2営業日の未調整正規終値と日別USDJPYの原本再生、11月17日保存原本による財務4,194銘柄との重複排除は未実施。過去の4,194という財務数の市場別内訳も未照合。
- 過去基準は2026-11-17取引日・11月18日観測母数。NYSE終値1,877/1,896、Nasdaq終値3,081/3,189、合計4,958/5,085。過去SEC財務照合2,746、通知判定可能1,472。**今回の新規終値取得0、財務照合0、割安判定可能増分0、候補0、実通知0。** 新しい簡易判定可能数と市場別比率、保留内訳は原本・突合表不足のため未測定。
- 次回起点: 2営業日の未調整正規終値と各日USDJPYを取得・検証して保存、SEC未照合普通株と財務判定済み集合を差し引き、JPX担当のPriceOnlyScreen契約を確認して米国株側の通知を接続する。古いキャッシュでは通知しない。急変は企業行動・価格基準検証後。APKと株価原本は公開しない。

## 2026-11-19 14:15 JST — 古いDoltキャッシュを日次更新成功と誤認しない

- 開始時の最新mainは [3237b4a](https://github.com/osawamas/value-hunter-ai/commit/3237b4abaa9c784fd14339bec92cd56a81452c83)。US開発ログ・同期本体・既存テストと直近コミットを確認。JPXファイルは変更していない。
- Dolt同期CLIがHTTP 429、タイムアウト、OSエラー後に既存キャッシュを保持した場合、従来は終了コード0であり、呼び出し側が「本日の更新成功」と誤認し得た。キャッシュ自体は保全しつつ、CLIを非ゼロ終了させて更新未完了を伝えるよう修正。[本体 3d54570](https://github.com/osawamas/value-hunter-ai/commit/3d5457051a11eddf1e9a3bac38739a23f0014741)。正常なupdatedは成功のまま。
- 3種のキャッシュ代替状態で終了コード1、正常updatedで終了コード0を要求するCLI境界テストを2メソッド追加。[テスト db845d6](https://github.com/osawamas/value-hunter-ai/commit/db845d62dc7ee870abb4b4079dc5c63df1896fae)。コードはGitHubに保存済み。ただし**追加unittest実行、変更後Actions成功、実Dolt同期は未確認**。pushワークフローの実行結果はこの接続から確定できない。[US CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。
- 過去の基準: 2026-11-17取引日、11月18日観測一覧母数。NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、同日厳密網羅率ではない）。SEC財務照合2,746、通知判定可能1,472も過去値。**今回の再測定なし**。今回新規終値取得0、財務再照合0、割安判定0、候補0、通知0。保留内訳は未測定。
- 次回起点: CIでCLI回帰テストの完走を確認し、呼び出し側が非ゼロ終了を適切に保留扱いするか調べる。続いてDolt実同期・SEC未照合銘柄の原因分類と削減、正規未調整終値/株式クラス/基準日照合、Android 15/WorkManager/無音通知へ進む。APK・株価原本・APIキーは公開しない。

## 2026-11-19 13:18 JST — 初回Dolt cloneのルートsymlink誤認を回帰テスト化

- 開始時main: [55a3233](https://github.com/osawamas/value-hunter-ai/commit/55a32336e5370a4e7e2e756a7e7c8f338b6adf7a)。最新コミット、当ログ、US同期本体・既存テスト・US Actions定義を確認。直近JPX担当の監査回帰テスト追加を確認しJPX側は変更なし。
- 初回cloneの終了コード0でも保存先ルートが別の有効なDoltディレクトリへのsymlinkに置換されていたら成功扱いしない回帰テストを追加。[テスト変更 e982b25](https://github.com/osawamas/value-hunter-ai/commit/e982b259bf5223308a687bb91895e325a364c99c)。既存本体の拒否分岐を固定するテストであり本体変更なし。追加unittest実行と変更後Actionsは未確認。[US CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。実Dolt同期・実429・Android 15検証も未実施。
- 過去基準: 対象取引日2026-11-17、11月18日観測一覧母数でNYSE 1,877/1,896、Nasdaq 3,081/3,189、計4,958/5,085（97.5%、同日厳密網羅率ではない）。過去SEC財務照合2,746、通知判定可能1,472。今回新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。最新値の再測定なし。
- 未解決: CI完走、実Dolt日次同期、未調整終値・分割前価格、SEC株式クラス・株数基準日、PER/PBR、WorkManager/無音通知。次回はCI完走を確認し、Dolt同期またはSEC未照合原因分類を進める。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。APK・株価原本・APIキーは公開しない。

## 2026-11-19 12:17 JST — 429判定とメタデータ消失の独立再現（実同期未実施）

- 開始時main: [77878ba](https://github.com/osawamas/value-hunter-ai/commit/77878baec4f9937fafdb389da13810e81fbb5a4d)。最新コミット、当ログ、US CI定義、Dolt同期本体・既存テストを確認。直近JPX担当はPDF取得監査・Android単体テストの変更で、競合するコードは変更せず。
- Python 3で現行 `RATE_LIMIT` 正規表現を独立実行。HTTP 429・Too Many Requests・status=429の検出、4290・X429・1429・429A・無関係なretry文字列の非検出、計8ケース成功。tempfileで既存 `.dolt` 消失の再現1件成功。これは**同期コードのunittest実行やDolt実同期の成功ではない**。GitHubへのローカルcloneはDNS名前解決失敗で不可。コード変更なし（既存テストと重複するため）。
- 直近mainのcombined commit statusは0件。push後のActions完走は取得できず未確認。[US CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。対象取引日は過去の2026-11-17、11月18日観測一覧基準: NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、同日厳密網羅率ではない）。過去のSEC財務照合2,746、通知判定可能1,472。**今回の実測**: 新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。
- 未解決: Dolt実同期、正規未調整終値・分割、SEC株数/クラス/基準日、正式PER/PBR、Android 15/WorkManager/無音通知。次回はUS CI完走と実同期を再試行、不可ならSEC未照合の具体的原因を分類。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。APK・株価原本・APIキーは公開しない。

## 2026-11-19 11:15 JST — 初回Dolt cloneの不正メタデータを回帰テスト化

- 開始時main: [56540d8](https://github.com/osawamas/value-hunter-ai/commit/56540d80e12d248b4cac819ec2c893b44ccd2e83)。最新コミット・US開発ログ・US CI定義・Dolt同期本体とテストを読んだ。JPX担当の直近[04df09a](https://github.com/osawamas/value-hunter-ai/commit/04df09a4ec60a10a42df1a9eeda68461c74607f1)と[56540d8](https://github.com/osawamas/value-hunter-ai/commit/56540d80e12d248b4cac819ec2c893b44ccd2e83)を確認し、JPXファイルは変更なし。
- 初回cloneが終了コード0を返しても、作成された `.dolt` が外部ディレクトリへのsymlinkなら正常なリポジトリと判定しない回帰テストを追加。[テストコミット 565e064](https://github.com/osawamas/value-hunter-ai/commit/565e064d9b6fe6adb77f67fc3e7f2c78260d0d85)。同期本体は既存の拒否条件を維持。独立Python再現でsymlinkを拒否する条件1件成功。ただし追加unittest自体と変更後Actionsは未確認。[US CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。
- ローカルGit接続はgithub.comのDNS名前解決失敗。実Dolt同期・実HTTP 429・SEC再照合・Android 15エミュレータ未実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。
- 対象取引日2026-11-17、11月18日観測一覧を母数とする**過去値**: NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、厳密な同日網羅率ではない）。SEC財務照合2,746、通知判定可能1,472も過去値。今回新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。
- 次回: 追加テストのCI完走、Dolt実同期、SEC未照合の削減と株数・株式クラス・企業イベントの検証。APK・株価原本・APIキーは公開しない。

## 2026-11-19 10:10 JST — FileNotFoundError時のDoltキャッシュ破損を区別

- 開始時main: [0c25ab6](https://github.com/osawamas/value-hunter-ai/commit/0c25ab6e849627e57d4957cbc647b052413a130c)。直近JPX担当の原本PDF SHA256同一性監査2コミット、US開発ログ・Dolt同期コードとテスト・US Actions定義を確認。JPXファイルは変更なし。
- Dolt runnerがFileNotFoundErrorを出したとき、既存キャッシュの.doltが同時に消えたケースを単なるdolt_not_installedと誤分類していた。既存キャッシュ破損ならinvalid_repository_after_command、初回cloneの部分ファイルが残ればpartial_clone_requires_manual_cleanupへ修正。[本体 a739a54](https://github.com/osawamas/value-hunter-ai/commit/a739a548e29988df0b71c6badcf37d38bab898fb)。2件の回帰テスト追加。[テスト 6fc1847](https://github.com/osawamas/value-hunter-ai/commit/6fc18476526192a456553d4548c0509e26d6fa7d)。
- GitHubへの2コミット保存と最新mainへの反映は確認。リポジトリ内unittestは未実行。コミットに紐づくActions取得は0件（コネクタはPRトリガーのみ返す制限あり）で、push後CI成功は未確認。[US CI一覧](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。Dolt実同期・実429・Androidエミュレータ未実施。
- 対象取引日2026-11-17、11月18日観測の母数による**過去値**: NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、同日厳密網羅率ではない）。SEC財務照合2,746、通知判定可能1,472も過去値。今回新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。
- 未解決: CI完走と実Dolt同期、未調整終値・分割、SEC株数/株式クラス/基準日、正式PER/PBR、Android 15・WorkManager・無音通知。次回はCI完走とDolt実同期、不可ならSEC未照合銘柄を調査。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC](https://www.sec.gov/edgar/sec-api-documentation)。株価原本・APIキー・APKは公開していない。

## 2026-11-19 09:15 JST — 429判定の独立再現

- 開始時main: 62f15ba6e7e70f78ea42cff2a5c70bad5c07b725。最新USログ、Dolt同期コードとテスト、US Actions定義、直近JPXのissuer-source監査コミットを確認。JPX側は変更なし。
- Python 3標準reで同期コードの429判定正規表現を独立再現。HTTP 429 / Too Many Requestsを検出、1429 / 4290 / 429A / X429を除外する計6件すべて成功。既存テストと重複するため今回は本体コードを変更しない。リポジトリ内unittestは未実行。
- [US Actions定義](https://github.com/osawamas/value-hunter-ai/blob/main/.github/workflows/us-daily-coverage-tests.yml)を確認。最新mainのcommit statusは個別0件。push Actions一覧を取得できず成功未確認。[US CI一覧](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。実Dolt同期・実429・Androidエミュレータは未実施。
- 対象取引日2026-11-17、11月18日観測の母数による過去値: NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、厳密な同日網羅率ではない）。SEC財務照合2,746、通知判定可能1,472も過去値。今回新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。
- 未解決: 実Dolt日次同期、正規未調整終値と分割、SEC株数・クラス・基準日、正式PER/PBR、WorkManager・無音通知。次回は実同期・CI完走、不可ならSEC未照合削減。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC](https://www.sec.gov/edgar/sec-api-documentation)。株価原本・APIキー・APKは公開していない。

## 2026-11-19 08:19 JST — Dolt同期のOS例外・失敗終了後のリンク差し替えを拒否

- 開始時main: [3be9337](https://github.com/osawamas/value-hunter-ai/commit/3be9337ae3f196b73b4ff3ed73d667f242cafd99)。最新US開発ログ、同期本体、既存回帰テスト、US Actions定義、直近JPXのPDFリダイレクト拒否2コミットを確認。JPXコードには触れず。
- 既存Dolt保存先がrunner実行中にsymlinkへ置換されると、OS例外または非ゼロ終了時にリンク先の.doltを正常キャッシュと誤認する分岐を修正。[本体 e5df789](https://github.com/osawamas/value-hunter-ai/commit/e5df789fbff59ccd550f236b76ff6a7d9d21eff7)。OS例外とHTTP 429失敗終了の2ケースを再現する回帰テストを追加。[テスト 80e6776](https://github.com/osawamas/value-hunter-ai/commit/80e67760ce99d348101b41a5ee89954942af0867)。
- GitHub APIでソースとテストの保存を確認。ローカルcloneはgithub.comのDNS解決失敗で不可。新規unittest・変更後Actionsは未確認（commit status APIに個別statusなし）。[US Actions一覧](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。実Dolt同期・実429・Android 15エミュレータは未実施。
- 対象取引日2026-11-17（過去基準）、母数は11月18日観測一覧。過去終値NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、厳密な同日網羅率ではない）。過去SEC財務照合2,746、通知判定可能1,472。今回新規終値0、財務再照合0、割安判定0、候補0、通知0、保留内訳未測定。全数値は今回の再測定ではない。
- 未解決: 新規CI結果、実Dolt日次同期、正規セッション未調整終値と株式分割、SEC株数・クラス・基準日、正式PER/PBR、Android連続更新と重複なし無音通知。次回はCI完走と実Dolt同期を優先し、不可ならSEC未照合銘柄の削減を実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。株価原本・APIキー・APKは公開していない。

## 2026-11-19 07:15 JST — Dolt同期先の実行中symlink差し替えを拒否

- 開始時main: [680539f](https://github.com/osawamas/value-hunter-ai/commit/680539fcb82d78f616414b217fe1bf24bac6d2af)。直近JPX担当のPDF通信再試行・404回帰テスト変更を確認。US開発ログ・同期本体・テスト・CI定義を読んだ。直近Actions全件のAPI取得は未確認。直近既知[US CI 44377757535](https://github.com/osawamas/value-hunter-ai/actions/runs/44377757535)は以前の成功であり今回の成功ではない。
- Dolt pullの429待機中、同期先ディレクトリそのものがsymlinkに置き換わると、リンク先に正常な.doltがある場合に再試行が別フォルダへ向かう可能性があった。再試行直前とコマンド後にルートsymlinkを拒否する。[実装 6967473](https://github.com/osawamas/value-hunter-ai/commit/6967473a6d04e0f9719edb29d94bc54d864fe36e)。429待機後と正常終了直後の差し替えを再現する2テストを追加。[テスト 0e4ec5](https://github.com/osawamas/value-hunter-ai/commit/0e4ec528c5dcfddeaf6647dc65689dcc29111585)。GitHubへ保存済み。追加テストのローカル実行・変更後Actions・実Dolt同期は未確認。JPXコードは未変更。
- 対象取引日2026-11-17（過去基準）。今回新規終値0件、財務再照合0件、割安判定0件、候補0件、通知0件。保留内訳は未測定。11月18日観測の母数を使った過去照合NYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、厳密な同日網羅率ではない）。SEC照合2,746、通知判定可能1,472は過去値で再測定なし。
- 未解決: 新規CIの完走、実Dolt同期、正規未調整終値・株式分割とSEC株数基準日の照合、PER/PBRの正式判定、Android 15/WorkManager/無音通知。次回は追加テストCIの完走と実同期を優先し、同期不能ならSEC未照合の削減を進める。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC](https://www.sec.gov/edgar/sec-api-documentation)。株価原本・APIキー・APKは公開していない。

## 2026-11-19 06:16 JST — Dolt同期先のシンボリックリンクを拒否

- 開始時main: [cfba4fb](https://github.com/osawamas/value-hunter-ai/commit/cfba4fb578c3c013f94162e9c0d4c863fa4421c3)。当ログ、直近JPXのissuer-level集計変更、US同期本体・テスト・CI定義を読んで競合回避。US CI前回確認済み[44377757535](https://github.com/osawamas/value-hunter-ai/actions/runs/44377757535)はsuccess。ただし今回の変更後CIは未確認。pushに対する最新Actions全件の取得はコネクタ制約で未確認。
- 同期先のルートがsymlinkの場合、従来のPath.resolve()がリンク先に移動して別ディレクトリをpullし得たため、絶対パス化後にリンクを拒否。[本体 a614d7c](https://github.com/osawamas/value-hunter-ai/commit/a614d7ca851781eb8784a37a4e02d9b0fe1b0a18)、[回帰テスト b80334f](https://github.com/osawamas/value-hunter-ai/commit/b80334f5df66d08dfe134ffe991baa043ee3104b)。独立した最小Python再現1件は成功。リポジトリの新規unittest・変更後Actionsは未実行/未確認。実Dolt同期も未実施。
- 対象取引日2026-11-17（過去値）。今回新規終値0件、財務再照合0件、割安判定0件、候補0件、通知0件。候補・保留の最新内訳は未測定。過去の11月18日観測一覧を母数とするNYSE 1,877/1,896、Nasdaq 3,081/3,189、計4,958/5,085（97.5%）は今回未再測定。SEC財務照合2,746、通知判定可能1,472も過去値であり今回の実測ではない。
- 未解決: 新規CI完走、Dolt実同期、正規未調整終値/株式分割、SEC株式クラス・株数基準日、正式PER/PBR、Android 15/WorkManager/無音通知。次回は新規CI結果とルートsymlink回帰テスト、Dolt実同期・SEC未照合の削減を優先。JPXコードは未変更。株価原本・APIキー・APKは公開していない。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。

## 2026-11-19 05:15 JST — Dolt同期終了直後のキャッシュ差し替えを回帰テスト化

- 開始時main: [e0cc70b](https://github.com/osawamas/value-hunter-ai/commit/e0cc70bbb153d1adab7bad91197f92fed5e7343a)。最新main、当ログ、US CI定義・同期コード・既存テスト、JPX担当の直近修正を確認。JPXコードは変更せず。
- Dolt pullがHTTP 429で失敗した直後、または終了コード0を返した直後に、.dolt管理情報がシンボリックリンクへ差し替わるケースの回帰テスト2件を追加。[テスト 47033f6](https://github.com/osawamas/value-hunter-ai/commit/47033f6d398042397230bef8955b24cbff7ea42a)。US CIの実行対象と変更パスに追加。[CI定義 bb2627e](https://github.com/osawamas/value-hunter-ai/commit/bb2627e4d8a62dd1ca5bea6ee5d7178fad577e57)。本体実装の変更なし。テストはコード上の既存保護条件を固定するもの。
- 前回[US CI 44377757535](https://github.com/osawamas/value-hunter-ai/actions/runs/44377757535)のtestジョブはsuccessと確認。**今回追加テストの実行・変更後CIは未確認**。直近確認できた[Android CI 44375275314](https://github.com/osawamas/value-hunter-ai/actions/runs/44375275314)はverify工程でfailure。JPX担当が[例外宣言を修正 e0cc70b](https://github.com/osawamas/value-hunter-ai/commit/e0cc70bbb153d1adab7bad91197f92fed5e7343a)しているためAndroid失敗の再確認が必要。
- 対象取引日2026-11-17（過去の保存結果）。今回新規終値0件、SEC財務再照合0件、割安判定0件、通知0件。11月18日観測一覧を母数とする過去値はNYSE 1,877/1,896、Nasdaq 3,081/3,189、合計4,958/5,085（97.5%、取引日当日の厳密な網羅率ではない）。SEC照合2,746件、通知判定可能1,472件も過去値。今回の候補・保留内訳は未測定。
- 未解決: 今回のCI完走、Dolt実同期/429、正規セッション未調整終値・分割前価格、SEC株式クラスと株数基準日、正式PER/PBR、Android 15連続更新・WorkManager・無音通知。次回はCI結果、Dolt実同期とSEC未照合の拡大を優先。原本株価・APIキー・APKは公開していない。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC API](https://www.sec.gov/edgar/sec-api-documentation)。

## 2026-11-19 04:15 JST — Doltキャッシュのシンボリックリンク拒否を追加

- 開始時main: [eead76b](https://github.com/osawamas/value-hunter-ai/commit/eead76bdf4fef6468a6a835a1ed389896e1f19b1)。最新main・当ログ・JPX担当の直近3コミット・同期実装とテスト・Actionsを読んで重複を回避。
- 既存キャッシュの `.dolt` がシンボリックリンクの場合、実体がディレクトリでも正常なDolt管理情報として扱わない。初期検査と429待機後・失敗後・成功後の検査に共通関数を適用。[本体 98ca420](https://github.com/osawamas/value-hunter-ai/commit/98ca4207d1bc9c850b4fd335432162020e7a9dae)。
- 事前にリンクを置いた場合はDoltを実行せず拒否、429待機中にリンクへ置換された場合は再試行せず停止する回帰テスト2件を追加。[テスト ff18798](https://github.com/osawamas/value-hunter-ai/commit/ff18798ffef5629f96dc75e570f4daac88bc9c7c)。GitHubへの保存成功。ローカルunittestは未実施。変更後[米国CI 44377757535](https://github.com/osawamas/value-hunter-ai/actions/runs/44377757535)は後続確認で**success**（変更後テスト完走）。変更前[米国CI 44367951698](https://github.com/osawamas/value-hunter-ai/actions/runs/44367951698)はsuccess。[直近Android CI 44375275314](https://github.com/osawamas/value-hunter-ai/actions/runs/44375275314)はfailure（verify工程、原因未特定）。
- 対象取引日2026-11-17。今回新規終値0、財務再照合0、候補再判定0、通知0。既存11月18日観測一覧基準の終値NYSE 1,877/1,896、Nasdaq 3,081/3,189、計4,958/5,085（厳密な当日網羅率ではない）。SEC財務照合既存2,746件、通知判定可能1,472件は過去基準値で今回未再検証。候補・保留の最新内訳は未測定。
- 未解決: 変更後CI成功、Dolt実同期/実429、正規未調整終値と分割前価格、SEC株数・株式クラス・企業イベント、正式PER/PBR、Android 15連続更新と無音通知。次回はCIの完走とAndroid失敗ジョブを確認し、同期・財務の実データ照合を優先。株価原本・APIキー・APKは公開していない。出典: [DoltHub](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC](https://www.sec.gov/edgar/sec-api-documentation)。

## 2026-11-19 03:16 JST — Dolt同期の入力異常時の安全停止を回帰テスト化

- 開始時main: [482dcf8](https://github.com/osawamas/value-hunter-ai/commit/482dcf8586a3f2f4ebfd51fc357e706feda691e4)。最新main、直近Actions、既存開発ログ、Dolt同期コードと既存テストを確認。全体開発のJPX変更とは重複しない。
- Dolt同期の再試行回数が0・負数・4回の場合、およびclone先の親ディレクトリがない場合に、外部コマンドを一度も呼ばず入力エラーで停止する回帰テスト2件を追加。[コード差分 0bc8fa5](https://github.com/osawamas/value-hunter-ai/commit/0bc8fa5bbc37f293a558a122286c19226bb23cf3)。既存の入力検査を明示的に固定するテストであり、本体コードの変更なし。
- ローカルGit接続はDNS解決エラーで失敗。追加したunittestは未実行、今回の変更後CIも未確認。前回までの[米国CI成功 44356701499](https://github.com/osawamas/value-hunter-ai/actions/runs/44356701499)は今回のテスト成功を意味しない。直近[Android CI失敗 44364251701](https://github.com/osawamas/value-hunter-ai/actions/runs/44364251701)はJPX関連コミットの実行で、原因は未調査。
- 対象取引日2026-11-17。今回の新規株価取得0件、NYSE/Nasdaqの新規網羅率測定なし。既存の照合4,958/5,085件は11月18日観測一覧との比較であり厳密な当日網羅率ではない。原データ・キー・APKは公開していない。
- 未解決: Dolt実同期と実429、正式終値・株式分割・SEC株数基準日の照合、正式PER/PBR判定、Android連続更新と無音通知。次回は新規テストのCI確認、Dolt実同期、Android失敗ログの調査を優先。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC](https://www.sec.gov/edgar/sec-api-documentation)。

## 2026-11-19 03:06 JST — 追加した米国株の終値を取引所資料で照合

- 財務・株数を照合済みの17銘柄のうち、利益と自己資本が正の5銘柄について、Nasdaqの公開履歴から同じ11月17日の終値を確認した。DoltHubの株式分割記録はタイムアウトし、株数基準日以降の区間を確認できなかった。
- SECのACCL年次報告では表紙の株数がClass AとClass Bの合計と分かった。上場株式との対応を確認するまで追加の通知対象には入れない。米国の通知可能数には前回確認済みの1,472銘柄を使用。

## 2026-11-19 02:45 JST — 外国発行体の米ドル年次報告を照合

- 米国取引所の普通株について、米ドル建てのUS-GAAP数値を載せた20-F・40-Fも利用できるようにした。普通株数、通期利益、親会社の自己資本を同一書類に照合し、開示日より後の終値に適用する。既存の10-K・10-Qの判定結果は保持する。
- SEC Company Factsの一括資料（20,597ファイル）とNYSE・Nasdaqの銘柄一覧を使用。従来「親会社自己資本なし」だった銘柄で条件を再確認し、ナスダックの17銘柄が株数・財務の照合を通過した。うち5銘柄は利益・自己資本が正。終値と分割記録の再取得はDoltHubの応答タイムアウトで未完了。通知可能数の集計は前回検証済みの1,472銘柄を維持した。
- 東証と共通のAndroid向けJVMテスト71件が成功。配布用APKは未作成。

## 2026-11-19 02:15 JST — Doltの429再試行中にキャッシュが消えた場合の安全停止

- 開始時main: [b0bd248](https://github.com/osawamas/value-hunter-ai/commit/b0bd248716fd2b0852c94a2ba0526669ccf10efb)。最新main、直近Actions、当ログ、Dolt同期コードとテストを確認。並行JPX実装は変更しない。
- 前回修正の[米国CI 44345265730](https://github.com/osawamas/value-hunter-ai/actions/runs/44345265730) は **success** と確認。直近[JPX CI 44347426281](https://github.com/osawamas/value-hunter-ai/actions/runs/44347426281) もsuccess（米国CIとは別）。
- 新たな競合条件を修正: HTTP 429の60秒待機中に既存Doltリポジトリの .dolt が消えると、次回の試行が既存ディレクトリへのcloneに変わる可能性があった。各試行前にメタデータを再検査し、破損時は invalid_repository_after_command で停止。既存ファイルは削除しない。[実装修正 f9820eb](https://github.com/osawamas/value-hunter-ai/commit/f9820eb0a28e89ed2ca8256984aa53e7fec0b31c)、[回帰テスト 77fa9ba](https://github.com/osawamas/value-hunter-ai/commit/77fa9bae0218f318a0422f2a8f3498f8247ce951)。
- ローカルでGit cloneしてunittestを実行しようとしたが github.com のDNS名前解決に失敗。今回追加テストと変更後Actionsは**未確認**。Dolt実同期も未実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日2026-11-17（既存データ）。今回新規株価0件、網羅率の再測定なし。既存記録はNYSE 1,877/1,896、Nasdaq 3,081/3,189（11月18日観測一覧との比較）、SEC財務照合2,746件。原株価・APIキー・APKは公開していない。
- 未解決: 新規CI完走、Dolt実同期、正規セッション未調整終値と分割前価格、株式クラス・株数基準日、正式PER/PBR、Android連続更新・無音通知。次回は新規CI結果とDolt同期を確認し、不可ならSEC照合へ。

## 2026-11-19 01:15 JST — Dolt初回タイムアウトのCI期待値を修正

- 開始時main: [d201026](https://github.com/osawamas/value-hunter-ai/commit/d201026be611506406ff96a3b7315ced784d74cd)。本ログ、同期実装、回帰テスト、米国CI設定と直近Actionsを読んだ。並行JPX開発には触れず。
- 同期実装は初回cloneがタイムアウトし、`.dolt` ディレクトリを残した場合に `partial_clone_requires_manual_cleanup` を返すが、既存の `test_timeout_initial_clone_not_retried` は旧値 `timed_out` を期待していた。実装の保護方針を維持してテスト期待値を修正し、部分メタデータの保存も明示的に検査。[修正コミット c799f0a](https://github.com/osawamas/value-hunter-ai/commit/c799f0af8275407d92949d09f3413b0ca628cc37)。
- 変更後[米国CI 44345265730](https://github.com/osawamas/value-hunter-ai/actions/runs/44345265730) は確認時点でqueued、成功未確認。変更前の[米国CI 44334278932](https://github.com/osawamas/value-hunter-ai/actions/runs/44334278932) は失敗。ローカルunittestとDolt実同期は未実施。直近[Android CI 44342640998](https://github.com/osawamas/value-hunter-ai/actions/runs/44342640998) は成功だが今回の変更以前の結果。
- 対象取引日2026-11-17（既存記録）。今回の新規取得0件、網羅率の再測定なし。既存値NYSE 1,877/1,896、Nasdaq 3,081/3,189（11月18日観測一覧基準）。SEC照合済みは最新既存記録で2,746件。原株価/APIキー/APKは公開せず。
- 未解決: 変更後CI、Dolt実同期、正規未調整終値・分割前価格、株式クラスと株数基準日、正式PER/PBR、Android連続更新・無音通知。次回はCI完走と失敗ログを確認し、Dolt不可ならSECの追加検証。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[SEC Company Facts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)。




## 2026-11-19 00:40 JST — 四半期利益と異なる決算期に対応

- 同じ利益指標で連続する4四半期を確認できる場合に直近12か月の利益を算出。最終四半期がない場合、期間の一致する通期と9か月累計の差を使う。11月17日の終値4,958銘柄で照合済み2,742→2,746銘柄、未照合2,212銘柄。既存の照合値は一致し、参考候補327件は同数。
- 積水ハウス、キヤノン、丸紅、オリックスの決算原本からEPS・BPS・期末株数を登録。11月17日のJPX日報で4銘柄の終値を確認。銘柄ごとの決算期末から権利落ち資料を照合する。JPX公式月報は1～9月分と日次Excel5本を検証、10・11月分は未掲載。

## 2026-11-19 00:29 JST — 普通株主帰属利益と日本株登録を拡張

- SEC財務の利益期間がそろわない場合に、普通株主帰属利益が同じ指標・期間・提出書類でそろうときの算出経路を追加。11月17日の終値4,958銘柄で全件を再集計し、照合済みは2,707→2,742銘柄（NYSE +15、Nasdaq +20）、参考候補は321→327件。以前の照合済み銘柄の株数・利益・純資産・提出番号は一致。
- 東証は三菱製紙（3864）、ENEOS（5020）、KDDI（9433）の通期決算原本からEPS、BPS、自己株式控除後の株数を登録。11月17日の日報に3銘柄の終値を確認。公式月報の3～9月分と日次Excel5本を再照合した。10・11月の月報は未掲載のため、資料不足の場合は通知を保留する。

## 2026-11-19 00:18 JST — Dolt初回clone中断時の不完全ディレクトリを保護

- 開始時main: [348b37a](https://github.com/osawamas/value-hunter-ai/commit/348b37a3d4d126fc60bf9a231a167f6d734c7edc)。最新main・本ログ・同期コード・テスト・[米国CI設定](https://github.com/osawamas/value-hunter-ai/blob/main/.github/workflows/us-daily-coverage-tests.yml)を読んだ。直近push Actionsの成否は取得できず、成功未確認。
- 初回Dolt cloneのTimeoutExpiredまたはOSErrorで不完全な保存先が残る場合、従来の timed_out / os_error ではなく partial_clone_requires_manual_cleanup と判定し、ファイルを削除せず保持する。[実装 a929075](https://github.com/osawamas/value-hunter-ai/commit/a929075f7aa04068c521b7c8ff6ad03846477bb3)、[回帰テスト fbd496d](https://github.com/osawamas/value-hunter-ai/commit/fbd496d81187a5b3cc87a3f8c092d3d45159b864)。並行するSEC/日本株コードには触れず。
- Pythonで初回cloneタイムアウトと不完全ディレクトリの判定条件を独立再現し1件成功。ただし追加したリポジトリ内unittestとActionsは未実行・未確認。Dolt実同期・実429は未実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日2026-11-17（既存保存データ）。今回新規終値取得0件、NYSE 1,877/1,896・Nasdaq 3,081/3,189は既存11月18日観測一覧との照合で今回の再測定ではない。SEC照合2,707件も既存記録で再測定なし。株価原本・APIキー・APKは公開していない。
- 未解決: 最新CI、Dolt実同期、正規未調整終値と分割前価格、企業イベント・株数基準日、正式PER/PBR、Android実機連続更新と無音通知。次回は追加テストのCI完走と中断clone復旧手順を検証し、Doltが不可ならSEC側のテストへ。






## 2026-11-19 00:09 JST — Android上でのSEC財務の差分更新

- SECの日次提出一覧を確認し、確定済みの財務を再利用する。提出あり・未照合・期末の古い銘柄を取り直す。一覧が欠ける場合や全件取得から7日以上経つ場合は全件を再取得する。途中まで取得した結果も、条件を満たす銘柄は次の取引日に引き継ぐ。
- 11月16・17日の日次提出一覧と、保存した終値・SEC財務の原本を再生。取得対象4,575銘柄のうち1,394銘柄で再取得を省略（30.5%削減）。再利用した値は全件取得の結果と一致し、財務照合済みは2,707銘柄。実機での連続運用時間は未測定。

## 2026-11-18 23:55 JST — Android単体の財務自動更新

- 運用にMac設定は不要。Androidで終値とSEC財務を取得し、為替・分割を照合して無音通知する。財務取得は従量制でない回線に接続中に実行し、同じ終値データでは途中から再開する。
- 11月17日分の保存データをAndroidと同じJava実装で再生。終値4,958銘柄のうちSEC取得対象4,575、財務・株数照合2,707、参考条件321で従来と一致。Android実機上での全件取得と連続更新は未検証。現在は取引日ごとに財務を取得する。

## 2026-11-18 23:30 JST — SEC照合保留の内訳と再同期

- 財務・株数などでまとめて保留していた1,448銘柄を再調査。同一提出書類に対応する株数が不足507件、親会社帰属の自己資本が不足475件、自己資本の基準日が古い150件、優先株式113件、比較に必要な利益情報が不足・不明197件、株数が不明確6件。
- 株数不足時の台帳に、次の原本照合に使う決算期末・提出日・提出種類・アクセッション番号を記録。株価キャッシュが同じでも財務照合コードが変わればMacから再同期する。同日版の再同期を新たな取引日とは扱わない。

## 2026-11-18 23:25 JST — SEC同一提出書類の株数・親会社帰属額を追加照合

- 連結貸借対照表の自己株式控除後の普通株数を、表紙の株数を取得できず、同じ提出書類・同じ期末の値を一意に確定できる場合に使用。連結合計と非支配持分が同じ提出書類・期間・単位で確認できる場合は、親会社帰属額を差し引いて計算する。財務台帳に株数の根拠と差引計算の有無を記録。
- 11月17日のDoltHub終値とSEC Company Facts原本を同じ入力で再生。終値4,958銘柄のうち照合済みは2,575→2,707銘柄（NYSE +70、Nasdaq +62）。以前の照合結果2,575件の株数・基準日・利益・自己資本・提出書類番号は一致。参考条件該当は312→321件。
- 未照合2,251銘柄。うち決算期間・株数等の確認待ち1,448件、複数上場クラス375件、US GAAP財務なし348件。分類別に次の取得経路を決める。Mac自動同期の実機運用は引き続き別途確認。

## 2026-11-18 23:19 JST — Dolt初回clone失敗時の不完全ディレクトリを保護

- 開始時main: [2037103](https://github.com/osawamas/value-hunter-ai/commit/2037103351fdfbc9e5bd0fc39bf981ff762b55ef)。既存ログ・同期実装・回帰テスト・[米国CI定義](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)を読んだ。直近のpush Actions結果は今回取得できず、前回記録の[米国CI成功44307602334](https://github.com/osawamas/value-hunter-ai/actions/runs/44307602334)のみ既知。
- Dolt初回cloneがHTTP 429等で失敗し、不完全なディレクトリが残ると、次回起動は既存非Doltディレクトリとして拒否される。破損キャッシュとして誤認せず、削除も自動実行しない専用結果 `partial_clone_requires_manual_cleanup` を追加。[同期実装 aedd71b](https://github.com/osawamas/value-hunter-ai/commit/aedd71bd1cc1aea10baaec4acaf56b595a0a79b2)、[テスト af83cb3](https://github.com/osawamas/value-hunter-ai/commit/af83cb3640f4c429ba0306e7b2d66b199da82206)、[既存期待値調整 67fc245](https://github.com/osawamas/value-hunter-ai/commit/67fc245fd82076d3f9ac9026a419e04322e211eb)。
- ローカルPythonで不完全ディレクトリのファイル保存条件を1件再現して成功。リポジトリの追加unittest実行と変更後Actionsは**未確認**。既存テストがCIで成功するまで修正完了とは断定しない。株価原本・APIキー・APKは公開していない。
- 対象取引日2026-11-17。今回の新規終値取得0件。既存22:27の報告値はNYSE 1,877/1,896、Nasdaq 3,081/3,189（11月18日観測一覧との照合であり17日当日の厳密網羅率ではない）。SEC財務照合2,575件は既存報告で、今回の再測定ではない。
- 未解決: Dolt実同期と実429、正規終値・分割前価格・株数基準日の厳密照合、正式通知、Android連続更新と無音通知。次回は[米国CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)で新規テストを確認し、不完全cloneからの安全な復旧手順を検証。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。

## 2026-11-18 22:27 JST — NYSE・Nasdaq全候補の終値監視とSEC一括照合

- 11月18日08:16米東部のNasdaq Trader一覧を11月17日取引分のDoltHub終値と照合。NYSE 1,877 / 1,896、Nasdaq 3,081 / 3,189、合計4,958 / 5,085。Androidの定期処理からも同じ公開一覧を読み、取引日の終値取得件数・不足数・一覧日を表示する。JVMで原本を再生し同じ件数を確認。
- SEC公開のCompany Facts一括ZIP（約1.43 GB）を使い、Androidと同じ決算期間・株数基準日の照合を4,958銘柄に実施。SEC発行体は4,950件に一致し、2,575銘柄（NYSE 866、Nasdaq 1,709）は終値・純利益・親会社自己資本・株数が揃った。2,383銘柄は財務等の照合を保留し、理由を台帳に記録した。先頭ゼロで埋めた文字列CIKにも対応。別の発行体のデータは保留した。
- 株価・為替・既知の分割記録を参照したPC一括判定は、優先候補119件、参考候補193件。正式通知には未接続。全銘柄のSEC台帳はPCで生成し、本人用Androidビルドで同じ基準日の照合件数を表示できる。別日の財務自動更新、照合保留の解消と正式通知が残っている。
- 原本の終値や生成済み台帳はGitHubに含めていない。

## 2026-11-18 22:17 JST — 米国CI成功と429判定の独立再検証

- 開始時main: [8973e0e](https://github.com/osawamas/value-hunter-ai/commit/8973e0ed77ffb60033c6c0a1d4d4382592aa070a)。最新main・本ログ・Dolt同期コード・直近Actionsを確認。22:16 JSTまでの並行米国開発（6銘柄60か月参考レンジ、11月17日終値12,604件、NYSE 1,877/1,896・Nasdaq 3,081/3,189、6銘柄SEC照合）を確認し、重複するコード変更を避けた。
- [米国CI 44307602334](https://github.com/osawamas/value-hunter-ai/actions/runs/44307602334) は成功。直近[Android private preview 44312116889](https://github.com/osawamas/value-hunter-ai/actions/runs/44312116889) は確認時点で実行中、[ZIP 44312117027](https://github.com/osawamas/value-hunter-ai/actions/runs/44312117027) は成功。これらを実機の連続更新成功とは扱わない。
- [Dolt同期コード](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py) の429正規表現をPython 3で独立再現し、HTTP 429・status=429・Too Many Requests・429A・X429・4290・1429・HTTP 429; retryの8条件を実行、8/8成功。リポジトリのテスト実行や実際のDolt接続ではない。コード変更なし、今回の差分はこのログのみ。
- 対象取引日: 2026-11-17（米国）。既存ログ上の取得12,604件、普通株ラベル照合NYSE 1,877/1,896・Nasdaq 3,081/3,189（観測日11月18日、当日確定網羅率ではない）。今回の新規取得0件。原データ/APIキー/APKは公開していない。
- 未解決: DoltローカルDBの実同期と429実測、正規セッション終値・全銘柄の分割前価格とSEC株数基準日照合、正式判定、Android実機連続更新と無音通知。次回はAndroid Actionsの完走確認、実同期と市場別照合の再測定、SECの基準日・株式クラス検証へ。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[米国CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。

## 2026-11-18 22:16 JST — 米国株6銘柄に過去5年の参考レンジを追加

- DoltHubの日付インデックスに合わせ、月末側3平日の正の終値を12か月単位で取得し、月ごとに最後に取得できた日を選ぶ。2021年11月〜2026年10月の60か月が6銘柄すべてで揃った。最初の5区間のうち1区間はタイムアウトし、再取得で補完した。
- Androidの定期更新から月単位で集計する。タイムアウト時は取得済み区間を次回に使い、日次終値・SEC照合の結果は先に保持する。60か月未満と分割記録のある銘柄はレンジ保留。現段階は価格の参考表示で、企業行動を全面調整したリターンや正式通知の判定根拠には使わない。
- SEC開示処理および履歴の欠損、分割、重複処理のJVMテストを通過。既存のアプリ定期更新が実機のバックグラウンドで複数回動く確認は残っている。

## 2026-11-18 22:12 JST — 米国株6銘柄の参考バリュエーションをAndroidに接続

- IBM、AAPL、HPQ、AMD、INTC、GMのSEC Company Factsを実取得。株数と親会社自己資本を同じ10-K/10-Qに結び付け、利益は直近の通期決算、または直近通期＋今期累計−前年同期累計で算出。公表日と同日の終値には開示を適用しない。
- 11月16日・17日分のDoltHub終値、FrankfurterのUSD/JPY、SEC開示をコードに通し、両日とも6銘柄の照合が通った。17日分では4銘柄でPER・PBRの両方を計算、HPQは自己資本が負、INTCは直近12か月赤字。2日とも試験範囲で条件該当は0件。
- Androidの定期更新で暫定時価総額・PER・PBR・円換算額と保留理由を表示する。円換算は10万円以下なら100株を優先し、超える場合は1株で判定。株数の基準日以降にDoltHubの分割情報があれば保留、取得エラーは次回更新で再試行。参考価格から正式ランキングや通知は発行しない。
- 実機での連続更新、銘柄の大幅拡張、終値・株数の厳密な当日基準照合、正式通知の接続が残っている。

## 2026-11-18 21:44 JST — キー不要のDoltHub日次終値をAndroidの既定に接続

- DoltHubの公開SQLが再試行でHTTP 200。1リクエスト1,000行の上限を確認し、リビジョンを `AS OF` で固定して全ページを取得。11月16日は12,639件、17日は12,604件。日付と正の終値、銘柄の重複なし、先頭の件数との一致を両日で確認した。
- 11月18日07:00米東部のNasdaq Trader一覧との普通株ラベル照合では、11月16日分はNYSE本市場1,875 / 1,896とNasdaq 3,101 / 3,189。17日分はNYSE本市場1,877 / 1,896とNasdaq 3,081 / 3,189（合計4,958 / 5,085）。一覧の観測日は価格日より後なので、当日確定のカバレッジではない。
- Androidは無料・キー不要のDoltHubを既定入力にする。定期更新は同一リビジョンの全ページ取得を検証後、端末内の最新1日分だけを差し替える。DoltHubの価格を画面で参考値と明記し、アプリのキャッシュを既存のSEC照合に入力できるようにした。Massiveはキーを指定してビルドした場合に選択できる。
- 同じ2日分の取得キャッシュを、今回の入力経路から実際のSEC発行体一覧と照合。普通株ラベルのうち16日分はNYSE 1,874件とNasdaq 3,094件、17日分はNYSE 1,876件とNasdaq 3,074件で、終値・銘柄・発行体が一致した。財務数値・株数までの全銘柄照合件数とは区別する。
- 株式分割があったAppleの前後価格は未調整と整合するが、全市場の価格基準は未確定。端末での複数回更新、銘柄別の取引日時点株数、公式終値との一致および割安通知は別途検証する。

## 2026-11-18 21:38 JST — 米国株の終値をAndroidの定期取得に接続

- Massive Stocks Basicの公式仕様で、米東部の日付が変わった後に日別一括データを取得できること、無料枠が毎分5回であることを確認。APIの接続先はキーなしでHTTP 401。DoltHubの公開SQLはこの環境からタイムアウト。認証済み実データによる複数取引日の検証と普通株の実測網羅率は未確認。
- Androidの初回起動から6時間間隔で定期取得を登録。前日以前の未調整終値を端末内に保存する。画面に米東部の取得日と受理した件数を表示し、通信失敗時は直前の成功データを保持する。無料キーはPC上のローカルファイルから本人用APKをビルドする際に渡せる。
- SEC Company FactsのAppleをHTTP 200で取得。2026年11月3日提出の10-Kに株数の基準日10月23日、純利益と純資産の決算期末9月26日を確認。Androidのキャッシュを、既存の銘柄・SEC発行体・財務・株数の照合に渡せるようにした。キャッシュとSEC銘柄一覧の接続は合成データで回帰テストを実施。Pythonは26件成功。実配信の終値、取引日時点の株数、Android通知の実機検証は今後の作業。
- 無料キー取得後はローカルの市場カバレッジ測定を複数日実施し、Androidで2回以上の更新を確認する。財務と株数は基準日と株式クラスを維持し、終値と照合する。

## 2026-11-18 21:12 JST — Dolt 429の英数字識別子誤検出を修正

- 開始時main: [b4f9737](https://github.com/osawamas/value-hunter-ai/commit/b4f97376570425ca10012d9d1e9ffdc92ab2971e)。既存ログ、同期コード、テスト、[米国CI定義](https://github.com/osawamas/value-hunter-ai/blob/main/.github/workflows/us-daily-coverage-tests.yml)を読んだ。日本株の並行変更は編集していない。
- 既存正規表現は 429A / X429 までHTTP 429と誤判定する。英数字に埋まった429を除外する[同期コード修正 68d549d](https://github.com/osawamas/value-hunter-ai/commit/68d549d4f612bf6c83f8e06471e81d64f57801eb)と[回帰テスト bfadee8](https://github.com/osawamas/value-hunter-ai/commit/bfadee844b1b5da90da833c0c6d3b0c150fba9a0)をmainに保存。
- ローカルPythonで新正規表現の7条件を実行し7/7成功。旧実装では429A / X429の誤検出を再現。既存判定の独立8条件も8/8成功。ただしリポジトリのunittestと変更後GitHub Actionsの結果は未確認。[米国CI一覧](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)は今回取得できず、前回の既知成功は[44265403943](https://github.com/osawamas/value-hunter-ai/actions/runs/44265403943)。
- ローカルGit接続はgithub.comのDNS解決失敗。GitHubコネクタでコード・テストは保存済み。Dolt実同期・429実測・キャッシュDB検査は未実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日: 2026-11-17（米国）。新規終値取得0件、NYSE/Nasdaqの同日網羅率未測定。正規セッション終値・分割前価格・SEC株数・正式PER/PBR・Android更新/無音通知は未完了。株価原本/APIキー/APKは公開していない。
- 次回: 今回の回帰テストのCI成否を確認し、Dolt実同期と市場別日付付き網羅率を優先。接続不可なら公開ファイル・SEC側の実装とテストを進める。

## 2026-11-18 20:11 JST — Dolt 429の単回試行・キャッシュ保持テスト追加

- 開始時main: [c3600a7](https://github.com/osawamas/value-hunter-ai/commit/c3600a78cb9d739df4d0a712aaf7f2bf00e91b38)。最新コミット・既存米国ログ・Dolt同期実装とテストを取得。直近の米国CIの既知成功は [44265403943](https://github.com/osawamas/value-hunter-ai/actions/runs/44265403943)（前回記録）。今回の最新コミットに紐づくPR起動Actions照会は0件で、push CIの新しい成否は未確認。
- Dolt既存キャッシュでHTTP 429、attempts=1の際に待機・再試行をせず、既存マーカーを保持してcached_after_rate_limitを返す回帰テストを追加。[テスト変更 c6e0b11](https://github.com/osawamas/value-hunter-ai/commit/c6e0b11845421b45befe7853d458bd323766aebf)。既存同期コード・日本株側は変更なし。追加テスト自体のPython実行・Actions成功は未確認。
- 出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[同期コード](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py)、[米国CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。Dolt実同期・実際の429応答・キャッシュDB完全性は未検証。
- 対象取引日: 2026-11-17（米国）。新規終値取得0件、NYSE/Nasdaqの同日網羅率未測定。正規セッション終値・分割前価格・SEC株数・企業イベント・正式PER/PBR・Android更新/無音通知は未完了。株価原本・APIキー・APKは公開していない。
- 次回: push CIの追加テスト結果を確認し、Dolt実同期と市場別日付付き網羅率の測定へ進む。Doltが不可なら公開ファイル・SEC照合の実装とテストを進める。

## 2026-11-18 19:19 JST — 米国CI成功を確認、Dolt 429標準出力と4290誤判定の回帰テストを追加

- 開始時main: [bf451e7](https://github.com/osawamas/value-hunter-ai/commit/bf451e701e0dd1a6864e6462292074f163d51f44)。最新main、既存米国開発ログ、Dolt同期コード・テスト、直近Actionsを読んだ。米国株CI [44265403943](https://github.com/osawamas/value-hunter-ai/actions/runs/44265403943) は成功（以前の構文エラー修正後）。直近ZIP Actions [44274309845](https://github.com/osawamas/value-hunter-ai/actions/runs/44274309845) も成功。ただし今回の追加テストに対するCI結果ではない。
- 既存のDolt同期テストに、HTTP 429が標準出力だけに現れる場合のキャッシュ保護・60秒待機・2回試行、および無関係な4290を再試行しないケースを追加。[コード/テスト変更 3e3d6b2](https://github.com/osawamas/value-hunter-ai/commit/3e3d6b267d00662f8e7cbc35b757409103d3f6ea)。追加テスト自体の実行・新CI結果は未確認。日本株の並行コードは変更なし。
- 出典: [DoltHub公開stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[同期実装](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py)、[米国CI](https://github.com/osawamas/value-hunter-ai/actions/workflows/us-daily-coverage-tests.yml)。Dolt実接続、HTTP 429実測、ローカルキャッシュ実体検査は未実施。
- 対象取引日: 2026-11-17（米国）。今回の新規株価取得0件。NYSE/Nasdaqの同日網羅率は未測定。正規セッション終値・分割前価格・SEC株数と企業イベント照合・正式PER/PBR・Android無音通知は未完了。株価原本・APIキー・APKの公開なし。
- 次回: 新CIで追加テストの成否を確認し、可能な環境でDolt実同期、NYSE/Nasdaq市場別の同一日付付き網羅率を測定。取得できない場合はSEC・公開ファイル側の実装と検証を進める。

## 2026-11-18 18:15 JST — Dolt 429判定を独立再現、実同期は環境制約で保留

- 開始時main: [f0cd8dd](https://github.com/osawamas/value-hunter-ai/commit/f0cd8dd3814b485bd61cae4d6ab5e775e52a43c2)。最新main、既存米国ログ、[米国株CI設定](https://github.com/osawamas/value-hunter-ai/blob/main/.github/workflows/us-daily-coverage-tests.yml)、[直近既知の米国CI 44258042386](https://github.com/osawamas/value-hunter-ai/actions/runs/44258042386)（失敗）、Dolt同期実装とテストを確認。今回の新しいpush Actions成否は未確認。日本株側の並行コミットには触れない。
- DoltのRATE_LIMIT正規表現をローカルPythonで独立再現。HTTP 429 / Too Many Requests / 1429 / 4290 / status=429 / status 429 の6条件すべて期待通り（6/6）。ただし実リポジトリのテストではないため全テスト成功とは扱わない。今回コード変更なし（既存判定が再現で正しく、重複修正を避けた）。変更箇所はこのログのみ。
- 実行環境の git ls-remote は github.com のDNS解決に失敗。GitHubコネクタによるソース読取とログ書込は利用可能。Dolt実同期、HTTP 429実測、キャッシュ実体の検証は未実施。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)、[同期コード](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py)。
- 対象取引日: 2026-11-17（米国）。今回の新規株価取得0件、NYSE/Nasdaq市場別の同日網羅率は未測定。正規セッション終値・分割前価格・SEC株数・PER/PBR・Android無音通知は未検証。株価原本・APIキー・APKの公開なし。
- 次回: [Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)で修正後の米国株CI完走を確認し、可能な環境でDolt同期・同一取引日の市場別網羅率を測定。CI失敗なら実ログに沿って修正する。

## 2026-11-18 17:15 JST — 米国株CIのSyntaxErrorを修正

- 開始時main: [405675b](https://github.com/osawamas/value-hunter-ai/commit/405675b100ee386b7a73a5eed0548ad438d8a3da)。最新main、既存米国ログ、[直近Actions 44263420532](https://github.com/osawamas/value-hunter-ai/actions/runs/44263420532)（JPX成功）と[米国株CI 44258042386](https://github.com/osawamas/value-hunter-ai/actions/runs/44258042386)（失敗）を確認。JPX並行更新には触れない。
- 米国CIの実ログから、前回のNasdaqテスト期待値修正でPythonコードに文字列としての `\\n` が混入し、97行目がSyntaxErrorとなってテスト収集自体が止まったことを特定。該当箇所を実際の改行に置換して[修正 f928afe](https://github.com/osawamas/value-hunter-ai/commit/f928afe453134d20929f344fc4d536f2c40605b7)を保存。独立したPython構文再現は成功。修正したリポジトリのテスト実行と修正後CIは未確認で、全件成功とはしない。
- 対象取引日: 2026-11-17（米国市場）。今回の実株価取得0件、NYSE/Nasdaq同日網羅率未測定。参照: [GitHub Actionsログ](https://github.com/osawamas/value-hunter-ai/actions/runs/44258042386)、[DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。株価原本・APIキー・APKの公開なし。
- 未解決: 修正後CIの成功、Dolt実同期・429実測・ローカルキャッシュ、正規未調整終値・株式分割・SEC株数照合、PER/PBR、Android無音通知。次回はCI結果と失敗箇所を確認し、Dolt実同期および市場別日付付き網羅率へ進む。

## 2026-11-18 16:19 JST — Dolt回帰テストを米国株CIに組み込み

- 開始時main: [5dd023d](https://github.com/osawamas/value-hunter-ai/commit/5dd023d551a9e255cad4c5959f0630f1f7252607)。既存米国ログ、Dolt同期コードと19件の既存テスト、[直近Actions 44252477996](https://github.com/osawamas/value-hunter-ai/actions/runs/44252477996)（JPX関連、成功）を確認。並行JPX変更は触らず。
- 従来の[米国株CI](https://github.com/osawamas/value-hunter-ai/blob/main/.github/workflows/us-daily-coverage-tests.yml)はDolt同期テストを実行せず、429再試行・キャッシュ消失の追加回帰テストがCIで未検証だった。ワークフローに `test_us_dolt_sync` を追加し、Doltコード/テスト変更時にも自動起動するよう[変更 9bdaae2](https://github.com/osawamas/value-hunter-ai/commit/9bdaae23cf23ed7cd55c8e170077f37ea67bec97)。外部DBへのアクセス、株価原本/APIキー/APKの公開はなし。
- [今回の米国株CI 44257980299](https://github.com/osawamas/value-hunter-ai/actions/runs/44257980299) は確認時点でqueued。**テスト成功は未確認**。対象取引日: 今回の新規株価取得なし（0件）。NYSE/Nasdaqの2026-11-17同日網羅率未測定。参照: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 16:20 JST追記: [CI 44257980299](https://github.com/osawamas/value-hunter-ai/actions/runs/44257980299) は **79件実行・3件失敗**。失敗はNasdaqセッション終了後の重複通知を正しく拒否した際、古いテストが別のエラー文言を要求していたため。実装は変えずテスト期待値を両方の拒否文言に合わせて[修正 007f85e](https://github.com/osawamas/value-hunter-ai/commit/007f85ead024ec1d4a39b9d016d75dff273948e4)。修正後CI結果は未確認。Dolt実データの取得や同期成功を意味しない。
- 未解決: CIの完走確認、Dolt実同期と429実測、未調整終値・株式分割・SEC株数照合、正式PER/PBR、Android更新・無音通知。次回はCI結果を読み、失敗なら修正し、実同期と市場別網羅率を測定する。

## 2026-11-18 15:18 JST — Dolt起動OSエラー後のキャッシュ消失を検出

- 開始時main: [12407a5](https://github.com/osawamas/value-hunter-ai/commit/12407a5e7585b229d111ba1922cb6051dc770fb0)。最新main・既存米国ログ・Dolt同期コードとテスト・[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)を確認。前回のtimeout/429とは別のOS例外分岐を修正し、JP並行開発には触れない。
- 既存pullのrunnerがPermissionErrorなどのOSErrorを出す際に .dolt が消失しても cached_after_os_error と誤判定する問題を修正。[実装 ceb4a79](https://github.com/osawamas/value-hunter-ai/commit/ceb4a79a17e81ebb20f0efaf3772294128f23d14)、[回帰テスト ad9fb7d](https://github.com/osawamas/value-hunter-ai/commit/ad9fb7d7aa0ecdee59ee49fe11ad1ece241de965)。消失時は invalid_repository_after_command とする。
- ローカルPythonで同条件の独立した分岐再現2/2成功（リポジトリのテスト自体ではない）。ローカルgit ls-remoteはDNS解決失敗。Dolt実接続、追加テスト実行、米国株Python全テスト、変更後Actions成功は未確認。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日: 今回新規取得なし（0件）、NYSE/Nasdaq同日網羅率未測定。未調整終値・分割前価格・SEC株数・PER/PBR・Android無音通知は未検証。株価原本・APIキー・APKの公開なし。次回は新規回帰テストのCI実行とDolt実同期、NYSE/Nasdaqの日付付き網羅率を優先。


## 2026-11-18 15:15 JST — Dolt pullタイムアウト後のキャッシュ消失を誤認しない

- 開始時main: [f5a290e](https://github.com/osawamas/value-hunter-ai/commit/f5a290e42ad5ba16f8182cd8f5fc14f16bac3a5d)。直近[JPX Actions 44247823835](https://github.com/osawamas/value-hunter-ai/actions/runs/44247823835)は成功。ただし米国株Pythonテストではない。既存米国開発ログ・Dolt同期コード・テストを読んでJP側とは重複しない障害処理を選択。
- 既存pullがタイムアウトした際に .dolt が消失しても cached_after_timeout と返す問題を修正。[コード 140bd59](https://github.com/osawamas/value-hunter-ai/commit/140bd594253c2c4c9b1041d11e016983c37d9010)、[回帰テスト d707791](https://github.com/osawamas/value-hunter-ai/commit/d70779136a4e322b2672a4eadc27ecd41ee15507)。消失時は invalid_repository_after_command とし、再試行や削除はしない。
- GitHubへのコード・テスト保存は成功。ローカルgit ls-remoteはDNS解決失敗。追加テスト・全Pythonテスト・新コミットActions・Dolt実同期は未実行/未確認。出典: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日: 今回の新規照会なし。取得0件、NYSE/Nasdaq同日網羅率未測定。株価原本・APIキー・APKの公開なし。未解決: キャッシュ実体の検査、429実測、正規終値・分割、SEC株数、正式PER/PBR、Android更新・無音通知。次回は追加テストの実行経路を確保し、Dolt実同期・市場別取得率へ進む。

## 2026-11-18 14:13 JST — Dolt失敗時にキャッシュ消失を誤認しない

- 開始時main: [b0149c1](https://github.com/osawamas/value-hunter-ai/commit/b0149c158229c011a61255d4fbb9e052b0e68909)。直近コミットのPR紐付けActions照会は0件。通常push Actionsの成否は未確認（[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)）。既存ログとDolt同期・テストを読み、並行JP開発とは別の障害処理を選択。
- Dolt pullがHTTP 429で失敗し、同時に既存の .dolt ディレクトリも消えた場合、従来は cached_after_rate_limit と誤判定し得た。失敗直後に .dolt の存在を再検査して invalid_repository_after_command とする[コード変更](https://github.com/osawamas/value-hunter-ai/commit/78668ad7dfb29b7663b779f9c18287d4fde2257b)と[回帰テスト](https://github.com/osawamas/value-hunter-ai/commit/c7c12a2f04bab1cc9f9708c88730a8c3a36ebc70)を保存。参照: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 独立Python最小再現1件成功。GitHub上の追加テストそのもの・全テスト・Actionsは未実行/未確認。ローカルgit ls-remoteはDNS解決失敗。Dolt実同期も未実施。
- 対象取引日: 新規照会なし。終値取得0件、NYSE/Nasdaqの同日網羅率未測定。株価原本・APIキー・APKは公開していない。未解決: キャッシュの実データ完全性、429実測、正規終値・分割、SEC株数、PER/PBR、Android通知。次回は追加テストの実行確認と実同期・市場別日付付き取得率を優先。

## 2026-11-18 13:13 JST — Dolt 429が3回続く場合のキャッシュ保護テスト追加

- 開始時main: [5196e0d](https://github.com/osawamas/value-hunter-ai/commit/5196e0db4b9324b014a8028f2bde0f2687c741bd)。直近の[Android Actions 44227434927](https://github.com/osawamas/value-hunter-ai/actions/runs/44227434927)は前回ログで成功と記録されているが、今回のActions一覧・新コミットのCI結果は未確認。既存ログ・Dolt同期コード・テストを読み、JP側と重複しない変更を選択。
- [回帰テスト追加 18ebd23](https://github.com/osawamas/value-hunter-ai/commit/18ebd23226d0795462a8a59e250751b3176dc3f1)。Dolt pullの標準出力に429が3回連続で出た場合、待機60秒・120秒、再試行計3回、既存ローカルキャッシュ保持、結果cached_after_rate_limitを検査。同期コード自体は変更なし。参考: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- GitHubへテスト保存済み。ローカルgit ls-remoteはDNS解決失敗。追加したPythonテスト、リポジトリ全テスト、Dolt実同期、新コミットのActionsは未実行・未確認で成功とは扱わない。[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)。
- 対象取引日: 新規照会なし。今回の終値取得0件、NYSE/Nasdaq同日網羅率未測定。株価原本・APIキー・APKの公開なし。未解決: Dolt実同期、正規終値と分割、SEC株数、PER/PBR、Android無音通知。次回はCIで新テストを実行し、Doltの実同期または代替公開ファイルによる日付付き網羅率を測定。

## 2026-11-18 12:16 JST — Dolt 429後の復帰を回帰テスト化

- 開始時main: [b8b1dc6](https://github.com/osawamas/value-hunter-ai/commit/b8b1dc67f6237df12ca02df939471b7fa98b84f8)。直近[Android Actions 44227434927](https://github.com/osawamas/value-hunter-ai/actions/runs/44227434927)は成功（今回のPythonテストではない）。既存米国ログとDolt同期コード・テストを読み、並行JP開発と重複しない変更を選択。
- [回帰テスト追加 b81242f](https://github.com/osawamas/value-hunter-ai/commit/b81242f3c01baafbc5e0b305bf448df03d2c965e)。429が2回続いた後の3回目成功、待機60秒・120秒、キャッシュ保持、pull継続を検証する条件。
- 既存sync関数と同一ロジックを抜粋した独立Python再現1件は成功。リポジトリ全テストと追加テスト自体の実行、変更後Actionsは未確認。git ls-remoteはDNS解決失敗。実Dolt接続・日次同期は未実施。参考: [DoltHub stocks](https://www.dolthub.com/repositories/post-no-preference/stocks)。
- 対象取引日: 新規照会なし。取得0件、NYSE/Nasdaq同日網羅率未測定。価格原本・APIキー・APKの公開なし。未解決: Dolt実同期、正規終値・分割前価格、SEC株数、正式PER/PBR、Android無音通知。次回は追加テストのCI実行確認とDolt実同期、市場別同日網羅率検証。

## 2026-11-18 11:12 JST — MoldUDP64ハートビートの境界回帰テストを追加

- 開始時main: [09eb1ee](https://github.com/osawamas/value-hunter-ai/commit/09eb1ee6728d4a04b7f550e34520df24dd85d7ce)。最新ログとNasdaq解析コード・テストを読んだ。直近コミットのPR紐付けActions照会は0件（push Actionsの成功は未確認、[一覧](https://github.com/osawamas/value-hunter-ai/actions)）。JPX並行開発と重複しないNLS境界テストを選択。
- MoldUDP64のハートビート（件数0xFFFF）を空メッセージとして受理し、末尾に1バイト余剰があれば拒否する2条件をPythonで独立再現し2/2成功。既存関数の抜粋による再現であり、リポジトリ全体のテストではない。参照: [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)。
- [テスト追加](https://github.com/osawamas/value-hunter-ai/commit/f3aff902b16543c7610187ee8f26af679be8c635)、[入力1バイトの明示修正](https://github.com/osawamas/value-hunter-ai/commit/97c7b9b536e1701a288f97a2bedf685e886e2fd9)。実装コード変更なし。追加テストのリポジトリ内実行・Actionsは未確認。
- 対象取引日の新規株価取得0件、NYSE/Nasdaq同日網羅率未測定。価格原本・APIキー・APKの公開なし。未解決: Dolt日次同期と429キャッシュ、正規終値・分割、SEC株数、正式PER/PBR、Android更新・無音通知。次回はテスト実行経路を確保し、Dolt同期と同日網羅率を優先。

## 2026-11-18 10:16 JST — MoldUDP64境界検査を最小再現で再検証

- 開始時main: [3e1047e](https://github.com/osawamas/value-hunter-ai/commit/3e1047e9ef2bd281d1146fdf6c1e80c9a2c17690)。[開発ログ](https://github.com/osawamas/value-hunter-ai/blob/main/docs/us-market-development-log.md)と `android-private/tools/us_nasdaq_nls_probe.py`、既存テストを読んだ。直近コミットのPR紐付けActions照会は0件で、pushの実行状況は未確認（[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)）。JP市場の並行コミットには触れない。
- 既存 `mold_messages` の境界条件をPython 3の最小再現で実行。正常1メッセージ、長さヘッダー欠落、件数0で余剰バイト、長さ0の4ケースすべて想定どおり（4/4）。これは既存関数を抜粋した再現で、リポジトリ全テストの成功を意味しない。参照: [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)。
- 変更箇所: この開発ログのみ。新しいコード差分なし（既存の境界検査が再現で期待どおりだったため）。git cloneはDNS解決失敗で、実リポジトリをローカル実行できなかった。対象取引日の新規取得0件、NYSE/Nasdaqの同日網羅率未測定。株価原本・APIキー・APKは公開していない。
- 未解決: GitHub上のPython全テスト・push Actions、Doltの日次実同期と429キャッシュ、当日未調整終値・分割、SEC株数、Android更新・無音通知。次回は全テストの実行経路を確保し、Doltの実同期または代替公開ファイルの当日件数照合へ進む。

## 2026-11-18 09:19 JST — NLS Plusの不正なシステム通知長を拒否

- 開始時main: [5cb54ec](https://github.com/osawamas/value-hunter-ai/commit/5cb54ec89fc588d1e0810ca455066058cdc7d533)。直近コミットのActionsを照会したが、コミット紐付けのPR実行は0件（通常pushの実行状況は未確認、[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)）。既存ログ・NLSコードとテストを読んで、並行JPX更新と重ならない入力検証を選択。
- [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)の10バイトのシステム通知に対し、開始後に長さ12の不正なSレコードが挿入されても従来は無視されていた。長さ不正を明示的に拒否する[コード変更](https://github.com/osawamas/value-hunter-ai/commit/764829be3cbc254f2da63c3db36fcd887c1f7dae)と[回帰テスト](https://github.com/osawamas/value-hunter-ai/commit/9d4596e3149771b577d6428eb5c035c0187b95e3)を追加。
- 同条件の最小Python再現を実行し、不正長ではValueError、正規O/Cでは成功を確認。リポジトリ全体のPythonテストと新コミットのActionsは未実行・未確認。対象取引日は新規なし、今回の株価取得0件、NYSE/Nasdaqの同日網羅率は未測定。価格原本・APIキー・APKの追加なし。
- 未解決: 回帰テスト全件、Dolt実同期・429時キャッシュの実測、正規セッション未調整終値と分割前価格、SEC株数、Android更新・無音通知。次回は新コミットのテストを実行し、Doltと市場別同日網羅率の検証を優先。

## 2026-11-18 08:10 JST — NLS Plus開始前の価格レコードを拒否

- 開始時main: [de375f3](https://github.com/osawamas/value-hunter-ai/commit/de375f3434e1d64474eac3f8e6de7b45153b2edf)。直近Actionsの今回変更に対する実行結果は未確認（[一覧](https://github.com/osawamas/value-hunter-ai/actions)）。前回ログと既存コードを読み、並行するJPX/Android更新と重複しないNLS Plusの入力検証を選択。
- [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)のセッション境界に沿い、開始通知Oより前に日次サマリーや不明なシステム通知が現れた場合を拒否。[コード変更 e29f3cc](https://github.com/osawamas/value-hunter-ai/commit/e29f3cc31c4fabdaa9f86ba59ddbfcf02ede8b81)、[回帰テスト追加 b9fea8a](https://github.com/osawamas/value-hunter-ai/commit/b9fea8a413194bb470060960d2f84522f1a70523)。開始前のサマリー、未知イベント、開始通知欠落の3ケースを追加。
- Pythonテストは今回未実行。新コミットのActions結果も未確認のため成功判定はしない。対象実測参照日2021-06-14のNOCP 4,605銘柄は過去ログからの参考値。今回の新規株価取得0件。2026-11-17のNYSE/Nasdaq同日網羅率は未測定。
- 未解決: Dolt日次同期の実測・429キャッシュ、未調整終値と株式分割、SEC株数、Android端末更新・無音通知。次回はPython回帰テストとActionsを実行・確認し、Dolt同期と同日上場一覧の網羅率検証へ戻る。株価原本・APIキー・APKは追加していない。

## 2026-11-18 07:18 JST — NLS Plus終了後の余剰レコードを拒否

- 開始時main: [c6046c6](https://github.com/osawamas/value-hunter-ai/commit/c6046c613ccfae6a14a1ff4c33ac5ffa1144f09f)。直近Actions [44188565771](https://github.com/osawamas/value-hunter-ai/actions/runs/44188565771)、[44188565705](https://github.com/osawamas/value-hunter-ai/actions/runs/44188565705)、[44188565596](https://github.com/osawamas/value-hunter-ai/actions/runs/44188565596) は成功。ただし今回の変更のテスト結果ではない。
- [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)に基づくセッション境界検査を追加。従来はO,Cの後に通常レコードが続いても終了マーカーの列がO,Cなら受理した。終了後の余剰データ（集計・システムレコード）を拒否する変更と回帰テスト3ケースを追加。
- GitHubへの保存対象: `android-private/tools/us_nasdaq_nls_probe.py`、`android-private/tools/test_us_nasdaq_nls_probe.py`、このログ。今回のPythonテストと新コミットのActionsは未実行・未確認。ローカルgit cloneはDNS解決失敗。成功と判定しない。
- 対象実測参照日2021-06-14のNOCP 4,605銘柄を維持。今回の新規終値取得0件。2026-11-17のNYSE/Nasdaq同日網羅率は未測定。Dolt日次同期、分割前終値・SEC株数、Android実機相当更新・無音通知は未完了。株価原本・APIキー・APKは追加していない。
- 次回: 新コミットのActionsでテストを実行・確認。Dolt同期と429キャッシュの実測、当日上場一覧との照合へ戻る。

## 2026-11-18 06:15 JST — NLS Plusセッション境界の異常を拒否

- 開始時main: [e46ce00](https://github.com/osawamas/value-hunter-ai/commit/e46ce00543f3c0552493405cbcc002009f36f6df)。直近の[GitHub Actions実行44167378934](https://github.com/osawamas/value-hunter-ai/actions/runs/44167378934)は成功（ZIP browser workflow）。米国株のPythonテストの成功を意味するものではない。
- [Nasdaq NLS Plus仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)を参照し、セッション開始O・終了Cを一度ずつ正しい順序で受け取る条件を厳密化。従来はO,C,CやO,C,O,Cを正常終了として許容していた。[修正](https://github.com/osawamas/value-hunter-ai/commit/f2a5f4602649eef0825bcbc949aa0047956ee318)・[回帰テスト](https://github.com/osawamas/value-hunter-ai/commit/f5a408436ad5eebefe6d18f2ebd1f2105dd4b388)を保存。重複・順序逆転・未知のシステムイベントを拒否する5ケースを追加。
- 今回はPythonテストの実行と新コミットのActions結果は未確認。実データ同期なし。対象実測参照日2021-06-14、前回のNasdaq NOCP 4,605銘柄を維持し、新規終値取得0件。2026-11-17のNYSE/Nasdaq当日網羅率は未測定。株価原本・APIキー・APKの公開なし。
- 未解決: 新テスト実行、Dolt日次同期と429再試行の実測、正規セッション終値と株式分割・SEC株数の整合、Android実機相当テスト。次回は米国株Pythonテストを実行し、Actionsの結果を確認してからDolt日次同期へ戻る。

## 2026-11-18 05:15 JST — Nasdaq NLSの破損パケットを安全に拒否

- 開始時main: [fdb3fa1](https://github.com/osawamas/value-hunter-ai/commit/fdb3fa19c32824e182d1aae6df2eea449247c3f5)。前回のNasdaq NOCPとDoltの照合を維持し、NLSキャプチャの破損入力検査を改善。
- MoldUDP64で宣言されたメッセージ数に対して残り2バイト未満の長さヘッダーを読もうとすると、従来は空スライスが長さ0として扱われていた。明示的に `ValueError` を返すよう[コード修正](https://github.com/osawamas/value-hunter-ai/commit/3372b23d8f7e72bbbd682d2ce78d471fb7072f72)、0/1バイトの不足を検査する[回帰テスト追加](https://github.com/osawamas/value-hunter-ai/commit/aa66f0d3365b0f277f7febbf8afa8d47eb2e824c)。不完全なサンプルを正常な終値欠落と誤認しないための修正。
- [Nasdaq NLS仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)と既存のMoldUDP64解析コードを参照。テストのGitHub保存は完了したが、この回ではPythonテストと新コミットのActionsは未実行・未確認。[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)。
- 対象の実測参照日は2021-06-14（既存サンプルのNOCP 4,605銘柄）。今回は新規の終値照会0件、NYSE/Nasdaqの当日網羅率再測定なし。SEC株数、分割前終値、Android実機相当の更新・通知は未検証。価格原本、APIキー、APKの公開なし。
- 次回: 追加テストのActions結果を確認し、MoldUDP64のパケット境界異常を追加検証。続いてDolt日次同期と同日上場一覧で市場別網羅率を実測。

無料・APIキーなしで、NYSE・Nasdaq上場の普通株を広く扱う個人用Androidアプリの開発記録。ダウ平均は構成銘柄の確認対象として扱う。各回の結果を新しい順に追記する。

## 2026-11-18 05:03 JST — Nasdaq公式終値との差が大きい銘柄を同一条件で再照合

- 開始時mainは [322d9c0](https://github.com/osawamas/value-hunter-ai/commit/322d9c078be7ed34f1bf8e63f2755be63c0bfaed)。Tape C検証レポートに `nocp_differences_vs_consolidated` を追加。同じ日・同じティッカーで、NOCPとの差が1セントを超えた銘柄について、Doltと取引所横断の集計終値の一致、差、欠測、複数値を記録する。
- 2021年6月14日のNasdaq原本と前回照会済みのDolt公開DB全11バッチを新コードで再照合。対象263銘柄中、262はDoltと取引所横断の集計終値が完全一致。残る1銘柄はNSPRで、Doltと両基準に1セント超の差があった。両方の価格基準を別の意味で扱うことは[Nasdaqの仕様](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NLSPlusSpecification3.0.pdf)にも明記されている。
- NSPRは[発行体の提出資料](https://www.sec.gov/Archives/edgar/data/1433607/000149315222006180/R16.htm)から2021年5月21日のNasdaq移管を確認。6月14日の差との因果は不明。ローカルテスト74件成功。今回は過去サンプル1日分で、現行市場・Android端末での日次取得、Doltの現行全銘柄の終値基準は未検証。

## 2026-11-18 04:51 JST — Nasdaq公開サンプル全件のDolt照合

- 開始時mainは [c956a35](https://github.com/osawamas/value-hunter-ai/commit/c956a359996e2bd3295e996a74682a12deaa9363)。NLS Plus Tape Cの比較出力に、完全一致件数、Doltの行欠落・無効値・1セント超の差のティッカーを追加。価格は出力しない。
- [2021年6月14日のNasdaq公開サンプル](https://emi.nasdaq.com/Basic_NLS/NLS/)を通読し、公式終値（NOCP）4,605銘柄と、一意な取引所横断終値4,453銘柄を、同日のDoltHub公開DBへ調査用に分割照会。全11バッチが成功し、各行の日付・銘柄・重複を検査した。ETFなどを含む対象日の比較。
- NOCPはDoltに有効値3,689、行なし916。有効値のうち完全一致3,334、完全一致を含む1セント以内3,426、1セント超263。取引所横断終値は有効値3,588、行なし865、有効値のうち完全一致3,587、1セント超1。双方とも比較母集団内に無効値行はなかった。
- 11月17日14:01米東部時間の一覧では、NOCP側で欠落した916件のうち90件と同じティッカーが非ETF・非テストのNasdaq銘柄に残っており、うち9件は普通株表記。同一証券を保っているかは未確認。
- ローカルテスト73件成功。現行全銘柄の取得率・価格差の理由・Android実機での日次取得は未検証。価格原本と調査用のDolt行はリポジトリに追加していない。

## 2026-11-18 04:25 JST — Nasdaqの公式終値通知を公開ファイルで検証

- 開始時mainは [8dcf59c](https://github.com/osawamas/value-hunter-ai/commit/8dcf59c95b80f2d104d83cfef38e3f102aa33b84)。`us_nasdaq_nls_probe.py` を追加。NLSの公式終値通知の売買条件Mを判別し、NLS Plus Tape CではNOCPと取引所横断の集計終値を別々に読み取る。完全なTape Cサンプルはシステムの開始・終了を検査し、異なる同日値のある銘柄を区別する。
- [NLS 4.0公開PCAP](https://emi.nasdaq.com/Basic_NLS/NLS%204.0/) は米東部時間2026年3月3日の約定162件、NOCP通知0件。[2021年6月14日Tape C公開サンプル](https://emi.nasdaq.com/Basic_NLS/NLS/)（圧縮約273 MB）は通読でき、Nasdaq上場のNOCP 4,605銘柄、取引所横断の集計終値は一意4,453銘柄・値が複数107銘柄。上場銘柄にはETF等も含まれる。
- 2021年6月14日のAAPLなど12銘柄を公開DoltHubで個別に調査し、NOCPとも取引所横断の集計終値とも12/12で1セント以内だった。照会は12銘柄に限定し、残りのDolt網羅率は未測定。
- ローカルテスト72件成功。今回の公開サンプルは指定日の検証経路。日次の公式配信にはアカウントが必要な経路があり、無料の全市場日次経路は未確立。Android端末での取得や訂正・取消反映は未検証。価格原本や個別価格は公開リポジトリに追加していない。

## 2026-11-18 04:11 JST — Doltの成功終了でも不正なローカルDBを採用しない

- 開始時main: [d0c4bd4](https://github.com/osawamas/value-hunter-ai/commit/d0c4bd4908fd2cb8c8a1a767db4447f8f104d0ea)。直近の[米国株テストActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44154786930)と[Android Actions](https://github.com/osawamas/value-hunter-ai/actions/runs/44154786872)は成功。既存のNYSEクラスA/B照合には触れず、Dolt同期の異常終了判定を対象とした。
- [同期コード](https://github.com/osawamas/value-hunter-ai/commit/b5efb6b45ce69c7b9c99c5df38ac403d0a1b3663): Doltコマンドが終了コード0を返しても、取得先に .dolt ディレクトリがなければ成功扱いせず invalid_repository_after_command を返す。CLIも非ゼロ終了する。成功と誤認して欠損キャッシュを使うのを防止。[回帰テスト](https://github.com/osawamas/value-hunter-ai/commit/0c7e434fae241808dc0e9796d671bd85909ba3663)を2件追加し、初回cloneと既存pullの異常を模擬。
- GitHubへのコードとテストの保存は完了。実行環境のgit cloneはDNS解決失敗のため、ローカル全テストは未実行。新コミットの[Android Actions](https://github.com/osawamas/value-hunter-ai/actions/runs/44156036892)は確認時点で待機中。テスト成功とは記載しない。
- 対象取引日2026-11-17: 今回はDolt実データの同期・終値取得・NYSE/Nasdaqの件数再測定なし。前回の2026-07-01 NYSE 2,397/2,401、2026-07-02 NYSE 2,398/2,403は公開サンプルに限る。Nasdaq全市場、正規セッション未調整終値、SEC株数、Android実機取得は未確認。原株価データ・APIキー・APKは公開していない。
- 次回: 新Actionsの結果と対象テストの実行を確認し、Doltの429・タイムアウト時のキャッシュを実環境で検証。日付付きNYSE/Nasdaq網羅率の実測へ進む。

## 2026-11-18 04:05 JST — NYSEのクラスA/B株を比較対象に追加

- 開始時mainは [15334b3](https://github.com/osawamas/value-hunter-ai/commit/15334b3b05ece7094b6521019002d9a0ef3604a5)。`--with-share-classes` でNYSE TAQの空白付きA/B接尾辞をドット付きの同一クラスとして照合。株式のクラス記号は[NYSE FIX仕様](https://www.nyse.com/publicdocs/nyse/markets/nyse/NYSE_CCG_FIX_Specification.pdf)と、11月17日作成の公開Nasdaq Trader otherlistedにあるACT/CQSの同表記で確認した。7月のNYSEサンプルに出たA/B表記21種が11月の一覧でもNYSE・同じドット付き表記に一致した。今回の7月サンプルの母集団はNYSE TAQ内で決め、11月の一覧は表記の確認にだけ使用した。
- 7月1日のTAQとDolt公開DBで16/16、7月2日は17/17のクラスA/B行が同日有効値で完全一致。既存の英字のみ銘柄を合わせると7月1日は2,397/2,401、7月2日は2,398/2,403がDoltにあり、比較できた値にはどちらも1セント超の差がなかった。
- ローカルテスト67件成功。無接尾辞・A・Bを別銘柄として検証し、優先株や条件付き接尾辞は変換対象外。11月17日当日分、Nasdaq全体、Android端末での取得は未検証。

## 2026-11-18 03:56 JST — NYSEで欠けた銘柄の後日の終値を追跡

- 開始時mainは [b1d484c](https://github.com/osawamas/value-hunter-ai/commit/b1d484cce6c6c358e92c158657b8148dadd3173c)。NYSE TAQ検証に `--follow-through` を追加。対象日にDoltで終値が欠けた銘柄だけをローカルDBで照会し、指定日までに見つかった最も早い終値の日付を出す。追跡エラー時も対象日の集計を出力する。
- 7月2日に欠けたDMC・GLAS・MBGL・OTAI・SECZは、現在のDoltHub公開DBで7月6日付の有効な終値が5銘柄すべてにあった。[NYSE公式日程](https://www.nyse.com/trade/hours-calendars)で7月3日の休場を確認。7月31日・11月16日にも5/5。公開DBでの長期集約照会はタイムアウトしたが、日付を絞った照会は成功。収録行の価格日付を確認したもので、当時の配信時刻は未検証。
- ローカルテスト66件成功。終端日以前の回復結果、未取得の保持、範囲外結果の拒否を確認。値の後日流用はしていない。Nasdaq全体・Android端末での日次自動取得は継続課題。

## 2026-11-18 03:47 JST — NYSEの欠落銘柄を特定し、上場・変更日を確認

- 開始時mainは [9aed6f3](https://github.com/osawamas/value-hunter-ai/commit/9aed6f3925a4597e339f859d44da2e4899f1b368)。NYSE TAQ照合レポートに、Doltに当日行がない銘柄、当日行があっても有効な終値がない銘柄、1セント超の差がある銘柄を追加。
- NYSE公式サンプルとDoltHub公開DBを日付ごとに照会。7月1日は2,385銘柄中2,381件照合、DMC・GLAS・MBGL・OTAIの4銘柄にDoltの行なし。7月2日は2,386銘柄中2,381件照合、同じ4銘柄とSECZの計5銘柄に行なし。両日とも照合値は2,308件が完全一致、73件が非完全一致で1セント以内、1セント超なし。
- [DMCへの変更は6月29日](https://investorrelations.freshdelmonte.com/news/news-details/2026/Fresh-Del-Monte-Produce-Inc--Announces-Name-Change-to-Del-Monte-Corporation-and-NYSE-Ticker-Symbol-Change-to-DMC/default.aspx)、[GLASのNYSE取引開始は6月30日](https://www.sec.gov/Archives/edgar/data/1848731/000110465926083587/tm2619713d1_ex4-13.htm)、[MBGLは7月1日](https://www.sec.gov/Archives/edgar/data/2090312/000110465926080006/tm2619098d1_ex99-1.htm)、[SECZは7月2日](https://www.sec.gov/Archives/edgar/data/2094496/000162828026056788/secz-20260630.htm)と確認。OTAIは[発行体資料](https://www.sec.gov/Archives/edgar/data/2094076/000149315226022571/ex99-2.htm)でユニットと普通株が別銘柄。普通株の単独取引の正確な開始日は未確認。Doltでの欠落原因と後日の初回収録日は未確認。
- ローカルテスト65件成功。公開サンプルの7月1日・2日のNYSE対象条件内での観測で、現在のNYSE・Nasdaq全銘柄やAndroid端末での日次取得は未検証。株価原本や観測価格は公開リポジトリに追加していない。

## 2026-11-18 03:36 JST — NYSE公開TAQの当日LastでDoltを検証

- 開始時mainは [e83c378](https://github.com/osawamas/value-hunter-ai/commit/e83c378105e62622cc0fa40e6397737f4dfd8cd5)。`us_nyse_taq_probe.py` で[NYSEの公開サンプル](https://ftp.nyse.com/Historical%20Data%20Samples/TAQ%20CLOSING%20PRICES/)とローカルDoltを照合できるようにした。NYSE上場コード、英字だけの銘柄コード、取引日一致、正のLastと出来高を確認。株式クラスの接尾辞を自動変換しない。
- 7月1日のNYSE原本9,187行を実取得し、条件を満たした2,385銘柄を公開DoltHubに調査用照会。2,381銘柄に有効値があり、うち2,308が完全一致、73が非完全一致で1セント以内、1セント超は0。Dolt側で4銘柄に正の終値がなかった。
- 原本でTAP A・WSO Bに対象日より前の日付のLastが入っていた。[NYSE仕様](https://www.nyse.com/publicdocs/nyse/data/TAQ_Closing_Prices_Client_Spec_v1.2.pdf) の持ち越し値を誤採用しないよう行の日付を照合。価格付き原本は公開リポジトリに追加していない。
- ローカルテスト65件成功。NYSEのベンチマークは公開サンプル1日分の条件付き比較。11月17日の同日網羅率、Nasdaq公式終値、Android端末での日次取得は未検証。

## 2026-11-18 03:17 JST — 定時実行で別ソースの追加取得候補を照合

- 開始時mainは [f9daf6b](https://github.com/osawamas/value-hunter-ai/commit/f9daf6bb324ddff925fd17eab4f557c56cf6371e)。並行更新 [5af711e](https://github.com/osawamas/value-hunter-ai/commit/5af711eedd31076bb59758ef028fe325aa25618b) を取り込み済み。`--compare-marketparquet` で登録不要の同日公開サンプルを照合。サンプルだけで確認できた銘柄と両方で欠けた銘柄を記録し、サンプルの異日・未配信・破損でDolt単独集計を止めない。
- 11月13日取引分のMarketParquet原本と11月17日作成の上場一覧で、終値が欠けた普通株候補はNYSE 21、Nasdaq 131。該当銘柄を同日のDoltHub公開DBで照会するとNYSE 1・Nasdaq 2に有効値があり、照会範囲で両方にないのはNYSE 20・Nasdaq 129。翌週の上場一覧を使った観測のため、11月13日当日の母集団の網羅率ではない。
- ローカルテスト64件成功。分割調整済みの参考値はDolt集計と分け、実際の値の補完や価格の公開はしていない。MarketParquetだけが持つ値の全銘柄再測定とAndroid端末での取得は未検証。

## 2026-11-18 03:15 JST — Dolt実行時のOS例外と空出力を安全に処理

- 開始時main: [f9daf6b](https://github.com/osawamas/value-hunter-ai/commit/f9daf6bb324ddff925fd17eab4f557c56cf6371e)。直近の[米国株Actions](https://github.com/osawamas/value-hunter-ai/actions/runs/44145243001)は成功。既存の終値欠落追跡機能は変更せず、Dolt同期のプロセス起動失敗に限定して修正。
- [同期コード](https://github.com/osawamas/value-hunter-ai/commit/73ca5a27ee17c51d8ce57958a4c5a5a2381ac41e): subprocessのstderr/stdoutがNoneでもエラー分類が停止しないようにし、PermissionErrorなどのOSErrorで既存キャッシュを維持。初回起動失敗はos_errorで明示。429の待機・再試行規則は維持。
- [回帰テスト](https://github.com/osawamas/value-hunter-ai/commit/408df967b30a94de50b32386202f60efafdfbf80): 既存キャッシュ保持、初回起動失敗、空出力の3件を追加。実行環境からGitHubへのgit cloneがDNS解決できず、ローカルPythonテストは未実行。新コミットのActions結果も未確定（[Actions一覧](https://github.com/osawamas/value-hunter-ai/actions)）。
- 対象取引日2026-11-17: 今回の終値実取得・NYSE/Nasdaq件数再測定なし。11月16日の過去測定値は同日上場一覧に基づかず正式網羅率ではない。正規セッション未調整終値、SEC株数、Android実機相当テストは未完了。株価原データ・APK・キーは公開していない。
- 次回: 新コミットのActionsを確認。失敗時は修正。Dolt同期の実測と11月17日付の同日終値照合を優先。

## 2026-11-18 03:12 JST — 終値欠落をティッカー単位で記録

- 開始時mainは [7f39f99](https://github.com/osawamas/value-hunter-ai/commit/7f39f999c04f6fd5118b9283e0378963f382c122)。定時実行の日付別レポートにNYSE・Nasdaq普通株候補の終値未取得ティッカーを追加。同一の上場一覧ハッシュと照合条件で、取得できるようになったティッカーと新たに欠けたティッカーを記録する。旧形式は従来の件数比較を維持する。
- 11月17日11:01米東部時間作成のNasdaq Trader上場一覧と11月16日のMarketParquet原本で、未取得ティッカーの数がNYSE 25、Nasdaq 92になり、集計件数に一致することを再現した。両ソースのカバー率を再測定した結果ではない。
- DoltHubの11月16日分を個別照会。BIO.B・TAP.A・WSO.Bと、ドットをハイフン・スラッシュに替えた表記、KELYBには正の終値がなく、別クラスのBIO・TAP・WSO・KELYAにはあった。株式クラスごとの照合を維持する。
- ローカルテスト60件成功。終値件数の合計が変わらなくても銘柄の入れ替わりを検出することを確認。11月17日の引け後の同日実数、Android端末での日次取得は未検証。

## 2026-11-18 03:01 JST — ダウ30の終値を日付の一致したDIA明細で検査

- 開始時mainは [f4f33de](https://github.com/osawamas/value-hunter-ai/commit/f4f33de1dfccdfc386874533e5ef65bb775a7ed6)。定時ツールに `--with-dow` を追加。State StreetのDIA保有明細を検証し、基準日別に保存。価格対象日と一致したときだけダウ構成銘柄の近似として集計する。取得失敗や日付不一致でNYSE・Nasdaqの集計を止めない。
- 公開明細の11月16日基準データから現金を除く30銘柄を取得し、DoltHub公開DBを調査用に照会して同日の正の終値を30/30確認。11月16日分の同時点上場一覧は未入手なので、NYSE・Nasdaq全体の網羅率は再測定していない。
- Pythonテスト59件成功。日付一致の明細の集計と、別日明細が混ざっても市場別集計が残る動作を確認。11月17日の正規セッション終値、Macの定時登録、Android実機の日次取得は未検証。

## 2026-11-18 02:54 JST — NYSE・Nasdaqの終値取得件数の増減を記録

- 開始時mainは [193a1aa](https://github.com/osawamas/value-hunter-ai/commit/193a1aa04b208a0f9178fc83524f48334b54562e)。保存済み集計の再照合で、同日・同じ価格基準・同じ上場一覧の取引所ごとに前回件数、今回件数、差をレポートと標準出力へ記録。新形式は一覧2本のSHA-256でも照合し、旧形式は日付・一覧作成時刻・対象件数で比較する。
- 11月17日12:53米東部時間時点の調査用公開DoltHub照会では、16日分の非NULL終値12,639行、17日分の行はなし。MarketParquetの17日分ファイルはHEAD確認でHTTP 404。どちらも米株の引け前の観測なので、17日終値の網羅率は未測定。
- ローカルテスト58件成功。増加・減少と、一覧内容が異なるときの差分停止、空の取得結果で既存レポートを保持する動作を検証。実データの日次照合、Android端末での日次取得は継続課題。

## 2026-11-18 02:50 JST — 集計済みの取引日も再照合

- 開始時mainは [2f5da19](https://github.com/osawamas/value-hunter-ai/commit/2f5da197cbae77730d3fde38138bc77e05d8df36)。定時処理は過去7暦日の保存済み一覧について、既存の終値集計も再照合する。結果に観測時刻と未確定の状態を記録し、正常に集計できた場合に日付別レポートを更新する。日次終値なしや照合エラーでは既存レポートを保持する。標準出力にNYSE・Nasdaqの銘柄カバー件数を出す。
- DoltHub公開DBの調査用照会で11月16日分の非NULL終値12,639行を確認。11月17日取引時間中の照会では17日分の価格行は未配信だった。アプリ開発用の定時処理は引き続きAPIキー不要のローカルDoltを利用。
- Pythonテスト57件成功。追加後の再照合でNYSEの取得数が増えることと、その後の空応答で前回の集計を保持することを模擬データで再現。実ファイルの11月17日保存分を新しいコードで読み込んだ。11月17日の引け後の実数測定とAndroid端末での日次自動取得は未検証。

## 2026-11-18 02:42 JST — 定時保存と当日一覧に基づく終値比較を接続

- 開始時mainは [7a56187](https://github.com/osawamas/value-hunter-ai/commit/7a5618701678ceb04e51b92fe578c7cc3ca94951)。`us_daily_coverage.py` でXNYS取引日に米東部時間の昼に一覧を取得し、過去7暦日内の未集計の保存済み取引日をDoltの同日終値と照合。日付別に集計を保存し、Dolt側に有効な値がない日は次回実行で再試行する。日本時間のMacで動かす定時実行例をREADMEに記録した。
- 11月17日12:41米東部時間、新規保存先で公式ファイル2本の取得・保存を実行。11月16日の一覧は未保存なので同じ日の実データ照合は未実行。既存の11月17日保存分を再利用する動作も確認。NYSEカレンダーでは11月26日が休場、同27日が13:00引けになることを照会した。
- Pythonテスト57件成功。Doltに終値がない日を保留し、別の同日一覧と終値が揃った日だけ集計する動作を模擬データで検証。定時起動例はリポジトリに記録済みで、Macへの登録、11月17日実データの引け後の同日照合、Android端末での日次取得は未検証。

## 2026-11-18 02:29 JST — 上場一覧2本を日付別に保存して再生

- 開始時mainは [9b84ba9](https://github.com/osawamas/value-hunter-ai/commit/9b84ba945e68579181c60d2843c0ccdf30bf6342)。`--save-directory-to` でNasdaq Traderの公開上場一覧を米東部時間の日付で保存。`--directory-archive` で対象日分を厳密に再生する。保存前に2本の作成日と重複を照合。2本まとめて公開先のディレクトリ名に移し、再実行は初回保存分を保持する。
- 実通信で米東部時間11月17日11:01作成の一覧2本を保存。上場一覧の検査でETF・テスト銘柄などを除いた後は7,456件（NYSE・Nasdaq以外の取引所や普通株以外も含む）。同じ日の再実行で保存済みペアを再読込した。11月16日分が未保存なら、当日値の検査に入る前に停止することも確認。
- ローカルのPythonテスト56件成功。11月16日の当日一覧は未入手。今回は終値の網羅率を再集計していない。自動での定時保存、保存した同日一覧と終値の正規セッション比較、Android端末での日次取得は継続課題。GitHubにはコードと開発ログを追加し、保存した上場一覧原本はローカルで検証した。

## 2026-11-18 02:15 JST — 上場一覧の観測日と終値対象日のずれを明示

- 開始時main: [cfa8d66](https://github.com/osawamas/value-hunter-ai/commit/cfa8d6609099039283b92dea444c078ba3b61723)。直近の[米国株テストActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44134268173)は成功。並行開発で追加されたティッカー変更照合は維持した。
- [検証ツール変更](https://github.com/osawamas/value-hunter-ai/commit/004c5741dce0f941695d2b51b4043d8dfc3ba518)で、終値対象日とNasdaq Trader上場一覧の作成日の差を日数・状態としてJSONに出力。未来・過去・同日観測を区別し、同日でも「取引日時点の上場母集団を確認済み」とは扱わない。[回帰テスト追加](https://github.com/osawamas/value-hunter-ai/commit/c0e54305f355db471e9ebd9a58051308b16ed377)。
- 対象取引日は2026-11-16、上場一覧は2026-11-17作成で1日後の観測。前回実測のNYSE 1,875/1,896、Nasdaq 3,103/3,191は再測定していない。VRSA/VBNKなど変更日にまたがる銘柄を誤って歴史的母集団に確定しない。
- 今回の新規テストはGitHubに保存済みだが、[変更直後のActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44134420024)は確認時点で待機中（コード変更コミットの実行）。テスト追加後のActionsと実機動作は未確認。価格原データ・APK・APIキーの公開なし。
- 次回: テスト追加後のActionsを確認し、取引日当日の上場一覧を安全に保存・比較する手順を実装。Dolt同期の429、正規セッション未調整終値、SEC株数照合は継続課題。

## 2026-11-18 02:12 JST — 上場・ティッカー変更の出典を終値欠落に照合

- 開始時mainは [009bf3d](https://github.com/osawamas/value-hunter-ai/commit/009bf3d567e6be1e8c94f80e30d8ffce57f56c03)。`--listing-evidence-file` で取引所・ティッカー・日付を照合し、発行体が示した開始予定と取引所が通知した変更発効日を区別。変更前の対象日については旧ティッカーの終値の有無も表示する。
- 3取引日連続欠落で停止記録に一致しなかった31銘柄のうち8銘柄に出典を登録し、11月16日の公開評価サンプル・Doltの欠落データで再現した。NasdaqのVRSAへの変更は11月17日付。11月17日の上場一覧から旧VBNKは消えていたが、MarketParquetには11月16日のVBNKの終値があった。[Nasdaqの公式通知](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-832)
- TXRは11月17日NYSE取引開始予定で、同日の上場をNYSEも告知。BRRKの単独取引は11月16日ごろの予定で初約定は未確認。GLED・SBXE・MIAC・PALO・RNAQの単独取引開始に関する発表日は以前で、11月16日の約定や欠落理由を確定できない。各出典は[検証用イベント一覧](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/evidence/us-listing-events-2026-11-16.json)に記録。
- ローカルのPythonテスト54件成功。価格のコピー・公開や既存の終値取得率の変更はしていない。取引日当日の銘柄一覧を保存する仕組み、未解決の銘柄への追加照会、Android端末での日次取得は継続課題。

## 2026-11-18 02:03 JST — 終値欠落とNasdaq Traderの売買停止記録を照合

- 開始時mainは [3a2f9e9](https://github.com/osawamas/value-hunter-ai/commit/3a2f9e92b53d96dff206e4451d91e0c274e73aa7)。検証ツールに `--with-halts` と `--halt-feed-file` を追加。対象日の翌日以降に配信されたRSSで、停止開始日が対象日より前、再開日が対象日より後か未記載のものを取引所・ティッカーの両方で照合する。終値の採否・カバー率は維持する。
- [Nasdaq Traderの公開RSS](https://www.nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS) の11月17日12:01米東部時間配信（75件）を、11月16日の終値が両ソースで欠けた109銘柄と照合。NasdaqのEFTY・HCHL・MAGH・OST・PC・SVA・TJGC・UCFIの8銘柄に、対象日をまたぐ停止記録を確認。8銘柄とも3日連続で欠けた39銘柄に含まれる。
- 3日連続欠落の残り31銘柄（NYSE 6、Nasdaq 25）は、今回のRSSに一致する記録なし。照合できなかった銘柄の停止有無や上場開始日は未確認。Nasdaqの歴史的な全上場異動を収録するDaily Listは月額契約なので、今回の取得経路には採用しない。
- ローカルのPythonテスト53件が成功。前回変更に対する [Androidビルド](https://github.com/osawamas/value-hunter-ai/actions/runs/44129863138) は成功。今回の照合は開発用ツールで検証した。Android端末での日次自動取得、取引日ごとの全上場銘柄照合は継続課題。

## 2026-11-18 01:49 JST — 終値欠落109銘柄の直前2取引日を照合

- 開始時mainは [8d41f73](https://github.com/osawamas/value-hunter-ai/commit/8d41f73141d72b484201fac5ecd826617f08733c)。[変更コミット](https://github.com/osawamas/value-hunter-ai/commit/06d679ae7e9c43c2426e59f6e1ad50b39e9fcdf7) で、NYSE・Nasdaqそれぞれの欠落を過去の最終確認日ごとに集計する `--history-date` を追加。以前の終値は対象日に流用しない。
- 11月17日11:01作成のNasdaq Trader上場一覧を基準とし、11月16日にMarketParquetで拾えなかった普通株候補117銘柄をDolt公開DBで11月16日・13日・12日について照会。通常の検証ツールは同期済みローカルDoltから読む。
- NYSEは1,896銘柄中、両ソースに終値なし21。そのうち直前に確認できた日が11月13日の銘柄11、11月12日のみ4、両日ともなし6。Nasdaqは3,191銘柄中88で、同じ順に40、15、33。70銘柄に過去値あり、39銘柄は確認した3日すべてで欠落。売買停止や新規上場などの個別理由は未確認。
- ローカルテスト52件と [米国株テストActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44129863243) 成功。[Androidビルド](https://github.com/osawamas/value-hunter-ai/actions/runs/44129863138) は記録時点で実行中。コードと集計結果を記録し、価格原データの公開はしていない。
- 次回は39銘柄から上場開始日や公式の売買停止記録を確認し、終値が欠けた理由を追う。当日の終値取得率はNYSE 1,875/1,896、Nasdaq 3,103/3,191。全銘柄の正規終値や取引日時点の株数、Android端末での日次取得は未検証。

## 2026-11-18 01:30 JST — DoltとMarketParquetの終値を比較

- 開始時main: [de8c4a7](https://github.com/osawamas/value-hunter-ai/commit/de8c4a775ad11622b0924797e8a9c6c0478f8643)。比較機能のコードは [24c16cf](https://github.com/osawamas/value-hunter-ai/commit/24c16cfc98910ca940c9e746259a24678456086f)。
- Nasdaq Traderの11月17日11:01作成の上場一覧で、11月16日取引分を比較。Dolt公開DBの調査用照会で12,639行（重複・異日混入の検査を含む）を読み、MarketParquetの同日公開評価サンプルと照合した。ローカル版はAPIキーなしのDoltクローンから読む。
- NYSE本市場1,896銘柄のうち、両方で1セント以内1,871、Doltのみ4、MarketParquetのみ0、両方なし21。Nasdaqは3,191銘柄のうち、両方で1セント以内3,099、Doltのみ4、MarketParquetのみ0、両方なし88。両方で1セント超の差は0。
- Pythonテスト50件と [米国株テストActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44126445869) 成功。価格は補完・公開していない。
- 次回は両方にない銘柄の未取得要因と、公式の正規セッション終値・取引日時点株数を確認する。価格の一致だけでは、両配布元の独立性や未調整終値の正しさは確定しない。

## 2026-11-18 01:13 JST — DoltのHTTP 429誤判定を修正

- 開始時main: [f72dd2a](https://github.com/osawamas/value-hunter-ai/commit/f72dd2adf4608ce9928875df4911244a210202a7)。直近のAndroid private preview Actions [44111407558](https://github.com/osawamas/value-hunter-ai/actions/runs/44111407558) は2026-11-18 00:12 JST頃に成功（開始時のmainに対応）。
- [Dolt同期ツール](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py) のHTTP 429判定を、単純な文字列包含から数字の境界を確認する正規表現に変更。無関係なエラー番号1429を429と誤認し、60秒待機して再試行する問題を防止する。HTTP 429と Too Many Requests は引き続き再試行対象。コード [8c2a204](https://github.com/osawamas/value-hunter-ai/commit/8c2a204717ed0136a4fbba21416f7af1b964b424)。
- [テスト](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/test_us_dolt_sync.py) に、1429を再試行しないこと、初回cloneの429で部分cloneを再試行しないことの2件を追加。[23486a9](https://github.com/osawamas/value-hunter-ai/commit/23486a91d5d6ffe7983563e9d375355c616ec27a)。変更ロジックの独立ローカル再現テスト3件は成功。既存7件を含む全テストと新規Actionsは記録時点で未確認。
- 対象取引日2026-11-16。NYSE 1,875/1,896、Nasdaq 3,102/3,190は過去の実測値を継承。今回は新しい実データの取得・網羅率再測定なし。Dolt全件同期、終値の取引セッションと未調整基準、SEC株数、正式PER/PBR、Android端末検証は未完了。
- 次回: 新規Actions結果の確認、Doltの部分cloneを安全に診断する手順、実データ同期と正規終値照合。公開GitHubに株価原データ・APIキー・APKは追加していない。

## 2026-11-18 00:10 JST — Dolt同期タイムアウト時の安全な保留処理

- 開始時main: [b901406](https://github.com/osawamas/value-hunter-ai/commit/b90140633df3e72e4c10b73cdd872216f1678ca2)。直近のGitHub Actions [44101251657](https://github.com/osawamas/value-hunter-ai/actions/runs/44101251657) は成功（ZIPブラウザーのワークフローであり、今回の米国株修正の検証ではない）。
- [Dolt公開DB](https://www.dolthub.com/repositories/post-no-preference/stocks) の同期コードで、180秒タイムアウト時の未処理例外を明示的な状態に変更。既存DBなら cached_after_timeout として保持し、初回cloneなら timed_out として部分cloneを再試行しない。Dolt未導入は dolt_not_installed として区別する。公開データ・APIキー・APKの追加なし。
- 既存4件に加えタイムアウト（既存・初回）とDolt未導入の3件を追加。Python unittest 7件成功（ローカル模擬実行）。この変更のActionsはコミット時点で未確認。
- 対象取引日2026-11-16。前回実測NYSE 1,875/1,896、Nasdaq 3,102/3,190を引き継ぐ。今回は新規の実データ同期・網羅率再測定なし。正規終値・全件同期・株数照合・正式PER/PBR・Android通知は未完了。
- 次回: Dolt実機での同期とタイムアウトの実地検証、失敗後の部分clone復旧手順、同日付の正規終値照合。

## 2026-11-17 23:15 JST — Dolt同期の安全な再試行を実装

- 開始時main: [b43fbf6](https://github.com/osawamas/value-hunter-ai/commit/b43fbf68e3385f8bf77c466b86bfbcb23fb6f788)。直近Actions [44091795985](https://github.com/osawamas/value-hunter-ai/actions/runs/44091795985)、[44091795884](https://github.com/osawamas/value-hunter-ai/actions/runs/44091795884) は成功。
- [同期ツール](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_dolt_sync.py) を追加。初回は浅いclone、既存DBはfast-forwardのみpull。HTTP 429時は既存DBを保持し、60秒待って最大1回再試行。初回clone失敗時は部分ディレクトリの可能性があるため自動再試行しない。認証エラーなどは再試行しない。価格原データはリポジトリへ保存しない。
- [回帰テスト](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/test_us_dolt_sync.py) を追加。ローカルPythonで4件成功（clone成功、既存DBと429、通常エラー、非DBディレクトリ拒否）。コードコミット [523586b](https://github.com/osawamas/value-hunter-ai/commit/523586b013797402fd4faada942a4d729d612ffd)、テストコミット [b530fa8](https://github.com/osawamas/value-hunter-ai/commit/b530fa85d7615b85039fd76f5f4f147871def348)。新規コミットのGitHub Actionsは本ログ記録時点で未確認。
- 対象取引日2026-11-16。前回実測NYSE 1,875/1,896、Nasdaq 3,102/3,190。今回は新規実データの同期や網羅率再測定なし。DoltのHTTP 429解消・利用条件・分割前終値の全銘柄検証は未完了。
- 次回: Dolt実行環境で同期の実地検証、429で部分cloneが残る場合の手動復旧手順、正規終値の基準照合。正式PER/PBRやAndroid通知へはまだ接続しない。

## 2026-11-17 22:19 JST — Dolt終値の入力検証を強化

- 開始時main: [3ac9ba5](https://github.com/osawamas/value-hunter-ai/commit/3ac9ba518ca16cdbf6a4d8bbec1302dd69511efe)。直近のAndroid private preview Actions [44089075788](https://github.com/osawamas/value-hunter-ai/actions/runs/44089075788) は成功。並行する日本株の更新は触れていない。
- [us_public_files_probe.py](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/us_public_files_probe.py) のDolt CSV読取りでNaN・無限大・ゼロ・負値・壊れた日付を拒否し、NULL/空欄は「終値なし」として保持するよう変更。無効な値を網羅率の正規終値として誤集計しないための前処理。
- [テスト追加](https://github.com/osawamas/value-hunter-ai/blob/main/android-private/tools/test_us_public_files_probe.py)。コミット [4d91188](https://github.com/osawamas/value-hunter-ai/commit/4d911882956340b711c19b13b73b8c5ec4e8d412)、[b169a42](https://github.com/osawamas/value-hunter-ai/commit/b169a4275aca28f231b03f85f341b62adf16d90f)、[b8ad575](https://github.com/osawamas/value-hunter-ai/commit/b8ad575b23b0228a9fb3fa2bc5bd7d4ea43a7d13)。最初のテスト追加は改行エスケープに誤りがあり修正した。最終コミットの[米国株テストActions](https://github.com/osawamas/value-hunter-ai/actions/runs/44091732748)は成功。[Androidビルド](https://github.com/osawamas/value-hunter-ai/actions/runs/44091732869)は記録時点で実行中。
- 対象取引日: 2026-11-16。前回実測のNYSE 1,875/1,896、Nasdaq 3,102/3,190を引き継ぐ。今回は新規の実データ同期・件数再測定なし。DoltHub [公開DB](https://www.dolthub.com/repositories/post-no-preference/stocks)のHTTP 429、全件同期、ライセンスと終値基準は未解決。
- 次回: Actionsの結果を確認し、失敗時は修正。Doltの同期失敗時に既存ローカルDBを保持する安全な再試行・キャッシュ手順を追加する。株数や正式PER/PBRへの採用は引き続き保留。

## 2026-11-17 22:01 JST — 毎時開発の開始点

- 開始時点のコードは [221273b](https://github.com/osawamas/value-hunter-ai/commit/221273b71dd3198a25c084a08e30c89d7bf97933)。
- 11月16日取引分の公開DBとの照合では、普通株候補に対してNYSE本市場は1,875 / 1,896、Nasdaqは3,102 / 3,190の正の終値を確認した。基準は11月17日観測のNasdaq Trader銘柄一覧。
- ローカルDoltの読取りはテストデータで確認済み。公開DBの浅いクローンはHTTP 429で止まり、全件同期と日次更新は未確認。Apple・NVIDIAの分割前後で未調整の水準を確認したが、市場全体の基準は未検証。
- SECの原本処理はBerkshire HathawayのA株・B株とSouthern Companyの親会社分を確認済み。取引日時点の株数、未調整終値、正式なPER・PBR、Android上の一連の動作は未検証または未実装。
- 次の作業は、Doltの公開資料と利用条件を確認し、HTTP 429の再試行制御と同期済みデータの再利用を優先する。同じ取引日の上場一覧・終値・分割情報の照合へ進む。
