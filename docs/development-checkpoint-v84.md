# VALUE HUNTER AI — v84 継続開発チェックポイント

作成日: 2026-11-14 JST。次回は必ず GitHub main、最新Actions、docs/data/latest.json を読み直してから着手。確認済み作業を繰り返さない。

## v83 完了
- v82 までに DBS(D05), OCBC(O39), UOB(U11) の2025年監査済み連結財務、2026年3Qと9M、同年/前年同期間比較を銀行専用フィールドに公開。3銀行の実際の取引時刻付き市場株価と現在株数は依然未検証、トップレベル price_sgd/shares_outstanding/market_cap_sgd/PER/PBR はnull。
- ウェブ調査でUOBの2026-09-30付SGXNet転載（Announcement Reference SG260930OTHRNN9Y）を発見。Section Dの自己株式控除後は1,647,838,591株、自己株式残高14,548,000株、両者の合計は1,662,386,591株。ただし**原本の公式 SGX corporate-announcement URLを確認できていない**。転載ページ https://a.siasset.com/news/news.html?nid=515665417&source=regional_sgxnet 。これは2026-11-14現在値と証明されたものでもない。
- OCBCの2026-11-12付「Notice of Use of Treasury Shares」Announcement Reference SG261112OTHRXH64、17:41 SGXNet転載を発見。転載ページ https://classic.shareinvestor.com/news/news.html?nid=515671461&source=sg_sgxnet 。**公式添付PDFの数値未取得**。10/20〜11/12に複数回の自己株式移転通知があり、2026年2月の古い株数を現在値として使わない。
- `SGX_PDF_connection_probe/bank_share_leads_v83.py` を新設。UOBの9月株数を `bank_share_discovery.candidate_shares_excluding_treasury`、OCBCの11/12通知を数値不明の調査項目として登録。status=SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED、primary_sgx_announcement_url=null、primary_document_sha256=null、primary_issuer_count_reconciled=false。**評価指標には利用不可**。
- `docs/app.js` は転載候補の株数と未検証理由を明示。`test_bank_share_leads_v83.py` では外部転載値から本番株式数・時価総額・ランキング資格を作れないこと、過去日付が新しい別開示より古い場合エラーにすることを検証。単独 Actions #43522149304 成功。統合 Actions #43522229675 成功。公開 `docs/data/latest.json` updated_at_utc=2026-11-13T22:50:04.799686+00:00 でOCBCとUOB調査欄の存在を確認。

## v84 完了
- `SGX_PDF_connection_probe/sgx_primary_buyback_v84.py` を新設。`https://links.sgx.com/1.0.0/corporate-announcements/<ID>/` のHTTPS直接SGX原本URL、発行体名、SGXNet announcement reference、日次買戻し種別、購入日、Section Dの『Number of issued shares excluding treasury shares after purchase』・『Number of treasury shares held after purchase』をすべて照合する解析器。
- 取得URLのリダイレクトやSGX偽ドメイン、本文のscript混入、他社、間違った日付、重複・不明な数値を拒絶。取得できても `DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY` として診断するだけで、現在株式数やPER/PBRには昇格させない。
- `test_sgx_primary_buyback_v84.py` で合成HTMLフィクスチャに対する正例・負例を追加。CI #43522622145 成功。main SGX dashboard testsにも組込済み。
- **重要：UOBおよびOCBCの銀行固有の SGX原本アナウンスURLはまだ見つかっていない。v84テストは合成HTMLだけ。銀行のSGX実原本に成功したと主張しないこと。**

## 状態と参照
- latest公開JSON 7社、数値不整合0、ランキング対象0、銀行株価・現在株式数null。v83の二次ソース調査欄以外は従来の財務・YoY指標を維持。
- v84コードmain統合実行 #43522708725 はこのチェックポイント作成時点で実行中。次回の最初にジョブの成功/失敗を確認し、必要なら修正する。v84単独CI #43522622145 は成功。
- v76のOCBC 2026-02-25控除後株式4,490,912,507、UOB 2026-02-23控除後1,651,589,183、DBS 2026-02-10控除後2,837,558,046は過去基準日。UOBの9/30候補もSGX原本照合前。財務データ・過去株数・市場価格の基準時点を絶対に混同しない。

## 次の優先事項（v85以降）
1. 2026年11月付SGX原本 UOB/OCBC の corporate-announcements URL を正しく発見し、v84の公式HTML解析器で日付・発行体・買戻し後株数を確認する。SGXNet announcement referenceで検索するときは、UOB SG260930OTHRNN9Y、OCBC SG261112OTHRXH64 を使う。二次転載ページを原本URLとして扱わない。
2. OCBCの連続した自己株式利用通知から最新の株数を得るには、すべての関連変更と基準日を追う。2026-02-25株式数から無検証の差分積算をしない。UOBの9/30イベントも11月現在の最新を保証しない。
3. 3銀行の正式時刻付きSGX価格ソースと取得履歴の安定化。時刻・営業日・取引通貨・訂正有無を取得し、別ソースで検証。株数+株価+財務独立検証まで時価総額/PER/PBRや投資ランキングを出さない。
4. main Actions #43522708725 を最初に確認。新規ソースの権限拒否・エラーはfail-closedで既存データを保つ。
5. 7社からSGX全銘柄への拡張は未完。既存産業銘柄のランキング基準の品質を落とさない。

## 次スレッドに貼る文章
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）のv84の続きから開発を再開して。まずmain、Actions、docs/data/latest.json、docs/development-checkpoint-v84.mdを読む。v83でUOBの2026-09-30付株数候補（自己株式控除後1,647,838,591、自己株式14,548,000）をSGXNet転載から見つけ、OCBCの2026-11-12付自己株式利用通知 SG261112OTHRXH64 も発見。ただし公式原本のURL/添付数値が未照合なので両方とも `bank_share_discovery` に未検証として掲載、現在株数・株価・時価総額/PER/PBRには不採用。v84でSGX原本専用のHTML/Section D診断解析器と負例テストを実装し単独CI #43522622145 成功、銀行原本での実証は未完。main統合 #43522708725 の結果を確認してからUOB/OCBCの原本検索・正式株式数の照合と時刻付き市場株価検証を継続。未検証値はランキング対象にしない。GitHubに保存して次回引き継ぎ文を添えて。
