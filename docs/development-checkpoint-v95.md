# VALUE HUNTER AI — v95 開発チェックポイント（2026-11-14 JST）

次回は必ずGitHub main、最新Actions、`docs/data/latest.json`、このチェックポイントを読んで再開。完了済みの検証を繰り返さない。

## ベースライン v93
- 2025年監査済み・2026年3Q/9Mの銀行3社財務、年次比較、UOB 2026-11-10/11/12のSGX原本3連続日買戻し履歴は公開。3銀行の現在株数と市場価格はnull、登録7社・算術不整合0・ランキング0。
- 11/13のUOB SGXNet転載に控除後1,646,677,591株と34,000株買戻し取消しの情報。公式11/12の1,646,711,591との差34,000株が一致するが、11/13公式SGX原本のURL未特定。OCBC 11/12 SG261112OTHRXH64は自己株式利用通知で添付Anno_12Nov2026.pdf。公式添付未取得。

## v94：時間付き価格の実取得実験
- `SGX_PDF_connection_probe/u11_ir_quote_probe_v94.py` と `test_u11_ir_quote_probe_v94.py`。UOB investor IR (`https://uob.listedcompany.com/`) に検索エンジン上で2026-11-13 17:14（SGT）のlast-done 37.750 SGDが掲載されている。実ブラウザで見える表示とGitHub Actionsの素のHTMLには差があった。Actionsから取得したHTMLは約2,183 bytes、UOB/quote/last_doneのブロックが無い。取得時刻付き価格のライブ機械取得には使えない。無理に値を昇格せず`NOT_VERIFIED`の診断JSONを出す。
- v94の初期workflowは原本HTML未取得により失敗していたが、ユニットテストと実サイト取得診断を切り離し、サイトが情報非公開ならfail-closedでその事実をサマリーへ記録する。最終CI #43529854142 成功。**実サイトの価格自動解析に成功したという意味ではない**。v94は研究用で、本体公開JSONには価格を追加しない。

## v95：銀行3社の歴史的なSGD終値（参考情報）
- 2026-11-13の履歴価格を複数サイトで照合。DBS D05 69.900 SGD（SGinvestorsとStockAnalysis）、OCBC O39 28.530 SGD（SGinvestorsとStockAnalysis）、UOB U11 37.750 SGD（SGinvestorsとEODData）。資料は第三者の過去履歴で、SGX一次データの生約定記録との独立検証・再取得の自動化は未完。
- DBSについてInvesting.comには同じ日付に70.14の表示があり、69.90と矛盾している。`bank_quote_research_v95.py` ではこの不一致を明示し、別の2サイトが一致する69.90はあくまで研究用候補とする。
- `bank_dated_quote_research.status=DATED_2026_11_13_THIRD_PARTY_PRICE_RESEARCH_NOT_LIVE` に `historical_trade_date=2026-11-13`、通貨SGD、研究用終値、2つのURL、固定スナップショットで自動更新されないこと、現在時価総額・PER/PBR/ランキング利用不可を保存。`price_sgd`, `shares_outstanding`, `market_cap_sgd`, `per_reference`, `pbr_reference_unverified`, `pbr_verified` はnullのまま。
- UIの銀行別『株価調査』欄で日付・2情報源・不一致・自動更新未対応を表示。`test_bank_quote_research_v95.py` が3社カバレッジ、データ未昇格、別資料の矛盾、数値改変、重複、株価混入を検証。単独 Actions #43530080046 成功。
- `.github/workflows/value-hunter-v29.yml` にv95ユニットテストと公開JSONへの研究データ付与を統合。統合Actions #43530122789 はこの記録時点で実行中、#43530160916 はpending。次回最初に確認し、成功していない場合はエラーを修正して完走させる。

## 見つかった株価資料URL
- DBS https://sginvestors.io/sgx/stock/d05-dbs/share-price-history と https://stockanalysis.com/quote/sgx/D05/history/
- OCBC https://sginvestors.io/sgx/stock/o39-ocbc-bank/share-price-history と https://stockanalysis.com/quote/sgx/O39/history/
- UOB https://sginvestors.io/sgx/stock/u11-uob/stock-info と https://www.eoddata.com/stockquote/SGX/U11.htm
- DBSの不一致 https://www.investing.com/equities/dbs-group-holdings-historical-data

## 次回（v96以降）の優先課題
1. `43530122789` と `43530160916` の実行完了結果と docs/data/latest.json の研究価格3社登録・現在株価null・ランキング0を確認。
2. 現在の株価を本当に自動取得するには、信頼できる時刻/価格種別/SGD/ソース表示（delayedかexchange officialか）、実サイトからの安定した機械取得、休日や場中・場後の新旧区別、2ソースでの齟齬を検証。研究用静的スナップショットと別系統にする。
3. UOB 2026-11-13 SG261113OTHRHOAFのSGX公式URL、OCBC 2026-11-12 SG261112OTHRXH64のSGX原本・Anno_12Nov2026.pdfの探索。インターネット検索に出た転載のURLを公式と詐称しない。
4. 最新株数を正しい基準日で確定できるまで時価総額・PER・PBR・投資ランキングは算出しない。SGX全銘柄への拡張を継続。

## 次スレッド用コピペ
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）の開発をv95の続きから再開して。まずmain、Actions、docs/data/latest.json、docs/development-checkpoint-v95.mdを確認。v94でUOBのIRに2026年11月13日17:14時点37.750SGDの表示を確認したが、GitHub Actionsの取得HTMLには価格ブロックが無く、実サイト自動抽出はfail-closed。最終CI #43529854142成功だが価格取得成功ではない。v95で3銀行の2026-11-13過去終値を2つずつの第三者履歴サイトから比較：DBS69.90 SGD、OCBC28.53、UOB37.75。DBSはInvesting.comの70.14という不一致も明示。研究専用 `bank_dated_quote_research` とUI欄を追加、現在株価・株数・時価総額・PER/PBR・ランキングは全て未検証のまま。v95単独CI #43530080046成功、統合 #43530122789・#43530160916の完了を最初に確認。UOB11/13 SG261113OTHRHOAF原本とOCBC11/12 SG261112OTHRXH64公式PDFは未取得。次は安定した時刻付き株価自動取得と両原本探索、GitHubで実装/テスト継続。最後に引き継ぎ文を付ける。
