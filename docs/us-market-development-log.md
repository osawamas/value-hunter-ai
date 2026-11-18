# VALUE HUNTER AI 米国株の開発ログ

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
