# VALUE HUNTER AI シンガポール株の開発ログ

## 2026-11-18 07:09 JST — 一覧に欠けていた10取引コードを補完

- 第三者の公開HTMLから再取得した623候補を、SGX上場確認・発行体開示に照合。公開HTMLに欠けていた10コードの証拠を [sgx-listing-evidence.json](data/sgx-listing-evidence.json) に記録し、通常実行時に候補へ追加する処理を実装した。10件のSGX原本を直接取得して、取引コード・証券識別子の掲載箇所を確認した。AWXの開示PDFは取引コードと通貨を記載し、ISINは候補に掲載されたXWAとSGinvestorsの両カウンター表示で照合した。
- 普通株のコード4件は9DC、MIM、MET、AWX。残る6件（A7RU、CJLU、CY6U、HMN、J85、Q5T）は信託・ステープル証券。AEMのAWX（SGD）と既存XWA（USD）は同じISINなので、取引コードは2件、証券識別子は1件と数える。
- 補完後は633取引コード（Mainboard 435・Catalist 198）、632種類のISIN。今回照合した10件の未取得は補完後0件。候補に同じコードで別のISINや取引区分が載った場合は、既存データを上書きせず不一致として出力する。候補全体の現行上場や証券種別は未確認。
- SGX市場全体の未取得数は未確定。SGX公式画面の直接HTMLに銘柄表がなく、10月末の月報は市場別件数のみで日付・範囲も異なる。SG Stocks BriefとEODDataのWeb利用条件に自動抽出の制限があるため、両サイトを一括照合には使用しなかった。
- Pythonテスト88件成功（今回追加2件）。株価取得・Android接続・ランキング反映は今回の作業範囲外。再実行は `python3 android-private/tools/sgx_public_directory.py --include-records`。

## 2026-11-18 06:59 JST — 公開HTMLから銘柄コードとISINを一括取得

- [GetResearchのSGX一覧](https://getresearch.ai/sg)（表示基準日2026-11-13）を1回のHTML取得で読み取る調査ツールを追加。ログイン・データAPI・CSV入力は不要。銘柄行の欠落やコードの重複を検出するため、取引区分ごとの件数をページ内の集計と照合し、ISINのチェックディジットを検証する。
- 実データは624行、Mainboard 426、Catalist 198。すべて別の銘柄コード・ISINだった。[AstakaのSGXNet掲載開示](https://links.sgx.com/FileOpen/Astaka%20-%20Announcement%20on%20Share%20Consolidation%20Completion.ashx?App=Announcement&FileID=904486)に従い、2026-09-17付で廃止された旧コード42Sと旧ISINの組み合わせを除外。新コード9SYは残した。除外後の候補は623件（Mainboard 426・Catalist 197）。
- 既存のSGX公式売買単位資料の11コードはすべて候補にあった。旧API候補182コードとの一致は155、新HTML側だけ468、旧候補側だけ27。コード集合の比較で、旧候補側だけの27件は上場状態やコード変更を未検証。S63・S68は一覧に含まれていた。
- [SGX公式月報PDF](https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20Update_Oct%202026.ashx?App=Announcement&FileID=911153)を直接取得して確認。10月末はMainboard 408、Catalist 197、計605上場証券。候補一覧とは対象日と範囲が異なり、全銘柄取得率や不足数は算出できない。公式企業情報ページも直接取得したが、企業表がHTMLに含まれていなかった。
- Pythonテスト86件成功（今回追加4件）。生HTML・銘柄一覧全件・株価原本はコミットに含めていない。Androidへの投入前に、公式開示で旧コード・上場廃止・銘柄種別を照合する。今回は株価取得とランキング候補の追加なし。

```sh
python3 android-private/tools/sgx_public_directory.py
python3 android-private/tools/sgx_public_directory.py --include-records
```

## 2026-11-18 06:54 JST — 発行会社ページからの日付付き終値を検証

- 目的はMainboardとCatalist上場銘柄の個人用Android監視。無料・データAPIなし・手動CSV登録なしの経路を調べた。
- [Singapore Exchange LimitedのIR](https://investorrelations.sgx.com/stock-information/historic-stock-lookup)の公開HTMLからS68の終値欄を読み取る調査用ツールを追加した。日付の完全一致を求め、同日行の重複、表の欠落・列の変更、ゼロ・無効価格を検出する。標準表示に日付がなければ、ページに載っている日付指定フォームを1回送信する。照会結果にもなければ、その日を未取得として返す。
- 実データではS68の2026年11月13日は標準表示、11月17日は日付指定フォームで、いずれも日付・終値欄に一致した。取得できた銘柄は1、対象取引日は2。出典はLSEGで、配当・分割を反映した表示値。未調整の公式終値やランキング適格件数には算入しない。取得した値・HTML原本はこのリポジトリに保存していない。
- [SGX公式価格一覧](https://www.sgx.com/securities/securities-prices?code=stocks)は直接取得したHTMLに銘柄表がなく、画面の Last は遅延最終売買値。未調整終値は[SGXの履歴データ案内](https://www.sgx.com/data-connectivity/historical-data)に別途記載がある。SGinvestorsの一覧・履歴ページへの直接取得はHTTP 403だった。[第三者の銘柄一覧候補](https://getresearch.ai/sg)は公開ページに624件と表示されるが、直接取得を確認できず、現行上場の普通株母集団には未採用。
- Android用調査ツールのPythonテスト82件が成功（今回追加6件）。調査用ツールの実行方法は下記。Androidの画面・日次監視には未接続。全市場の銘柄コードとISINを取得できる一括ソース、および日付付きの未調整終値を引き続き調査する。

```sh
python3 android-private/tools/sgx_public_ir_close.py 2026-11-17
```

出力はURL・銘柄コード・対象日・照会時刻・価格の種別・照合件数・結果。終了コードは一致が0、日付なしが1、取得・検証エラーが2。
