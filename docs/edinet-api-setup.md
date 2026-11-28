# 金融庁 EDINET APIキーの設定

1. [金融庁のEDINET API登録画面](https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1)を開きます。画面が開かない場合は、ブラウザーで `api.edinet-fsa.go.jp` のポップアップを許可します。
2. サインアップし、メールで届く確認コードを入力します。パスワードを設定し、画面の案内に従って多要素認証と連絡先の登録を完了します。
3. サインイン後の発行画面でAPIキーを発行し、表示された値を控えます。
4. [GitHubのActions用リポジトリシークレット設定](https://github.com/osawamas/value-hunter-ai/settings/secrets/actions)で **New repository secret** を選びます。名前を `EDINET_API_KEY` にし、値欄にキーを入力して **Add secret** を押します。リポジトリのシークレットを管理できる権限が必要です。
5. 次のPR #162の **Build30 public market coverage** の新規実行で、出力の `valuation_input_audit` を確認します。古い実行の再実行は、シークレット追加前の設定を使うことがあります。

キーの入力先はGitHubのシークレット設定欄です。チャット、PR、コミットには貼り付けないでください。実行環境はキーを環境変数から読み取り、金融庁のAPIに文書化された認証パラメーターで送信します。失敗時は認証情報を含まないエラーだけを記録します。照合に失敗した場合は集計結果に理由を記録し、未照合銘柄は評価に加えません。

[金融庁の手順書](https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf) · [GitHubのシークレット管理手順](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)
