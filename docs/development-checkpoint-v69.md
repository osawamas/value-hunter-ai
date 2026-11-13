# VALUE HUNTER AI — v69 開発チェックポイント / 次スレッド引き継ぎ

記録日: 2026-11-14 JST。別スレッドでは最初に GitHub main/最新コミット/Actions/docs/data/latest.json を読み込んでから、このファイルを参照する。既に成功した作業をやり直さない。

## v63〜v69 実装済み
- v63: DBS Group (D05) の FY2025/FY2024 監査済み公式 Annual Report PDF 58ページから銀行専用損益8項目を抽出。2025年の総収益22,900、純金利収益14,500、親会社株主帰属利益10,933（百万SGD）。収益内訳・親会社帰属利益+非支配利益=純利益の算術検証を実装。PDF独立取得ワークフロー #43511573502 成功。
- v64: 同 Annual Report の連結（Group）貸借対照表から FY2025 総資産897,488、負債828,572、親会社株主持分68,867、非支配持分49、総純資産68,916（百万SGD）を取得。2024年度分も取得し、assets-liabilities=equity、parent+NCI=total equity を検証。実PDFワークフロー #43511852681 成功。
- v65: D05の財務・貸借・2026-02-10時点の自己株式控除後株式数の3解析を1回の公式PDFダウンロードに統合。厳密な出典SHA256/期間/財務単位/算術/非ランキング照合を行い、docs/data/latest.json の D05 レコード内 banking_evidence にのみ掲載。現時点の株価・時価総額/PER/PBRはnull。単体CI #43512207291 成功。日本語UIの銀行専用詳細欄も実装済み。
- v66: O39 OCBCとU11 UOBの公式FY2025年次報告書についてGroup銀行損益・貸借のページを探索。PDF実取得のActions #43512809603 成功。OCBCのGroup分析/ハイライトはPDF98頁、直接財務諸表は約125・127頁。UOBの5年Group概要はPDF45頁、損益諸表は約137頁。
- v67: O39の年次報告書PDF98頁の財務ハイライトから2025/2024の総収益14,614/14,473、純金利収益9,150/9,755、株主帰属利益7,422/7,587、総資産675,688/625,050、親会社株主持分61,768/59,316（百万SGD）を抽出。実PDF Actions #43513183675 成功。管理側のGroupサマリーであり、監査済み財務諸表各行との独立突合は未完。
- v68: U11の年次報告書PDF45頁のGroup5年サマリーから2025/2024の総収益13,808/14,294、営業利益7,651/7,984、株主帰属利益4,682/6,045（百万SGD）を抽出。総資産は572/538、株主持分は51/50（十億SGD丸め値）として別単位で管理。実PDF Actions #43513386420 成功。丸め値から正確なPBRを計算しない。
- v69: O39/U11の年次サマリーを銀行専用 banking_summary に出典SHA256/期間/単位/未検証をつけて公開JSONに追加。一般企業用売上高/営業利益率や株価・PER・PBR・ランキングは変更せず、銀行専用UIを表示。集計統合 Actions #43513765728 は全工程成功。

## 最終実データ確認
- docs/data/latest.json updated_at_utc=2026-11-13T21:48:08.324061+00:00。
- SGX登録7社 S68/G13/S20/S63/D05/O39/U11。金融新規3社の株価・PER・PBRはnull、ranking_eligible=false。
- 公開D05 banking_evidence.status=BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED、2025総収益22,900、総資産897,488。
- 公開O39銀行summary.status=ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024、2025総収益14,614、総資産675,688（百万SGD）。
- 公開U11銀行summary.status=ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024、2025総収益13,808（百万SGD）、資産/持分のunitはSGD_billions_rounded。
- data quality: 登録7、株価未取得3、計算不整合0、自己株式不整合0、ランキング対象0。

## 重要な未解決・次の v70 以降
1. O39の年次報告書 Group audited income statement (PDF約125頁) と balance sheet (約127頁) を直接抽出し、既存のハイライト値と各項目照合。同一発行体・別表の照合であり第三者独立検証ではない。
2. U11の監査済み正式連結BSおよび損益明細を取得、丸め十億SGD資産・株主持分を正確な百万SGDに置換してからPBR分母の候補にする。ただし市場データと独立検証が揃うまで実際のPBRはnull。
3. D05/O39/U11の2026年の株式数・自己株式控除・株価時刻の公式根拠を追加。2026年2月10日DBS株式数は歴史的資料であり、現在値として流用禁止。
4. 銀行専用の収益・費用・NIM/ROE/NPLなど評価ロジックを慎重に設計。一般企業の『営業利益率』を銀行に流用しない。
5. 一時的HTTP403はアクセス拒否として即時停止。429/5xxの限定再試行だけ使う。公式PDFが取得できないときは銀行専用項目を無理に更新せず、一般SGX処理の継続を優先。
6. GitHub Pages初期設定はレポジトリ所有者が Settings > Pages > Build and deployment > GitHub Actions で有効化する必要あり。Actions成功は公開サイト稼働を意味しない。
7. 次回も修正/テスト/実PDF/公開JSON/GitHubコミットを続け、最後に次スレッドへ貼る短い引き継ぎ文を付ける。

## 短いコピペ用
VALUE HUNTER AI（GitHub osawamas/value-hunter-ai）のv69から開発を続けて。まずmain、最新Actions、docs/data/latest.json、docs/development-checkpoint-v69.mdを読む。v63-v65でDBSの銀行専用損益・貸借・歴史的株式数を1つの公式PDFから検証し公開JSONへ掲載。v66-v69でOCBC・UOBのFY2025/2024銀行財務ハイライトも公式PDFから抽出して別欄に反映した。直近の統合Actions #43513765728 は成功。SGX登録7社、計算不整合0、ランキング採用0。金融3社の株価・PER・PBRは未取得。次はOCBC/UOBの監査済みGroup損益・BSを正確に抽出してハイライトと照合し、銀行財務の定義/精度を強化する。既存データを壊さず、偽の値を出さず、GitHubに継続コミット。最後に短い引き継ぎ文を付ける。
