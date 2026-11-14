# SGXデータの正規取り込み手順 — v231

> STATUS: 未完成のデータ取得ワークフロー。公式サイトの存在とデータを合法的に再利用できることは**別**。現在の本番ランキングは0社。記載の例は試験用であり、SGXの実際のCSVエクスポート形式を保証しない。

## 1. データ源を分離する

| 入力 | 公式の入口 | 中身 | 取り扱い |
| --- | --- | --- | --- |
| 上場発行体 | https://www.sgx.com/securities/corporate-information | 発行体名、上場市場、国、上場日 | 売買コードと同一視しない |
| 売買証券 | https://www.sgx.com/securities/securities-prices?code=stocks | 取引カウンターのコード、通貨、銘柄名など（画面には相場も含む） | 株価・板・出来高などを落としても、原データの利用条件は別途確認 |
| 既存の第三者候補 | `docs/data/sgx-universe-candidates.json` | 第三者が発見した182候補（変動し得る） | 取引所の完全な発行体一覧ではない |
| 既存の財務登録 | `docs/data/latest.json` | 現在7社の登録と検証状態 | 投資ランキング適格0社 |

SGXルールの Official List は、Mainboard、Global Listing Board、Catalistに受理された**発行体**の一覧を指す。証券・別通貨カウンター数やETFなどを足し合わせて企業数にはしない。

## 2. 取得と権限

1. SGX公式の該当ページを手動で閲覧し、発行体の情報と売買証券の情報を区別する。
2. 入手日・対象日・元URL・取得方法・利用可能な範囲を記録する。発行体一覧の公式な一括取得形式と再配布許諾は現在未確認。
3. ソース内容を**無許可で公開サイトへコピーしない**。StocksSGなどの無料APIが利用できても、契約上の再配布許可を意味しない。
4. 取引所の「Download」に株価や板情報が含まれる場合、ローカル処理以外に利用しない。価格の権利を推定しない。
5. PDFの発行体資料については、実ファイルのバイト列からSHA-256を計算した場合のみ原本ハッシュとして記録する。リンクや目視だけでは確定しない。

## 3. ローカルで手動取得データを仮取り込みする

コマンド例（リポジトリのルートから実行）。入力ファイルは権利を確認のうえ自身で用意する。既存の出力を黙って上書きしない。

**証券のCSV** は、少なくとも `Trading Code,Trading Name,Traded Currency` が必要。任意で `Security Type,Listing Board`。これは取り込み用の正規化スキーマで、**SGXの実際のダウンロード形式であると未確認**。

```bash
node scripts/stage-sgx-csv-v199.js \
  --input build/input/securities.csv \
  --out build/staging/securities.json \
  --as-of 2026-11-14 \
  --source-url 'https://www.sgx.com/securities/securities-prices?code=stocks'

node scripts/audit-staged-sgx-universe-v229.js \
  --staged build/staging/securities.json \
  --out build/research/securities-coverage.json
```

**発行体のCSV** は、手動で正規化した `Company Name,Country,Listing Board` が必要。任意で `Listed Date`（`YYYY-MM-DD`）。公式ページに記載される複数の上場・市場移行日付を勝手に最初の一日へ還元しないこと。必要なら空欄として原ページを別途レビューする。

```bash
node scripts/stage-sgx-issuer-directory-v230.js \
  --input build/input/issuers.csv \
  --out build/staging/issuers.json \
  --as-of 2026-11-14 \
  --source-url 'https://www.sgx.com/securities/corporate-information'
```

両取り込み器とも、**ローカル出力**を前提とする。出力先が `docs/` 内なら拒否。元CSVの生バイトSHA-256を保持し、不正なUTF-8・異常な行・重複などは拒否する。証券CSVから価格・出来高・気配・時価総額は保存しない。発行体CSVは証券コードやISINを推測しない。

## 4. どの状態なら正式登録できるか

- 発行体と個々のカウンターの紐付けを、SGX原本または十分な一次資料で独立に裏付けること。
- 台帳の対象日時、上場・廃止・通貨の区分と再配布権限を確認すること。
- 財務諸表の数値とその会計定義、基準日が一致する株式数、利用許可のある時刻付き価格を確認すること。
- 上記が欠ける発行体は「調査対象」にとどめ、PER/PBR/時価総額や正式ランキングへ**自動昇格させない**。

## 5. テスト・今後の作業

```bash
node scripts/verify-evidence-v198.js
```

この一括検証の実GitHub Actions成功は未確認。V8互換環境で個別テストは成功しているが、Node本体とCIの全走破は別途実ジョブで検証する必要がある。

実際のSGX発行体一覧・証券CSVの正規のフォーマット・完全性・利用許諾、UOB/OCBCの未取得原本、正式な株価契約とGitHub Pages公開設定が未完。取得できたときは先に新しい入力のスキーマと証拠をレビューし、これまで完成した処理は繰り返さない。
