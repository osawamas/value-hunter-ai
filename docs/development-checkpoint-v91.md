# VALUE HUNTER AI — v91 開発チェックポイント（2026-11-14 JST）

次回は必ずGitHub `osawamas/value-hunter-ai` のmain、最新コミット、GitHub Actions、`docs/data/latest.json`、本ファイルを読んで完了済みの作業を繰り返さない。

## v85〜v91で実装・検証
- v85: 実SGX原本U11（UOB）2026年9月7日の買戻し通知（`SG260907OTHRJM0S`）を直接取得してSection Dの株数を抽出成功。最初はSGXページの『見出しと数字が連続するHTML』を既存v84解析器が誤解析・fail closed。修正をコミットし実SGX Actions #43523537778 成功。控除後1,648,956,591株、自己株式14,160,900株、控除前計算値1,663,117,491株。
- v86: v85原本から抽出成功したときだけ、`bank_primary_share_history` としてUOBの9/7時点の公式履歴を公開。日付・URL・SHA256を含む。市場の現在株式数／株価／時価総額／PER／PBR／ランキングは未変更。単体Actions #43523741173 成功。
- v87: UOBの2026年11月13日付SGXNet転載（SG261113OTHRHOAF）を確認。自己株式控除後1,646,677,591株、自己株式14,548,000株。ただしSGX公式原本のURLがまだ照合できていないため、`bank_share_discovery` へ**未検証の転載候補**として登録。以前の9/30転載（SG260930OTHRNN9Y、控除後1,647,838,591株）は `bank_share_discovery_history` に保持して消さない。単体Actions #43524017333 成功。
- v88: UOBの**2026年11月12日付SGX公式原本**を発見（SG261112OTHRSYPK）。元のSGX URLのID後に64桁のハッシュが付くパターンにもv84原本検証器を対応させた。公式Section Dで自己株式控除後1,646,711,591株、自己株式14,548,000株、控除前1,661,259,591株を直接抽出・算術照合。実SGX Actions #43524255196 成功。
- v89: 11月12日のSGX原本は `bank_primary_recent_share_event` として、これより新しい11/13の未検証転載とは分離して公開。出典URL・HTML SHA256・基準日を保持。単体Actions #43524426426 成功、統合Actions #43524509409 成功。
- v90: 2026年11月10日、11日、12日の**3つのSGX公式原本**を連続して取得し、同一発行体・開示番号・購入日・Section Dの株数を照合。控除後は順に1,646,779,591／1,646,745,591／1,646,711,591株、すべて自己株式14,548,000株。連続日ごとに34,000株減。実SGX＋負例Actions #43524762071 成功。
- v91: v90の3原本チェーンを、各日付・URL・SHA256を保持する `bank_primary_three_day_chain` に追加。v89の11/12原本ハッシュとv90の11/12原本ハッシュ一致、各日算術、11/13転載が未検証のままであること、時価総額・PER・PBR・ランキングが未計算のままであることを検証。単体Actions #43524942596 成功。日本語UIで11/10・11/11・11/12の株数と公式URLを表示。v91の統合 Actions #43525031088 は全工程成功。`docs/data/latest.json` updated_at_utc=2026-11-13T23:11:32.873971+00:00。`bank_primary_three_day_chain` に3つの原本SHA256と正しい11/10-12株式数が公開済み。

## 発見した本物のSGX原本URL（直接実取得・成功）
- 2026-09-07 SG260907OTHRJM0S: https://links.sgx.com/1.0.0/corporate-announcements/XR54CRHWN0U287GV/
- 2026-11-10 SG261110OTHRQ7Q7: https://links.sgx.com/1.0.0/corporate-announcements/Y0NT6GHJQAPLSMVQ/58e79d1d9d9600964459eebacee1ddcafc278a5ae3bfa3fac4da267e7247d75c
- 2026-11-11 SG261111OTHRGYNT: https://links.sgx.com/1.0.0/corporate-announcements/OGJOD7K9GS51JRLV/cab40affb30af649a2f5a37c76072f84a0e1497d6fae97787c4c968bc7c120cc
- 2026-11-12 SG261112OTHRSYPK: https://links.sgx.com/1.0.0/corporate-announcements/MTW96I6ZXZBTQZK8/7c3dc707a598dc02da057fc772c1ba67abe1b9b3ceb4fe9d2b92fd00b510d97d

