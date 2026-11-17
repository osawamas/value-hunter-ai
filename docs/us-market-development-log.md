# VALUE HUNTER AI 米国株の開発ログ

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
