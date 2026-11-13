# VALUE HUNTER AI — v76 開発チェックポイント（2026-11-14 JST）

再開前に GitHub main／最新コミット／Actions／docs/data/latest.json を必ず確認し、完了済み作業のやり直しを避ける。

## 今回 v73〜v76 で実装
- v73: D05/O39/U11 の公開データに `bank_financial_state.status=AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED` を導入。銀行専用の2025年監査済み連結財務が解析済みであることを正確に表示。`financial_source_kind=REGISTERED_SOURCE_NOT_PARSED` と一般企業向け `FINANCIAL_MISSING_*` は投資用共通スキーマに残すが、UIでは銀行固有の財務解析・一般企業用指標非適用・市場データ未検証を区別。銀行3社とも参考ROE/経費率は v72 から利用可能。市場株価/PER/PBRは null のまま。
- v74: O39/U11 の2025年年次報告書内の2026年2月時点の株式数・自己株式数を調査。O39は公式PDFの256ページ、U11は237ページ。資料の取得元URL・基準日・数値のあるテーブルを実PDFで確認。診断CI #43517545321 成功。
- v75: O39/U11公式年次PDF内の自己株式控除を厳密に自動抽出。日付、発行体、表の見出し、子会社保有なし、株式数内訳、控除算術、公式資料からの数値回帰を要求。偽の過去日付・違う株式数・子会社持分・重複をエラーにする。最終実PDFCI #43518059712 両銘柄成功（途中の失敗 #43517859673/#43517950160 は正規表現テストを修正済み）。
- v76: 上記2銘柄の株式数を `bank_historical_shares` にだけ公開。年次報告書を監査済みGroup財務のPDFと同一SHA256・URLで照合。トップレベルの現在株式数、株価、時価総額、PER/PBR、ランキング適格フラグは変更禁止。負例テストCI #43518276975 成功。統合更新 #43518346582 成功し `docs/data/latest.json` に反映済み。UIに過去基準日・自己株式控除式・不採用理由を表示。

## 公式PDFに基づく歴史的株数
- O39（OCBC）2026-02-25時点：発行済株式数（自己株式含む）4,501,436,229、自己株式10,523,722、控除後4,490,912,507（計算値）。PDF256ページ。source: https://www.ocbc.com/iwov-resources/sg/ocbc/gbc/pdf/investors/annual-reports/2025/2025-annual-report-en.pdf
- U11（UOB）2026-02-23時点：自己株式控除後1,651,589,183、自己株式15,243,008、控除前1,666,832,191（計算値）。PDF237ページ。source: https://www.uobgroup.com/investor-relations/assets/pdfs/investor/annual/uob-annual-report-2025.pdf
- D05（DBS）2026-02-10時点：控除後2,837,558,046、自己株式113,424の資料はv62-v65で既に `banking_evidence.historical_shareholding` に公開済み。これも現在値ではない。
- 2026-11-14現在では上記3件は過去資料。2026年11月の時価総額を計算するためには、新しい発行済株式数と取引時刻が付いた株価の厳格な検証が必要。

## 公開データ実測
- `docs/data/latest.json` updated_at_utc=2026-11-13T22:20:16.274478+00:00。対象 S68/G13/S20/S63/D05/O39/U11 の計7社、算術不整合0、自己株式不整合0、ランキング適格0。新規銀行3社の株価・PER/PBRは依然 null。`bank_financial_state` は3社すべて解析済み。
- #43518381927 は本チェックポイント記録時点で実行中の再走（最初に最新結果を確認する）。#43518346582 の成功データを確認済み。

## 2026年3Qの新しい公式ソース（未解析・次の調査対象）
- D05: DBS 2026-11-05公表3Q26 SGX: https://links.sgx.com/1.0.0/corporate-announcements/PWUTJ371L9ASOMF8/3044419f7294ad033fa90ebb2386da5245d415e663ece3af98d4448469034599
- O39: OCBC 2026-11-06公表3Q26 SGX: https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/ （結果: https://www.ocbc.com/group/media/release/2026/ocbc-group-third-quarter-2026-results.page）
- U11: UOB 2026-11-04公表3Q26 IR: https://www.uob.com.sg/investor-relations/financial/index.html （PDF例: https://www.uobgroup.com/investor-relations/assets/pdfs/investor/financial/2026/cfo-slides-3q-2026.pdf）
- これらの最新資料へのリンクは調査済みだが、**最新株式数／株価／3Qの財務値としてアプリに取り込んだわけではない**。各ソースの実PDF構造、連結範囲、四半期vs累計、株式数基準日を個別に検証してから追加すること。

## 次回優先課題
1. GitHub Actions #43518381927 の終了結果とmainの最新版を確認。
2. DBS/OCBC/UOBの3Q2026公式PDFから2026-09-30の連結財務指標を日付・期間付きで追加。年次2025と3Q/9M2026を同一単位や同一期間であるかのように混ぜない。
3. 新しい公式株式数基準日、自己株式控除、信頼できる価格ソース・時刻を探す。株価取得が安定していない場合は未取得のままにしてランキングを有効化しない。
4. 一般事業会社の財務項目未取得理由と銀行専用検証済み状態をさらに明瞭にし、SGX全銘柄への拡張を進める。
5. GitHub Pages公開はリポジトリ所有者による一度限りの Settings > Pages > GitHub Actions 有効化が必要。GitHub Actionsのデータ検証成功とは別。

## 次スレッドに貼る短い文章
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）のv76の続きから開発を再開して。main、Actions、docs/data/latest.json、docs/development-checkpoint-v76.mdをまず読む。v73でDBS/OCBC/UOBの銀行専用連結財務を『解析済み・株価未検証』とUI表示。v74〜v76でOCBC/UOB年次報告書から2026年2月の自己株式控除を公式PDFで抽出し、過去株数として公開。OCBC控除後4,490,912,507株、UOB控除後1,651,589,183株。実PDF/統合CIは成功 #43518059712/#43518346582。対象7社、算術不整合0、投資ランキング0。次は3銀行の公式3Q26決算を日付・四半期/累計区分付きで自動解析し、2026年のより新しい株式数と信頼できる株価を探す。未検証数値を時価総額/PER/PBRに使わず、GitHubに成果を保存。最後に短い引き継ぎ文を付ける。
