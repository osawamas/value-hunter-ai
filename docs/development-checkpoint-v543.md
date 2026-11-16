# v543 日本株の日報と年次財務の照合

- `android-private/tools/jpx_valuation_probe.py` はJPXの日報PDFから立会日と未調整終値を読み、公開済みの年次EPS・BPSと結合する。日報の午後終値を優先し、午後に終値がなければ午前終値を使う。公開日しか分からない開示は翌日以降に使う。重複で矛盾する終値や計算不能な指標は理由を残す。
- [極洋の2026年3月期決算短信](https://www.kyokuyo.co.jp/files/20260501.pdf) の基本EPS 576.02円、BPS 6,511.31円をサンプルとして登録。10月29日・11月11日のJPX日報を用いる回帰試験を追加。テストの出力は実行環境内だけに保存する。
- 出力は年次開示ベースの参考試算。銘柄ごとの最新四半期反映、分割・併合照合、全銘柄の財務自動更新、定期取得の運用確認とAndroid監視への接続は未実装。
- [EDINET DBの開発者向け案内](https://edinetdb.jp/developers) で個社財務には無料キーが必要と確認した。無料枠は1日100回。全銘柄の初回取得とその後の差分更新は分けて検討する。[IRBANK規約](https://corp.irbank.net/terms/) は正規API以外の自動取得を禁止。
- [DataCedarのSGX一覧](https://datacedar.com/markets/sgx) は485銘柄。[API仕様](https://datacedar.com/docs) に無料枠1回3銘柄・毎秒1回とあり、全掲載銘柄で最低162回。公式上場一覧との差分と無料認証後の終値取得率は未実測。
