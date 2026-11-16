# v544 東証の終値・財務カバー率の実測

[検証コードのコミット](https://github.com/osawamas/value-hunter-ai/commit/b7de8eb4737d7c6f469cb404f1c562f043768b6a) · [東証日報と実APIの検証結果](https://github.com/osawamas/value-hunter-ai/actions/runs/43982019697) · [Android回帰](https://github.com/osawamas/value-hunter-ai/actions/runs/43982019698)

11月16日時点のHachiquant最新年次財務を無料・キーなしで20ページ、3,977件取得。JPX公表の内国普通株一覧（プライム・スタンダード・グロース）と日報2日の終値に証券コードで照合。銘柄別の照合結果は配布せず、検証では集計だけを記録した。

| 立会日 | 対象 | 終値あり | 終値・円建て通期EPS・BPSあり | EPS・BPSがともに正かつ出典IDあり |
|---|---:|---:|---:|---:|
| 2026-10-29 | 3,686 | 3,638 | 3,612 | 3,189 |
| 2026-11-11 | 3,686 | 3,658 | 3,631 | 3,211 |

11月11日の終値・EPS・BPSがそろった内訳は、プライム1,536件、スタンダード1,521件、グロース574件。極洋（1301）はAPIの年次財務の出典ID S100YE8K と個社の開示一覧を突合し、対象期末2026-03-31、有報提出日2026-06-22を確認した。決算短信の2026-05-15とは出典書類が異なる。

`/screener` の `latest_filing_date` は会社側の最新定期提出日で、年次財務を算出した書類の提出日とは限らない。上記件数は最新財務と過去日報が結びつく件数。基準日までの公開を判定するには `source_doc_id` と `/companies/{ticker}/filings` の書類IDを一致させる。株式分割・併合をまたぐ未調整終値と1株指標の株数基準も照合が必要。JPXの定期取得条件とAndroid監視への接続は引き続き調べる。

- [Hachiquant API](https://hachiquant.com/docs) は無料・キー不要。RESTは毎分60回、一覧は200件/ページ。
- [JPX配当落・権利落等情報](https://www.jpx.co.jp/listing/others/ex-rights/) は直近分の補助候補。[統計月報](https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html) の新株落・権利落等一覧は過去分の候補。監視に組み込む前に、権利落日・基準日・効力発生日と対象商品の範囲を区別して確認する。
