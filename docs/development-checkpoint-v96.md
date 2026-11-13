# VALUE HUNTER AI — v96 継続開発チェックポイント（2026-11-14 JST）

再開前に必ず GitHub main、直近コミット、最新Actions、docs/data/latest.json、本ファイルを取得。既に終えたテスト/変更は繰り返さない。

## 前提 v91〜v93
- UOB11月10/11/12のSGX買戻し通知3件は公式原本を直接取得し、株式数・SGX URL・SHA256を検証済み。UOB11/13 SG261113OTHRHOAF（転載）とOCBC11/12 SG261112OTHRXH64（添付Anno_12Nov2026.pdf）は公式原本URL未取得。UOB11/13転載の控除後1,646,677,591株と前日公式1,646,711,591株の差34,000株は算術的に一致するが、一次資料検証済みではない。
- 登録7社、銀行D05/O39/U11は2025年監査済み・2026年Q3/9M・前年比解析済み。銀行の現在株数、取引時刻付き信頼性確認済み価格、時価総額、PER、PBRはnull、投資ランキング対象0。

## v94 — 実株価取得の失敗を調査/失敗閉じ
- UOB issuer-linked investor site https://uob.listedcompany.com/ に検索結果では 2026-11-13 17:14 SGT 最終約定37.750SGDと表示される。`u11_ir_quote_probe_v94.py` が実サイトをダウンロードするが、Actionsで届くHTMLは約2,183バイトでUOB/quote/last_doneの機械可読な構造を含まず、`NOT_VERIFIED`へ失敗閉じ。
- テストは日付、価格、URL、ソース種別を満たす合成HTMLでのみ成功。実IRサイトからの自動株価取得は成功していない。Workflow v94は診断が失敗した場合にNOT_VERIFIEDとrecord=nullをassertして継続する構成。最終GitHub Actions #43529854142 成功（データ取得成功と同義ではない）。

## v95 — 銀行3社の過去日付付き価格研究を公開
- SGinvestorsと別の履歴サイトをそれぞれ照合。2026年11月13日の参考終値: D05 DBS 69.900 SGD、O39 OCBC 28.530 SGD、U11 UOB 37.750 SGD。
- `bank_quote_research_v95.py` は2サイトずつのURL/固定参考値を `bank_dated_quote_research.status=DATED_2026_11_13_THIRD_PARTY_PRICE_RESEARCH_NOT_LIVE` に記録。発行体公式のSGX約定価格の独立検証ではなく、ブラウジング時に参照した歴史的な第三者履歴の研究候補。実サイトからの自動更新は未実装。
- DBSはInvesting.comに同じ日付で70.14の相違があり、`price_source_disagreement` に明示して69.90をlive priceに採用しない。URL: https://www.investing.com/equities/dbs-group-holdings-historical-data
- ソース：D05 https://sginvestors.io/sgx/stock/d05-dbs/share-price-history と https://stockanalysis.com/quote/sgx/D05/history/ 。O39 https://sginvestors.io/sgx/stock/o39-ocbc-bank/share-price-history と https://stockanalysis.com/quote/sgx/O39/history/ 。U11 https://sginvestors.io/sgx/stock/u11-uob/stock-info と https://www.eoddata.com/stockquote/SGX/U11.htm
- `test_bank_quote_research_v95.py` で数値不一致、DBS別ソース相違、銘柄重複、price_sgdへの不正投入を排除。UIに『過去の株価調査』欄を表示し二つの出典と価格一致・異常値も説明。
- CI #43530080046 成功、統合 #43530122789 と後続 #43530160916 成功。docs/data/latest.json 更新日 2026-11-13T23:51:36.615880+00:00 を確認、銀行3社の参考値が掲載され、price_sgd/shares_outstanding/market_cap_sgdはnull、7社・不整合0・ランキング0。

