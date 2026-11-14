# VALUE HUNTER AI — v102 開発チェックポイント（2026-11-14 JST）

次回は GitHub `osawamas/value-hunter-ai` main / 最新コミット / GitHub Actions / `docs/data/latest.json` / `docs/data/sgx-universe-candidates.json` / 本ファイルを最初に読み、完了済み作業を繰り返さない。

## v96までの前提
- 2025年監査済み連結決算と2026年3Q/9M/前年同期比の銀行3社財務、UOBの11月10〜12日付 SGX原本連続買戻し株式数履歴は公開済み。
- UOB 11/13 SG261113OTHRHOAFはSGXNet転載の算術が前日と一致するが原本未照合。OCBC 11/12 SG261112OTHRXH64の添付PDF `Anno_12Nov2026.pdf` のSGX原本未取得。
- 銀行D05/O39/U11の2026-11-13参考過去終値（DBS69.90、OCBC28.53、UOB37.75 SGD）は第三者の研究値で、現在の株価やPER/PBRに未採用。v96の実株価スクレイパは3銀行とも原サイトからの識別+時刻検証ができず NOT_VERIFIED。ランキングは0件。

## v97: SGX銘柄候補のアルファベット順HTML取込
- `SGX_PDF_connection_probe/sgx_universe_candidates_v97.py` とテスト、`.github/workflows/value-hunter-v97.yml` を作成。SGinvestorsの https://sginvestors.io/sgx/stock-listing/alpha を実HTTP取得し、ticker重複/7既存銘柄の漏れを拒否する診断。
- 単独Actions #43532807718 はテスト成功、**しかし実サイトHTMLが候補タイトルを含まず `NOT_VERIFIED`**。候補の公開には使用していない。

## v98: 認証不要の企業一覧JSON API
- StocksSGの公式ドキュメント https://stocks.com.sg/developers で `GET /api/v1/companies` は認証不要のFree枠10 requests/min、JSON `data[]`, `meta` を確認。
- `SGX_PDF_connection_probe/sgx_companies_api_v98.py` と負例テストで https://stocks.com.sg/api/v1/companies を実際に取得。デフォルト50件のうち49社の有効候補を解析、出典SHA256を記録。CI #43532996874 成功。これもSGX取引所公式の一覧ではなく第三者API。

## v99: 独立した候補台帳
- `SGX_PDF_connection_probe/sgx_companies_publish_v99.py` とテストを実装。企業一覧を verified `docs/data/latest.json` に直接追加せず、`docs/data/sgx-universe-candidates.json` に別ファイルとして書く。rawRows、accepted/rejected、出典URL・SHA256、既存7社との重複数、第三者候補・SGX完全性未確認・ランキング利用不可を厳格に表示。
- `.github/workflows/value-hunter-v29.yml` に企業一覧別ファイルの生成・コミットを追加。受信不可なら既存候補スナップショットを維持し、公式全銘柄や検証済み7社のデータと混ぜない。CI #43533172814 成功、初回統合 #43533257927 成功。

## v100: 日本語候補検索画面
- `docs/index.html` に『SGX銘柄候補台帳』セクションを追加し、検証済み7社の銘柄スクリーナーとは区別。`docs/universe.js` で別sidecar JSONを読み込み、重複/検証状態/候補数をチェック、銘柄コード・企業名の検索ができる。1回表示最大100件（候補数そのものは全件のまま）。
- `docs/test_universe_v100.js` は偽の完全網羅表記、銘柄重複、データ昇格、壊れた件数を拒否。Actions #43533490777 成功。`.github/workflows/value-hunter-pages.yml` にJS構文・このテストを追加。GitHub Pages初期有効化は依然repo Settings→Pages→GitHub Actions で所有者設定が必要。Pages検証成功だけで公開URLの動作保証ではない。

