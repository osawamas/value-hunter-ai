# VALUE HUNTER AI 米国株の開発ログ

無料・APIキーなしで、NYSE・Nasdaq上場の普通株を広く扱う個人用Androidアプリの開発記録。ダウ平均は構成銘柄の確認対象として扱う。各回の結果を新しい順に追記する。

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
