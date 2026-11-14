# VALUE HUNTER AI — v252 checkpoint (2026-11-15 JST)

## Start from live repo, do not redo completed work
- Repo: `osawamas/value-hunter-ai`. Start of this work HEAD `47f51a55f3c4df250ea8b77a29b1ce34e1279425` (v251 checkpoint). Always read new main, latest Actions, `docs/data/latest.json`, and this checkpoint because multiple threads/workflows may commit.
- `docs/development-checkpoint-v251.md`: SGX original August 2026 month-end statistics: 604 listed securities (Mainboard 406, Catalist 198), not a complete dated issuer master, and not identical in unit or time to the current 182 third-party company candidates. 51/51 CI passed.
- Registered financial records 7, ranking eligible 0. Neither licensed current stock quote rights nor independent accounting audit or actual public Pages deployment has been obtained.

## Official issuer directory discovery
- Found SGX native site `https://www.sgx.com/securities/corporate-information` and indexed paginated examples `?page=24` (examples include Oceanus, Octopus, Oiltek, OIO, OKP, Olam) and `?page=3` (e.g., AnnAik). Page results list issuer names and MAINBOARD/CATALIST listing board, but a browser/search-index view is NOT a verified full dated security-code master, nor a verified automated export. Some SGX pages render an unsupported-browser shell in basic fetch. **No new official full list has yet been captured.**
- SGX security-prices viewer `https://www.sgx.com/securities/securities-prices?code=stocks` shows a download affordance, but this is a market-price viewer with separate redistribution terms; it has not been used to collect or republish current quotes. No source licensing was inferred.
- Keep `docs/data/sgx-official-monthend-aug2026-v251.json` as August historical aggregate only. Unverified 182 candidates remain isolated.

## v252 implementation
- Created `scripts/stage-sgx-official-directory-v252.js` (commit `66a7594b2839e0215400f59819425a3bee25bf65`). It accepts a **manually sourced, dated** normalized UTF-8 SGX issuer/security CSV; implements quoted/multiline-safe CSV parsing, explicit exact headers (`Trading Code,Trading Name,Listing Board,Traded Currency`), source hostname check, valid as-of day, unique uppercase security codes, finite supported listing boards/currencies, row/size limits. Calculates SHA256 of submitted CSV, compares securities to existing third-party 182 and financial 7, and writes ONLY `build/research/sgx-official-directory-staging-v252.json`. Explicitly FALSE for full official master, document authenticity, source license, numerical audit, quote availability and ranking. No automatic scraping or silent upgrade of `docs/data/latest.json`.
- The required CSV is an **application normalized schema**, not a claim about the native SGX CSV download format. Real dated official export still needs discovery and human review before CLI use. Example syntax:
`node scripts/stage-sgx-official-directory-v252.js /path/to/verified-export.csv 'https://www.sgx.com/securities/corporate-information' 2026-11-15`
- Added `docs/test_sgx_directory_staging_v252.js` with malformed CSV, duplicate symbols, invalid source domains/boards/currency/dates, illegal promotion, and a REAL command-line invocation that verifies generated JSON SHA and zero ranking. CSV used by tests is synthetic illustration, not official SGX data. Initial test commit `b8b066bbdc3266205465fe2571db35f78b05b767`; CLI coverage commit `cb375a20d9c2564019609655806f8dfc4bc4c7b1`.
- Registered test in `scripts/verify-evidence-v198.js` commit `b31a1d676e3f2da596848f309db1543657adc4fb`; CI workflow paths `.github/workflows/bank-corporate-actions-v191.yml` commit `ca2fd6281e5cc1b382627bc8635136a41db4eb15`.
- Usage/security documentation `docs/SGX-DIRECTORY-IMPORT-v252.md` commit `97fc9f72f12dc15bf91110a483a1636deb789c9e`. Points to official SGX directory, requires only reviewed source input, warns no native export guarantee or finance promotion.
- Real Node20 GitHub Actions final [43617020249](https://github.com/osawamas/value-hunter-ai/actions/runs/43617020249), job 132514194306: **completed SUCCESS**, `PASS docs/test_sgx_directory_staging_v252.js`, `Evidence smoke suite: 52/52 passed; rankings remain independently gated.` Initial pass [43616899108](https://github.com/osawamas/value-hunter-ai/actions/runs/43616899108) also 52/52.
- Latest Pages workflow [43617020264](https://github.com/osawamas/value-hunter-ai/actions/runs/43617020264): validate/preview SUCCESS, `pages` SKIPPED. An application ZIP is usable locally but website publishing still needs owner settings. No inference of site live.

## Next real work, avoid duplicate safety theater
1. Find actual official source for a **dated complete SGX code-level** issuer/security directory with appropriate use terms; not a market-size statistic nor index snippet. Capture source files in permitted way, validate trading codes and export schema, and only then use v252 importer. Measure actual cross coverage; keep rating gated.
2. Obtain licensed quote feed with timestamps and application redistribution/computation rights; avoid treating SGX delayed viewer as permission.
3. UOB 2026-11-13 `SG261113OTHRHOAF` and OCBC 2026-11-12 `SG261112OTHRXH64` `Anno_12Nov2026.pdf` original source still missing. Do not use mirrored share counts as primary.
4. Independently reconcile financial numeric figures / equity owners and source audit before any ranking eligibility.
5. Owner must enable Pages at GitHub Settings > Pages > Build and deployment > GitHub Actions, then verify actual `pages` job success.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv252から継続。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v252.md`から着手。v251はSGX公式8月末上場証券604（406/198）を確認。ただし第三者182企業候補と母集団が違う。v252はSGX公式 Corporate Information のページ一覧入口を発見、CSVによる銘柄コード/会社名/上場市場/取引通貨の取り込み・厳密バリデーション・候補差分検出CLIを実装。実際の公式全件CSVはまだ未入手。CLIテストに加えて生成JSONも検証済み。Actions #43617020249 は52/52 PASS。財務7・ランキング0。最新PagesもpagesジョブSKIPPED。今後は実際の公式コードマスター取得、許諾付きSGX株価、UOB/OCBCの未取得原本、独立会計数値照合を優先。推測値や二次情報を正式ランキングへ昇格させない。
