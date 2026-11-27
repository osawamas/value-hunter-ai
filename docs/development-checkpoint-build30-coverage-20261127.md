# Build30 判定可能率の検証引継ぎ

2026年11月27日（日本時間）。作業ブランチは `integration/valuehunter-flexible-coverage`。起点は #159 の `cfe8b6578972823843158f4336db0b3b2ec94d67`。#158、#160、#161 の公開HEADをローカルで統合し、Androidの修正と無関係なSGX履歴および同時期の資産更新は起点に揃えた。判定集計と通知の実装コミットは `bbd8bdde` と `5ffd69b9`。main と公開PRは未更新。

## 同一取引日の計測

米国はNYSEとNasdaqの取引日付き普通株監視集合。日本は東証プライム、スタンダード、グロースの内国普通株。終値なし、照合待ち、予算外も母集団に残す。予算内率の分母は終値と必要な為替で予算内と確認できた銘柄。財務取得数、厳格判定、追加の柔軟判定、理由別保留、標準閾値での予算内三段階該当を記録する。確定済みの非正値財務は専用の除外理由とし、既存の候補・比較判定は従来の扱いを維持する。端末診断の三段階集計は通知投稿の成功件数とは別に扱う。

アプリは取得・照合後に診断と `no_backup/us-assessment.json` または `no_backup/jpx-assessment.json` を更新する。日本株の端末集計には上場一覧の基準日が含まれる。新規上場・上場廃止の転記状況を確認して分母を固定する。両市場とも実測未計測。2026-11-26の東証日報、2026-11-25の米国終値と為替、Nasdaq Trader銘柄一覧、SEC銘柄一覧・companyfactsへの試行は、この環境の接続プロキシから403を受けた。クラウドの接続はパッケージ取得先などに制限されていた。対象ホストの追加確認は完了せず、設定は適用されていない。取得できた市場全体の一次入力はない。90%達成と旧方式からの実データ増分は未検証。

## オフライン再生

米国は監視処理済みのデバッグ端末から同じ取引日のスナップショットを取得する。処理途中、上場一覧の日付が異なる、終値データのハッシュが異なる、分割照合の版が古い場合は再生を拒否する。JDK 17 と JSON Java 20240303 を使用する。

```bash
app=jp.valuehunter.privatewatch.diagnostic19
adb exec-out run-as "$app" cat no_backup/us-daily-closes.json > us-daily-closes.json
adb exec-out run-as "$app" cat no_backup/us-sec-financials.json > us-sec-financials.json
# JSON Java 20240303 の jar を任意の絶対パスで指定
workdir=$(mktemp -d)
cp "$JSON_JAVA_JAR" "$workdir/json.jar"
bash android-private/tools/compile_us_replay.sh "$workdir"
java -cp "$workdir/classes:$workdir/json.jar" jp.valuehunter.privatewatch.UsRetryReplay \
  --coverage us-daily-closes.json us-sec-financials.json > us-assessment.json
```

日本は当日の公式JPX PDFと同日基準の内国普通株一覧が必要。JPX公表の一覧から抽出し、新規上場・上場廃止を適用した集合を使う。抽出の起点は `android-private/tools/jpx_daily_probe.py` の `ordinary_stocks`。一覧ファイルの先頭行はISO取引日、後続は一行一銘柄コード。デバッグアプリとテストAPKを入れた同じ端末に渡す。端末の自動財務・権利キャッシュに依存し、キャッシュが空でも母集団を縮めず結果を返す。入力を使用した際にPDFと一覧のSHA-256を出す。

```bash
app=jp.valuehunter.privatewatch.diagnostic19
day=2026-11-26
pdf="jpx-${day//-/}.pdf"
adb shell -T "run-as $app sh -c 'cat > $pdf'" < "$pdf"
adb shell -T "run-as $app sh -c 'cat > jpx-coverage-universe.txt'" < jpx-coverage-universe.txt
adb shell am instrument -w -e coverage_day "$day" \
  "$app.test/jp.valuehunter.privatewatch.JpxPdfGeometryProbe"
```

## 検証と残課題

