# v550 保留銘柄の不足月と前年資料を照合

[実装](https://github.com/osawamas/value-hunter-ai/commit/4af3160ba346f2eb542a86df6d28610988d1a8db) · [実データ検証](https://github.com/osawamas/value-hunter-ai/actions/runs/43987659114) · [Android回帰](https://github.com/osawamas/value-hunter-ai/actions/runs/43987659111)

11月11日終値の仮候補サンプル30件を再照合。株数基準変更3件、資料不足27件。保留銘柄ごとの不足を取引日の月まで数える処理を追加。

- JPXの[2025年アーカイブ](https://www.jpx.co.jp/markets/statistics-equities/monthly/00-archives-01.html)から10〜12月分を追加し、64件を抽出。前年の不足が残る銘柄は8件から3件に減少。
- 27件すべてに2026年10月・11月分が必要。うち9件は[2026年1月分](https://www.jpx.co.jp/markets/statistics-equities/monthly/t13vrt000000nwgb-att/17_kenri2601.pdf)、そのうち3件は[2025年9月分](https://www.jpx.co.jp/markets/statistics-equities/monthly/um3qrc0000027wd5-att/17_kenri2509.pdf)も必要。1月・9月は公式PDF公開済みで、行座標の解析を修正する。2026年10月・11月の月報は検証時未掲載。
- 次回は公開済み2資料の読み取りと、未掲載期間の個別照合を優先。日次Excel、JPX信用取引の権利処理一覧、発行会社・TDnetの開示は個別イベントの確認に用いる。対象外・未取得を理由に保留を解除しない。Android実機の自動通知は未接続。