## 未検証の情報（公式原本と絶対に混同しない）
- UOB 2026-09-30 SG260930OTHRNN9Y、転載（https://classic.shareinvestor.com/news/news.html?nid=515665417&source=sg_sgxnet）、控除後1,647,838,591株。後続の公式原本連鎖で日付変更は確からしいが9/30の原本未確認。
- UOB 2026-11-13 SG261113OTHRHOAF、転載（https://classic.shareinvestor.com/news/news.html?nid=515671689&source=regional_sgxnet）、控除後1,646,677,591株、自己株式14,548,000株。11/12公式原本の1,646,711,591との差は34,000株だが、**11/13原本未照合**。連続した買戻し通知の予測や推測を正式株式数として掲載禁止。
- OCBC 2026-11-12 SG261112OTHRXH64、自己株式利用に関するSGXNet転載。数値は未取得（元の添付 `Anno_12Nov2026.pdf` 未取得）。OCBCの2026年2月公式株数を現在値として流用禁止。
- DBS 2026年2月の株数は公式年報で過去基準日照合済みだが11月時点の最新値未検証。

## 継続品質条件
- 登録7社（S68/G13/S20/S63/D05/O39/U11）、全体の算術不整合0、ランキング対象0を維持。D05/O39/U11の現在株式数・株価・時価総額・PER・PBRはnull。
- 2025年監査済み連結、2026年3Q/9M、2025年同期間との前年比、2026年2月公式年報株数、SGX 9月・11月の買戻し通知はそれぞれ別出典・別の基準日で管理。
- v90連鎖はUOBの11/10〜11/12の原本照合に限り成功。11/13が最新の取引日であるという断定でも、11/14現在の発行済み株数の証明でもない。
- 各ActionsはSGX直取得で403等になった場合にfail closed。途中の統合 #43524200631 は別の財務PDFのHTTP403で失敗したが、後続の #43524476715, #43524509409 は成功。

## 次の作業（v92以降）
1. v91統合Actions #43525031088 は成功済み。次回はGitHub最新版を読み、公開JSONで原本3日分の株式数・銀行3社現在株数null・計算不整合0・ランキング0を維持していることを確認。
2. UOB 2026-11-13 SG261113OTHRHOAF のSGX原本URLを特定して、v84の原本解析器で直接抽出、11/12の原本と連続照合。**SGXNet転載だけでv91の既存公式履歴を上書きしない**。
3. OCBC 2026-11-12 SG261112OTHRXH64 のSGX原本および `Anno_12Nov2026.pdf` を特定し、自己株式移転前後の正式残高・基準日を取得。数値が未取得なら未検証のまま。
4. 正確な取引時刻付きSGX市場株価について、ソースの営業日・通貨（SGD）・時刻・価格種別（直近約定/終値/遅延気配）を検証。買戻し通知の最高/最低取得価格を取引所の現在値・終値として流用しない。
5. 新しいSGX全銘柄への拡張、一般事業会社と銀行の財務指標区別、既存の投資ランキングの保守。

## 新しいスレッドへ貼る文章
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）をv91の続きから再開して。まずmain、Actions、docs/data/latest.json、docs/development-checkpoint-v91.mdを読む。v85でUOBの9/7付SGX公式原本の株数読み取りを実証、v88-v89で11/12付SGX原本から自己株式控除後1,646,711,591株・自己株式14,548,000株を取得して銀行専用の過去株数欄に反映。v90-v91では11/10・11/11・11/12の3原本（それぞれ控除後1,646,779,591／1,646,745,591／1,646,711,591株）を連続日照合し、単体実SGX Actions #43524762071、公開安全CI #43524942596成功。v91統合 #43525031088 は成功。UOBの11/10-12公式原本連続3日分の株数・出典SHA256が公開JSONに保存済み。UOB 11/13付転載株数1,646,677,591株のSGX公式原本は未特定。OCBC 11/12付Treasury Shares通知の原本PDFも未取得。次はこの2つの原本探索と正式株式数照合、時刻付き株価取得の信頼性検証。現在株価・株式数・PER/PBR・ランキングは未検証のままにし、GitHubにテスト/変更を保存して最後に短い引き継ぎ文を付けて。
