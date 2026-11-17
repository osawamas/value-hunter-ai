# v551 JPX日次・月次原本の追跡性を強化

- 起点: v550 / `47ff3de1a67da875a02777a870cbf284f0cc8abd`。
- 実装: [`20d45fb8`](https://github.com/osawamas/value-hunter-ai/commit/20d45fb8bb606d26eaf86db0db36fbee83aabd79) で `android-private/tools/jpx_rights_sources.py` の出力に、取得した日次XLSの公式URL・SHA256と、月次PDFの公式URL・SHA256を追加。取得したバイト列をハッシュし、原本照合に使えるようにした。従来の月次件数・保留判定は変更しない。
- 検証: この実行環境ではGitHubへの直接Git接続がDNS解決不可。GitHub連携で更新後のソース保存は確認。新コミットのGitHub Actions成功、JPX現物取得、APKビルド、Android実機通知は未確認。成功を推定しない。
- 未完了: 2026年1月・2025年9月のJPX月報行座標解析、2026年10・11月の未掲載月の個別TDnet照合、日次終値と財務・株数の実データ連続更新。資料不足だけで保留解除しない。
- 次回: 最新mainとActionsを先に確認し、JPX原本の取得結果に新しいURL・SHA256が含まれることをCIで検証。次に月報解析を修正し、Android本人用監視経路へ接続する。公開Artifacts/ReleaseでAPKを配布しない。