ローカル JDK 17、Gradle 8.10.2、SDK 35。Android単体225件、デバッグAPKおよび計装テストAPKの組立、米国再生4件と関連Pythonテスト173件（米国145件、日本株28件）は成功。#159のGitHub通知ジョブは API 28/34/35 とも中止を確認した。統合ブランチのGitHub Actionsは未実行。API 35のローカルエミュレーターでは起動時の銅色エンブレム、ホームのヘッダーと下部4タブ、通信・無音通知の設定表示を目視確認した。無音通知計装テストは2回とも `Process crashed` で終了。初回は端末ログでアプリの起動ANRを確認し、無音・点灯・再起動後の履歴は未検証。

ローカルAPKは `jp.valuehunter.privatewatch.diagnostic19`、versionCode 30、`0.6.24-test-separate19`。SHA-256 は `85f1348091719f20aa28e1d1cd67cb260d936def0dc432709eeb63259bbba309`。ローカルデバッグ証明書のSHA-256は `b6d6892998eca85a1b33d3ebd2d0fa00605c8167071180c9e384776913dbedf5`。配布済みBuild30の署名と既存保存データの引継ぎは未照合。配布用APKは保留。

次の検証は日米の同日スナップショット取得と旧方式との同一入力比較、通知成功件数との照合、実機での無音・消灯からの点灯・再起動後の履歴。EPS不在時の独立した代替評価、財務以外の追加情報、JPX予算外の財務取得、再現可能な探索キュー、長期バックテストが残る。

## JPX財務取得0件の切り分け

2026年11月28日（日本時間）。PR #162で旧パーサーのまま取得を再計測したところ、累積592銘柄が保留となった。EPS・BPS照合保留554件、訂正版のiXBRLなし26件、通期開示を特定できず11件、通期iXBRLなし1件。実行時に新たに確認したのは16銘柄で、通信再試行は1銘柄。最初の192件単独の内訳は当時の実行に銘柄別成果物がなく、累積内訳と区別する。1301・6758・7203は取引所の企業開示検索がHTTP 200を返し、企業コードとiXBRLリンクを確認した。[旧版の銘柄別監査](https://github.com/osawamas/value-hunter-ai/actions/runs/46030414836)