## v101: 企業一覧の件数指定を実サイトで検証
- `sgx_companies_pagination_v101.py` を実行し、3リクエスト以内で`default`, `?page=2`, `?limit=200`を比較。CI #43533659962 全工程成功。
- 実API meta はデフォルト `count=50,total=183,limit=50,offset=0,next_offset=50`、page=2は**無視され同じ49有効候補**、`limit=200`は `count=183,total=183,limit=200,next_offset=null` となり**182有効候補**が返ることを確認。第三者企業カタログ183件とSGX全上場銘柄の数は同義ではない。

## v102: 182銘柄候補に拡張、実装・テスト・公開済み
- `sgx_companies_api_v98.py` の本番取得URLを `https://stocks.com.sg/api/v1/companies?limit=200` に変更。`sgx_companies_publish_v99.py` は正確なURLを照合し、provider reported total・除外行数・next offsetを保持。
- `test_sgx_companies_expanded_v102.py` を追加、CI #43533855051 成功。
- 初期の並行pushによる統合Actions #43533763117 はv98/v99ソースURL変更の一時的な不一致で2テストが失敗。その後の #43533789003 はユニットテスト〜公開JSON更新・コミットまで**全工程成功**。
- `docs/data/sgx-universe-candidates.json` の実測: 182候補、API報告183件・除外1件、検証済み7社とのコード重複7社（すべて含む）、source_urlは`https://stocks.com.sg/api/v1/companies?limit=200`、generated_at_utc=`2026-11-14T00:23:58.352694+00:00`。`full_sgx_listing_completeness_verified=false`、`eligible_for_ranking=false`。
- `docs/data/latest.json` は引き続き登録7社、算術不整合0件、ランキング適格0件。銀行の price_sgd、shares_outstanding、market_cap_sgd、PER/PBRはnull。候補182社をこの評価対象に加算したとは主張しない。

## 次の優先タスク（v103〜）
1. GitHub main、最新Actions、公開sidecar 182社が維持されているかと Pages validate を確認。必要ならフロント画面の日本語表示とテーブル100件制限を調整。
2. StocksSG APIの除外1行の理由・`is_active`、`delisting_date`、銘柄種別やboardを調査し、上場廃止・非アクティブ・重複表記を候補情報で明確に区別。第三者の is_active をSGX公式確認と誤認させない。
3. SGXの公式取引所発行体/証券マスターを取得可能か調査し、182件はあくまでStocksSGの一部でSGX全銘柄ではないことを維持。最終的には原本確認済みの銘柄のみ財務検証ラインに追加。
4. UOB2026-11-13 SG261113OTHRHOAF原本、OCBC2026-11-12 SG261112OTHRXH64の公式添付Anno_12Nov2026.pdfを探し、実文書の基準日・発行済株数を検証。
5. 時間付きSGD株価の信頼できる自動データ取得と二重照合を継続。財務・株価・現在株式数が未検証ならPER/PBRとランキングを有効化しない。

## 次スレッド用コピー文章
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）をv102の続きから開発して。まずmain、最新Actions、docs/data/latest.json、docs/data/sgx-universe-candidates.json、docs/development-checkpoint-v102.mdを読む。v97でSGinvestorsのアルファベット順一覧を試したがActions実HTMLはNOT_VERIFIED。v98でキー不要のStocksSG会社一覧APIを実HTTP検証して既定50件・49有効候補取得。v99で候補を検証済み7社の財務ランキングと別sidecarに保存。v100で日本語の検索台帳UI（上限100件表示）追加し単独JS CI #43533490777 成功。v101でAPIのpage=2は無視されるがlimit=200なら183行返すことを実証。v102で取得をlimit=200へ変更、sidecarを182社に拡張（183件中1件は形式不備で除外、元の検証済み7社すべて候補一覧に含む）。v102 CI #43533855051、全体統合 #43533789003 成功。候補182社はSGX公式の全上場社数ではなく第三者台帳・財務未検証で、投資ランキング対象は依然0。次に除外1行と非アクティブ/上場廃止のprovider属性を検証、公式SGX銘柄マスターを探し、UOB11/13・OCBC11/12 SGX原本探索と日時付き株価の安定取得も進める。完了済み作業は繰り返さず、GitHubで実装・テスト・データ公開し最後に短い引き継ぎ文を添える。
