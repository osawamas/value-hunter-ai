# VALUE HUNTER AI — v80 継続開発チェックポイント

作成: 2026-11-14 JST。次回は GitHub mainの最新コミット、Actions、docs/data/latest.json をまず再取得する。完了した工程を繰り返さない。

## 今回 v77〜v80 で実装・検証
- v77: D05 DBS／O39 OCBC／U11 UOBの公式2026年9月30日終了の第三四半期開示PDFを特定し、各社1ファイルを取得。`bank_q3_2026_probe_v77.py` で日付・発行体・期末・表ページを診断専用として抽出。個別CI #43519488424 全3銀行成功。ソース: DBS SGX FileOpen ID910439、OCBC SGX FileOpen ID910569、UOB 2026年3Q CFO presentation PDF。
- v78: `bank_q3_table_probe_v78.py` で実PDFの表列を調査。DBSはPDF7頁でQ3/9M混在、OCBCはQ3がPDF2頁、9MがPDF4頁、UOBはPDF3頁で9M/Q3混在。CI #43519606976 成功。
- v79: `bank_q3_financials_v79.py` に発行体ごとの厳格なPDF抽出、収益／純金利収益／費用／最終利益の既知値回帰、出典SHA256、Q3(2026-07-01〜2026-09-30)と9M(2026-01-01〜2026-09-30)の期間スキーマ、グループ内算術検証を実装。UOBの9M合計には開示単位百万SGDにおける1百万SGDの端数調整差を明示し1以内のみ許容。違う年度、改変値、重複等を負例テスト。実PDF＋単体テスト CI #43520312306 の3社全ジョブ成功。途中の失敗ジョブは fixture と正規表現を修正済み。
- v80: `bank_q3_publish_v80.py` がソース識別・状態・年度・期間・単位・算術を独立確認した場合のみ、公開JSONの `banking_interim_2026` に Q3 と nine_months を別スロットに保存。FY2025監査済み資料、株価、株式数、時価総額、PER/PBR、ランキング資格は一切変更しない。`docs/app.js` に銀行のQ3/9M別表示、PDFページと公式出典SHA256、未検証表示を追加。安全テスト CI #43520691032 成功。統合CI #43520690947 も完走成功。公開JSON docs/data/latest.jsonで3銀行のQ3/9Mを全て確認。

## 公開済み最新の四半期データ（SGD百万）
| 2026年3Q | D05 DBS | O39 OCBC | U11 UOB |
|---|---:|---:|---:|
| Q3総収益 | 5,845 | 3,733 | 3,381 |
| Q3純金利収益 | 3,711 | 2,313 | 2,278 |
| Q3最終利益 | 2,813 | 2,042 | 1,250 |
| 9M累計総収益 | 17,886 | 11,731 | 10,398 |
| 9M累計純金利収益 | 10,786 | 6,798 | 6,900 |
| 9M累計最終利益 | 8,822 | 6,237 | 4,165 |

## 公開データと安全条件
- `docs/data/latest.json` updated_at_utc = 2026-11-13T22:37:21.385150+00:00。登録7社、算術不整合0、自己株式不整合0、ランキング対象0。新規銀行3社の current price/current shares、market cap、PER、PBR はすべてnull。
- 2025年の銀行監査済み連結通期データは `banking_audited` (O39/U11) か `banking_evidence` (D05)。2026年3Q+9Mの取引アップデートは `banking_interim_2026`。2026年2月の自己株式は `bank_historical_shares` (O39/U11) と D05の historical_shareholding。絶対に通期と累計、過去株数と現在株数を混ぜない。
- 公式PDFの数値回帰は同一発行体の記載との照合であり第三者独立数値検証ではない。ランキング有効化禁止。
- GitHub Pages有効化はGitHubリポジトリ所有者が Settings > Pages > Build and deployment > GitHub Actions で設定する必要あり。Actions成功はサイトURLの公開成功を意味しない。

## v81以降の優先課題
1. まず main/latest Actions/docs/data/latest.json から更新確認。既に成功した #43520690947 を繰り返さない。
2. 3銀行について Q3/9M の前年同期値を PDF から同一期間区分で抽出し、前年比・費用率・銀行NIMなどの期間別指標を安全に算出。Q3を9MやFYと比較した偽の成長率を出さない。
3. 2026年11月に近い発行済株式数と自己株式残高を公式開示で更新・照合。D05/O39/U11の2026年2月の数値を現在値に使用禁止。
4. 信頼できるタイムスタンプ付き市場株価、データ取得元、SGD表示を検証。quote+shares+財務独立検証までは時価総額/PER/PBRと投資ランキングに採用しない。
5. SGX全銘柄の機械的な公式一覧取得と取引所情報の安定性評価。銀行専用ロジックを一般企業の売上／営業利益率へ流用しない。

## 次スレッド用コピペ
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）を v80 の続きから開発して。まずmain、最新Actions、docs/data/latest.json、docs/development-checkpoint-v80.mdを確認。v77/v78でDBS・OCBC・UOBの2026年Q3公式PDFを取得し表構造を特定。v79で実PDFから Q3(7-9月) と9M(1-9月累計)を厳密に別解析し、#43520312306 で全3社のテスト成功。v80で銀行専用の banking_interim_2026 として公開JSON/日本語画面に反映し、統合Actions #43520690947 成功。登録7社、算術不整合0、ランキング0。次は前年同期間比を正しい期間対応で算出する機能、より新しい株式数と検証済み株価の取得。既存の2025年通期や株価・PER・PBR・ランキング判定を壊さず、成果をGitHubにコミットして最後に短い引き継ぎ文を付けて。
