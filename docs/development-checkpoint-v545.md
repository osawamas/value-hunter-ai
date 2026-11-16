# v545 100株10万円以内の候補を先に照合

[実装](https://github.com/osawamas/value-hunter-ai/commit/2b3534b2bde668b27cbe8ea075464fd27a0563a8) · [実データ検証](https://github.com/osawamas/value-hunter-ai/actions/runs/43982703753) · [Android回帰](https://github.com/osawamas/value-hunter-ai/actions/runs/43982703782)

東証2026年11月11日の日報とHachiquant 11月16日時点の通期財務から、100株10万円以内、参考PER 15倍以下、参考PBR 1倍以下を抽出。100株価格は日報の当日最終取引値×100で、費用は含まない。参考PER/PBRは通期EPS・BPSがともに正の銘柄のみ。サンプルは市場ごとに銘柄コード順に等間隔で選んだ。

| 市場 | 100株10万円以内 | 財務条件込みの仮候補 | 年次財務の出典書類が取引日前に提出済み |
|---|---:|---:|---:|
| プライム | 220 | 59 | 10/10 |
| スタンダード | 760 | 228 | 10/10 |
| グロース | 358 | 19 | 10/10 |
| 合計 | 1,338 | 306 | 30/30 |

30件は有報・訂正有報の書類ID、銘柄コード、期末日、提出日を照合。結果は全306件の確認を意味しない。取引日当日の提出は時刻未照合のため見送る。株式分割・併合による株数基準の一致、日報の定期取得条件、Android実機での通知は未確認。

## 分割・併合の確認経路

- [JPX統計月報](https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html) の新株落・権利落等一覧は権利落日・基準日・分割比率を掲載。前月分は原則翌月21日以降掲載。
- [JPX配当落・権利落等情報](https://www.jpx.co.jp/listing/others/ex-rights/) は基準日が2週間以内の予定を掲載、過去の公表分は直近4営業日分。日本株の監視では月報の公表遅れを補う資料の継続性と、併合の対象漏れを調べる。
- キーエンスの1→5分割は、[JPX通知](https://www.jpx.co.jp/derivatives/products/individual/securities-options/t13vrt000002k6jv-att/KEYENCECORPORATION_J.pdf) で権利落日11月19日、[発行体公告](https://www.keyence.co.jp/pdf/PressRelease_20261105.pdf) で基準日11月20日、効力発生日11月21日を確認。株価の切替は権利落日を使い、1株指標がすでに遡及調整済みの場合の二重補正を防ぐ。
