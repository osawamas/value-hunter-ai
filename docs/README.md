# VALUE HUNTER AI — SGX日本語Webダッシュボード（v29）

この `docs/` はGitHub Pages向けの静的Webアプリ。無料で表示でき、APIキー・有料サーバー不要。

## 設計
- 対象は試験中の **S68 / G13 / S20 の3銘柄のみ**。SGX全銘柄対応は未完成。
- `docs/data/latest.json` を読み込んで、検索・絞り込み・並び替え・詳細表示・CSV書き出しを実行。
- 個々の銘柄に財務元PDF、株価ソース、株式数ソース、取得基準日、ランキング除外理由を表示。
- 未取得のデータは空欄。**独立検証が完了するまでは全銘柄をランキングから除外**。
- `latest.json` の初期状態は **実データなし**。サンプル株価を捏造しない。

## データ更新
`/.github/workflows/value-hunter-v29.yml` が平日の決算PDF・株価・株式数・クロス資料照合を統合し、**全段階が成功したときのみ**このJSONを差し替える。取得に失敗したら以前の公開JSONを維持。GitHub ActionsのArtifactsに診断ファイルが出る。

Actionsの実行結果だけでなく、`docs/data/latest.json` の `updated_at_utc` と各株価・株式数の基準日時を必ず区別すること。

## GitHub Pagesで公開する
GitHubリポジトリの **Settings → Pages → Build and deployment → Deploy from a branch → main → /docs → Save**。
これは最初の一度のみ。GitHub Pagesが未設定の場合、コードの反映だけでサイト公開は始まらない。

ローカルではリポジトリのルートから `python -m http.server 8000 --directory docs` を実行し、`http://localhost:8000/` を開く。

## 重要事項
- PDF同士の照合は同一企業の異なる発表資料の照合であり、第三者独立監査ではない。
- Yahoo Finance株価取得先は非公式であり、取得失敗・更新遅延がありうる。
- PBRの参考表示には未検証の親会社株主持分を含む場合がある。
- 静的な表示は**投資推奨ではない**。
