# VALUE HUNTER AI — v250 checkpoint (2026-11-15 JST)

## Starting position
- GitHub repo: `osawamas/value-hunter-ai`. Initial main `e71df146e9e99641589246fe53d30ec6d398330c` was the v249 checkpoint. Fetch latest main and Actions before modifying, as the repo is updated by multiple workflows. Read `docs/development-checkpoint-v249.md`, `docs/data/latest.json`, and this checkpoint; do not repeat v190–v249.
- Verified financial feed at initial check: 7 issuers; rankings disabled and eligible 0. Separate 182 unverified third-party candidates; official complete SGX master not yet obtained.
- Public GitHub Pages NOT enabled: Pages workflow overall SUCCESS but `pages` job SKIPPED on latest runs. Don't mistake green workflow for published site.

## v250 key achievement: verify actual exported preview ZIP, not just its inputs
- New Python `scripts/verify-preview-archive-v250.py` validates **real generated ZIP** `build/preview/value-hunter-dashboard-preview-v249.zip`: archive CRC integrity, path traversal, duplicates and symlinks, file count and total extracted size limits, essential app/data files, 25+ HTML-linked assets, fail-closed feed rank state. Extracts to a temporary directory and runs a localhost HTTP server, reading HTML, JS, CSS, latest feed JSON and SGX replay JSON through actual HTTP. Generates `build/preview/dashboard-preview-smoke-v250.json` containing SHA256 of ZIP, counts and explicit false Pages/SGX quote license flags.
- Existing `.github/workflows/value-hunter-pages.yml` dashboard-preview job now executes this verifier **before** uploading the downloadable ZIP artifact; also uploads the smoke-report artifact separately with 30-day retention. Unverified ZIP must fail the job.
- Real GitHub Actions run [43615762823](https://github.com/osawamas/value-hunter-ai/actions/runs/43615762823) successful: log `v250 PASS: REAL ZIP verified (267 files), 36 linked assets, localhost HTTP and ranking hold`. `pages=skipped` because owner Pages setting is not enabled; preview completed successful.
- Later actual Pages run [43615840159](https://github.com/osawamas/value-hunter-ai/actions/runs/43615840159) all validate/pages-setup/preview completed SUCCESS; pages SKIPPED. Artifacts: downloadable `value-hunter-dashboard-preview-v249` ID **14122037436**, and `value-hunter-dashboard-preview-smoke-v250` ID **14122750274**.
- New test `docs/test_dashboard_preview_smoke_v250.js` ensures archive validation/local HTTP smoke code is present as a mandatory pre-upload job and ranking is disabled. Registered in `scripts/verify-evidence-v198.js` and CI path triggers.
- Final evidence suite real GitHub Actions [43615859648](https://github.com/osawamas/value-hunter-ai/actions/runs/43615859648), job 132510650363: **SUCCESS** with `PASS docs/test_dashboard_preview_smoke_v250.js`, `Evidence smoke suite: 50/50 passed; rankings remain independently gated.`
- Commits: `319f62737f2af824a8a5aebb6b27f270a5ee13d1` (Python real archive verifier), `1a417050884cbf2e5d55692ffe3c80c6cf65e75c` (preview verification and artifact), `388f0f0d2e6ff91a050307ce6ca6bdc60d624518` (test), `81ad2e0599bbf1e70f5ea33fd0f0282300b44838` (suite), `28b489a901d99880f1a071286667528b80711039` (CI trigger).

## Real blockers / priorities
1. Owner GitHub Pages setting must be enabled at `Settings → Pages → Build and deployment → Source: GitHub Actions`. After that, rerun `VALUE HUNTER dashboard publish v46` and prove **pages job success** + reachable public URL. ZIP/localhost proof is not deployed-site proof.
2. UOB Nov13 2026 `SG261113OTHRHOAF` and OCBC Nov12 2026 `SG261112OTHRXH64` original SGX primary documents, including `Anno_12Nov2026.pdf`, remain unobtained. Never invent file IDs or current shares from secondary mirrors.
3. Current SGX licensed market-data feed, trade timestamps, permissioned application redisplay / analysis rights unavailable. Full official dated SGX security master unavailable. Independent accounting numeric verification incomplete; keep ranking eligible 0.
4. SGX H02/V03 four issuer primary PDFs were actually replayed in v247 and displayed in v248; a source byte digest does not prove independent financial audit. Avoid repeating those proof-only stages without new data.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv250から継続。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v250.md`を読む。v249までZIPプレビュー自動生成済み。v250で実際のZIPを展開・CRC/パス安全性/不足ファイル/財務ランキング無効を検査し、localhost HTTPでHTML/JS/CSS/JSON読み込みに成功。Actions #43615762823で267ファイル、36アセット、HTTP全PASS。#43615840159でZIP artifact ID14122037436 と検証レポート artifact ID14122750274保存。統合CI #43615859648 は50/50 PASS。Pages本番公開ジョブはSKIPPED（所有者がPagesを有効化する必要あり）。財務7、ランキング0。UOB11/13・OCBC11/12 SGX公式原本、正規株価ライセンス、公式全銘柄マスター、独立会計数値検証は未完。次は本当に不足している原本・実データ・公開設定を優先し、既済工程を繰り返さない。