Android API 35で同じ通期iXBRLを使い、旧版では解析できず、修正版でEPS 60・BPS 1,000を取得した。Androidで必須指定していたパーサー固有の機能設定を外し、DTD・ENTITYの事前拒否と外部参照の拒否を維持した。BPSが欠ける場合は、同じ企業の前年度資料から同じ連結区分・会計基準のEPSを確認する。株式の権利調整と公表日を既存処理で照合する。取得先、HTTP・解析結果、保存ファイルの記録、取引日の照合結果を成果物で銘柄単位に追跡できる。[修正版の再計測](https://github.com/osawamas/value-hunter-ai/actions/runs/46031309015)

3,689銘柄の分母は、月末マスターのプライム・スタンダード・グロース内国普通株3,686銘柄に、取引日までの公式上場・廃止を反映した集合。差分は正味3銘柄。4,958は引継ぎ書にある旧設定値で、当時のJPX銘柄一覧がないため、1,269銘柄の銘柄別差分は確定できない。同じ4,958という数値は別の米国株開発ログでは、2026-11-17の米国取引日に取得できた終値件数として使われている。JPX以外の区分やETFなども確認できるよう、公式マスターの区分内訳を出力する。

修正版の最初の実測では、旧版の成果物と192銘柄が一致した。192社の会社開示を解析し、178件のiXBRLを受信。192銘柄の保存を照合し、旧版でEPS・BPS照合保留だった178銘柄が取引日に使える財務を取得できた。11月26日の判定可能数は143/3,689（3.88%、厳格143、柔軟追加0）。基準の11件から132件増加し、割安36件、かなり割安0件、超割安0件。米国株は11月27日の5,080銘柄を確定したが、終値の取得・検証が完了せず判定率は未計測。[実測と銘柄別成果物](https://github.com/osawamas/value-hunter-ai/actions/runs/46031309015)

取得済み財務を再利用した2バッチの実測では384銘柄を新たに処理し、取引日に利用できる財務は累積533銘柄となった。判定可能は389/3,689（10.54%、厳格389、柔軟追加0）、割安97・かなり割安0・超割安0。公式マスターの全商品区分は4,444行。監視対象はプライム1,546・スタンダード1,550・グロース590の内国普通株コード3,686を基準に、取引日の上場・廃止を反映した。Hachiquantの再計測は初回にXLS読込依存関係が欠けていたため、その依存関係を追加した。[2バッチの実測](https://github.com/osawamas/value-hunter-ai/actions/runs/46032217205)

## 11月28日（日本時間）の再開結果

PR #162の統合ブランチ `integration/valuehunter-flexible-coverage` で作業。日米の判定処理を変更したコミットは `117902bf` と `a5c30a63`。通知計装の最新修正は `3e5067e8`。UIとブランド資産のファイルには変更を加えていない。

| 対象取引日 | 監視対象 | 厳格 | 柔軟追加 | 合計・判定率 | 割安／かなり割安／超割安 |
|---|---:|---:|---:|---:|---:|
| JPX 2026-11-26 | 3,689 | 555 | 0 | 555（15.04%） | 145／0／0 |
| 米国 2026-11-27 | 5,080 | 未計測 | 未計測 | 未計測 | 未計測 |

JPXは終値3,655、有効財務794。従来の累積547件から8件増えた。新たな取得で企業開示16件、iXBRL受信14件を確認し、企業開示のHTTP 503で取得を停止してバックオフを保存した。前回、有効財務780件から厳格判定に入らなかった243件は、EPSまたはBPSがゼロ以下173件、株数基準確認中70件。今回の保留は177件と72件。取得枠を最大4バッチに拡張した計装は、保存済み進捗を再利用する。日本株の90%は未達。[銘柄別監査と判定実測](https://github.com/osawamas/value-hunter-ai/actions/runs/46061801303)

Hachiquantで、月末マスター3,686件中3,623件の終値・円建て通期EPS/BPSが揃った。3市場から抽出した6社すべてで公表日を照合し、取引日前だった。JPX権利月報では2025年1月から2026年10月までを検証し、2026年11月分が欠けていたため、6社すべての株数基準を保留した。値の原本突合と本番採用も保留。JPX・Hachiquant・DoltHubへのCodexクラウドからの接続はプロキシのCONNECT段階で403。公開の標準GitHubランナーで取得を試行した。[Hachiquant利用条件](https://hachiquant.com/legal) · [市場取得監査](https://github.com/osawamas/value-hunter-ai/actions/runs/46061801303)

当期BPS欠損時、比較可能な2期のEPSと権利基準を確認した前期BPSを使い、保守的なPER/PBR条件を満たす場合に「かなり割安」まで判定する回帰テストを追加した。独立した価格履歴・同業比較、追加の非伝統的情報と探索キュー、十分な代替根拠によるJPX柔軟第3段階は残課題。

米国DoltHubの終値取得は、タイムアウトを同じ種類として扱い、小さいページへ切り替えて同じコミットの続きを取得する。11月27日取引分はHTTP 200で終値0件の回とタイムアウトした回を確認し、全市場の判定率は未計測。Android単体234件、米国の保存データ再現4件、デバッグ・計装APKの組立に成功。ブランド画面CIはAPI 28・35で成功。[市場再検証](https://github.com/osawamas/value-hunter-ai/actions/runs/46063404288) · [ブランド画面CI](https://github.com/osawamas/value-hunter-ai/actions/runs/46062488585)

通知CIではAPI 28・34・35で無音、画面点灯、履歴と再起動後の重複防止、Wi-Fi復帰を確認。後続の終値補完テストが、SEC財務と開示の同形URLをどちらも財務取得として数えて失敗したため、計数をcompanyfactsに限定した。実機の動作は未検証。[通知の検証](https://github.com/osawamas/value-hunter-ai/actions/runs/46062488708) · [修正後の通知CI](https://github.com/osawamas/value-hunter-ai/actions/runs/46064200091)