## v96 — 3銀行の日時付きページから自動取得可能性を検証
- `bank_quote_http_probe_v96.py` にSGinvestorsのD05/O39/U11 stock-infoページを実HTTP GETする機能と、Issuer identity・銘柄コード・ISIN・SGD価格・`Share Price as of`のSingapore時刻をすべて照合する厳格な読み取り器を実装。`test_bank_quote_http_probe_v96.py` で合成HTMLによる正常系と、偽銘柄/ISIN、未来日付、誤時刻、重複、不達をテスト。今後の実行日の変化で将来日付判定を誤らないよう、2026-11-14固定値を廃止し`Asia/Singapore`現地日付の翌日を拒否する方式へ修正。
- Actions #43530480266 はD05/O39/U11の3つ全ジョブ完了・成功。**ただし実サイト3件ともSGXの株価欄を含む発行体/ISIN表示が取得HTMLから確認できず `NOT_VERIFIED` となった。** 合成HTMLの検証成功と、実サイトの株価取得成功を混同しない。取得不達を診断アーティファクトに残した。
- 本体 `.github/workflows/value-hunter-v29.yml` にv96の合成HTMLユニット回帰テストを追加。実外部株価取得を本番の価格として採用する処理は意図的に追加していない。v96回帰テストを含む本体Actions #43530563069 は全工程成功。日時検証の追加修正後 #43530810735 も全工程成功。独立したv96の3銀行実サイト診断CI #43530810813 と再走 #43530840836 も成功（ただしサイトの値が抽出できたという意味ではない）。文書更新トリガーによる #43530840912 は記録時点でqueued。

## 優先タスク（v97以降）
1. #43530563069 の本体統合結果・main状態と docs/data/latest.json を確認し失敗なら修正。必要な情報が足りない時はfail closed。
2. UOB11/13買戻し通知（SG261113OTHRHOAF）のSGX公式URLを特定、原本のSection Dの株数と基準日を照合。転載の34,000株差だけで正式株式数に昇格させない。
3. OCBC11/12自己株式利用通知（SG261112OTHRXH64）の SGX公式原本と添付 `Anno_12Nov2026.pdf` を取得。買戻しと自己株式の移転の形式を混同しない。
4. SGX公式または権利・利用規約上利用可能な代替市場データフィードで時刻/取引日/通貨/遅延種別の機械検証を進める。SGinvestors/issuer IRの表面HTMLはGitHub Actionsで必要な株価欄を取得できず、スクレイピングだけに頼らない方針を検討。
5. 株価と最新自己株式控除後株数が検証されるまで時価総額・PER/PBR・投資ランキングを無理に有効化しない。SGX全銘柄への拡張は未完。

## 新しいスレッドへの引き継ぎ文章
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）のv96の続きから再開して。main、最新Actions、docs/data/latest.json、docs/development-checkpoint-v96.mdを最初に読む。v94でUOB issuer IRに2026-11-13 17:14 SGTで37.750SGDの表示を見つけたがActionsの取得HTMLには株価が無くNOT_VERIFIED。v95で3銀行の2026-11-13研究用終値DBS69.90/OCBC28.53/UOB37.75 SGDをそれぞれ2つの第三者履歴サイトで照合し `bank_dated_quote_research` に公開、DBS別サイト70.14の矛盾も記録。単独CI #43530080046、統合 #43530122789/#43530160916 成功。v96で3銀行のSGinvestors株価ページの自動HTML抽出器と負例テスト追加。CI #43530480266 のユニットテストは成功だが実3サイトの機械読み取りはすべてNOT_VERIFIEDのため、ライブ株価は未取得。本体 #43530563069 は成功、v96にSingapore現地の日付に応じた未来日付拒否を追加済み。後続 #43530810735 / #43530810813 / #43530840836 も成功。新しい #43530840912 の結果を確認。UOB11/13のSGX原本、OCBC11/12の原本PDFを引き続き探す。登録7社、算術不整合0、ランキング0。現在株価・最新株式数・時価総額・PER/PBRはNULLを維持。GitHubへ継続実装/検証し、最後に短い引き継ぎ文を添えて。
