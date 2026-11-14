# VALUE HUNTER AI — v249 checkpoint (2026-11-15 JST)

## Baseline and important finding
- Repo `osawamas/value-hunter-ai`; initial observed latest main `d54d394900b4cefdde1f59ddfbb005ccbf7a021d` (v248 checkpoint). Fetch live main, Actions, `docs/data/latest.json`, and this file before continuing; concurrent workflows mutate source data.
- After latest v248 update, observed feed `2026-11-14T16:17:42.130634+00:00`, 7 financial records, ranking eligible **0**. No right to promote licensed SGX prices.
- Real Pages run [43614877637](https://github.com/osawamas/value-hunter-ai/actions/runs/43614877637): overall SUCCESS but `validate=success`, `pages-setup=success`, **`pages=skipped`** because GitHub Pages is not enabled in owner settings. Do not call site published.

## v249 major feature: obtain functioning app without Pages
- Modified `.github/workflows/value-hunter-pages.yml` to add `dashboard-preview` job after successful dashboard `validate`, independent of Pages-enabled state. The job checks static essentials, ZIPs the complete `docs/` tree, and uploads `value-hunter-dashboard-preview-v249` as a GitHub Actions artifact (30 days), containing `value-hunter-dashboard-preview-v249.zip`. The ZIP is a local preview snapshot, **not** a public deployment.
- Actual first live workflow [43615071754](https://github.com/osawamas/value-hunter-ai/actions/runs/43615071754) succeeded: `dashboard-preview=success`, `pages=skipped`, artifact ID `14121593502` (485,514 compressed bytes).
- Added `docs/test_dashboard_preview_v249.js`, now part of unified evidence suite, to verify that preview job is separate from Pages publication and that HTML script/style references and essential `docs/data/*.json` files are present, while rank eligibility stays false.
- Added `docs/README-PREVIEW-v249.md` inside ZIP, giving Mac/Windows steps: GitHub Actions Artifacts download outer ZIP, extract inner ZIP to get `docs/`, start local HTTP server with `python3 -m http.server 8000` from the directory containing `docs`, then visit `http://localhost:8000/docs/`. Double-clicking index.html from file:// is NOT sufficient because JSON fetch requests are blocked.
- Updated Pages workflow push paths to include `docs/*.js`, `docs/*.css`, `docs/*.html`, `docs/data/*.json` and README, so changes automatically rebuild the downloadable snapshot.
- GitHub commits `429533a818440901a89100f688ad63c8cd2707da` (ZIP workflow), `995f9846cce9e640a30fdec065cfc46db8013f39` (test), `8d6353ad798ed4d37978f078acd1202b78b94f1f` (evidence suite), `1c08a6163d5bfaa2fd3c0c3e91e43a949b3578e9` (test trigger), `90bcb2c9dd82ea48c28502553a7fe288a8248c76` (README), `52662d5a3a971dc4aabb0535d19a1d13803cb6cc` (preview rebuild on updates).
- Latest actual workflow [43615331410](https://github.com/osawamas/value-hunter-ai/actions/runs/43615331410): **completed SUCCESS**, preview artifact ID **14121519398** compressed size 487,802 bytes; `validate=success`, `dashboard-preview=success`, **`pages=skipped`**. This latest ZIP includes the README.
- Latest real Node20 evidence integrity Actions [43615331454](https://github.com/osawamas/value-hunter-ai/actions/runs/43615331454) job 132509011451: **SUCCESS**, logs `PASS docs/test_dashboard_preview_v249.js`, `Evidence smoke suite: 49/49 passed; rankings remain independently gated.`
- Owner still needs **Settings → Pages → Build and deployment → Source: GitHub Actions**, and then Actions → `VALUE HUNTER dashboard publish v46` → `Run workflow`. Only actual `pages=success` and accessible URL count as published. Do not claim Pages configuration changed from this code.

## Current blockers and high-priority next work
1. Original primary SGXNet 2026-11-13 UOB buyback announcement `SG261113OTHRHOAF` and original 2026-11-12 OCBC `SG261112OTHRXH64` PDF `Anno_12Nov2026.pdf` still missing; do not promote syndicated secondary share counts.
2. Licensed actual timestamped SGX quote rights for display, processing, redistribution, and compliant valuation not obtained. Official full SGX security master not obtained (11-company partial SGX batch and 182 unverified third-party candidates do not satisfy complete scope).
3. Independent accounting/owner-equity verification not done. Ranking eligible 0.
4. GitHub Pages owner setting not enabled and page publish skipped, but v249 downloaded ZIP now available for local preview.
5. Next milestones should prioritize real market-data licensing/source acquisition or user-visible deploy setup over more source-only badges.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv249から続ける。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v249.md`を読む。v247原本PDF4件の再取得SHA照合、v248でアプリ内表示が完了。v249でPagesが未有効のため本番公開ジョブSKIPPEDであることを実際のrun #43614877637と#43615331410で確認。代わりにページ検証後のアプリ完全ZIPを自動生成しGitHub Actions artifactとして保存、#43615331410 のartifact ID14121519398で取得可能。READMEにMacでのローカル閲覧手順同梱。更新時自動ZIP再生成。CI #43615331454 は49/49 PASS。Pages公開には所有者がSettings → Pages → GitHub Actions を選択する必要あり。財務7銘柄・ランキング適格0、UOB11/13・OCBC11/12公式原本、SGX全銘柄公式一覧、正規SGX株価許諾、独立財務監査は未完。完了済み作業を繰り返さず実用化を進める。
