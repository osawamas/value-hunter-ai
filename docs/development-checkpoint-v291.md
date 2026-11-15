# VALUE HUNTER AI — v291 checkpoint (2026-11-15 JST)

## Start next session
- Read actual latest main, GitHub Actions, docs/data/latest.json, docs/development-checkpoint-v291.md.
- Existing hourly automation is enabled; do not create duplicates. Other jobs may commit to main.
- v290: SGX market display/non-display license research and gate, 80/80 CI. Formal investment ranking eligible remains zero of seven, no SGX data license obtained.

## v291 actual work
- Existing v199 CLI already stages locally obtained user CSV, strips quote columns, records original SHA, does NOT authenticate as an official full security universe; v278 browser manual master importer already exists. Avoid rebuilding these.
- Added `scripts/diff-sgx-snapshots-v291.js`: safely compares two locally staged identity snapshots with strictly increasing as-of dates, validates source snapshot schema, provenance/sha flags, rejects duplicated code|currency|type, computes possible additions, possible removals, name/board changes and same-code currency/instrument type change review candidates.
- CSV CLI accepts --older, --older-date, --older-url, --newer, --newer-date, --newer-url, --out; reuses actual v199 UTF-8 original bytes + sha and normalization; writes `wx` into local output, refuses publishing unauthenticated staged data under docs/. No scraped quotes, no direct SGX fetch, no financial feed mutation.
- All inferred listing events explicitly FALSE; difference is between incomplete input snapshots, NOT confirmed SGX new listing/delisting. No ranking eligibility promotion, no issuer count inference, no full universe certification or market rights approval.
- Added regression `docs/test_sgx_snapshot_diff_v291.js`: mutation, chronology, symbol variant and local CLI end-to-end tests. Registered it in `scripts/verify-evidence-v198.js` and relevant CI workflow path filters.
- GitHub Actions source evidence suite run #43670069422 **SUCCESS 81/81**, and #43670067015 SUCCESS; actual user-ready ZIP #43670053016 SUCCESS; actual file:// double click Chrome #43670053014 SUCCESS; dashboard publish workflow #43670052993 SUCCESS (do not assert Pages site public without actual Pages deployment).
- Core commits: 7b2431c6... module; 17c2c84e... test; 15195d1f... suite; 39605620... workflow.

## Actual blocking work still open
1. Obtain official dated complete SGX securities reference master with terms permitting internal processing. SGX site https://www.sgx.com/securities/securities-prices?code=stocks has browser interactive listing/download but is not verified complete and re-use permission not proven.
2. SGX official Market Data Policy effective July 1 2026: https://www.datadirect.sgx.com/Market-Data-Policy . Vendor directory https://www.sgx.com/data-connectivity/our-data-vendors distinguishes licensed direct/indirect vendors; indirect customers may not further redistribute data without SGX approval. Request both browser display and back-end non-display license, plus redistribution rights if needed.
3. Independently verify accounting evidence and current ex-treasury shares. UOB 2026-11-13 SG261113OTHRHOAF and OCBC 2026-11-12 SG261112OTHRXH64 SGX original URLs remain missing.
4. Ranking eligible 0 of 7, no full SGX master, no approved automated investable screening. No fake completion percentages.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v291から継続。最新main、Actions、docs/data/latest.json、docs/development-checkpoint-v291.mdを読む。v291は既存v199 CSV取込を活用して2日付のSGX銘柄一覧の追加・消失・名前・通貨変更をローカルで抽出、原本SHA・日付・根拠を保存し未検証の上場廃止/新規上場は断定しない。CI #43670069422 は81/81 PASS、Chrome/ZIP成功。正式ランキング0/7。次は公式全銘柄マスターの正規取得、許諾付き表示＋分析株価、独立財務照合、UOB/OCBC原本を重視。毎時自動開発既存で有効。
