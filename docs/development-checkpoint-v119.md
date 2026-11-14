# VALUE HUNTER AI — v119 checkpoint (2026-11-14 JST)

## Restart / first reads
Before next development, read GitHub `main`, latest Actions, `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-g13-official-identity-v119.json`, `docs/development-checkpoint-v119.md`, plus previous `docs/development-checkpoint-v116.md` if needed. Do not repeat v97–v119.

## v117 completed: seven-issuer ranking eligibility blockers
- Added `SGX_PDF_connection_probe/sgx_ranking_readiness_v117.py`, negative tests, and `.github/workflows/value-hunter-v117.yml`.
- CI #43560417817 **SUCCESS**: live public feed 7 companies; explicit separate `docs/data/sgx-ranking-readiness-v117.json` listing validation blockers by issuer and by sector. Banks do not incorrectly require industrial revenue/operating margin.
- G13/S63 prioritized for verification *work* based on issuer document crosschecks and S63 newer buyback snapshot, NOT because either is an investable or objectively undervalued candidate. Issuer-to-issuer matching is not independent numerical validation.
- Blocks for industrials: independently verified financials and parent equity, authenticated timely SGD quote, up-to-date treasury-adjusted share count, reference-date compatibility. S20 loss means positive-earnings PER inapplicable. Banks have distinct independent financial, market quote and current shares gaps. Ranking remains zero.
- Crucial: v117 records use explicit false for independently verified fields until a separately authenticated pipeline exists; do not silently flip based on issuer-only or Yahoo evidence. This is readiness diagnostic, never a bypass gate.

## v118 completed: ranking blockers UI and refresh linkage
- Added `docs/ranking-readiness-v118.js`, `docs/test_ranking_readiness_v118.js`; modified `docs/index.html` to show Japanese seven-issuer verification blockers and `.github/workflows/value-hunter-pages.yml` for UI tests.
- CI #43560563204 **SUCCESS**: Node tests and public JSON integration. UI refuses stale diagnostics when feed `updated_at_utc` differs from v117 diagnostic's published feed timestamp, and rejects ranking promotion/inconsistent issuer data.
- Updated `.github/workflows/value-hunter-v117.yml` (commit `684028e99860f17e6ee2f4948b10b38f54a8de91`) to trigger v117 diagnosis after a successful v29 financial feed refresh on main. Subsequent v117 CI #43560598257 and #43560666186 **SUCCESS**, with regenerated sidecar.
- v29 #43560544753 SUCCESS; Pages #43560666181 SUCCESS. Last checked current feed timestamp `2026-11-14T05:14:55.805445+00:00` equals readiness sidecar timestamp, ranking eligible 0, registered issuers 7. This confirms latest audit sidecar matches the then-published financial feed. Pages CI success does NOT prove a live accessible published website or a user-browser screenshot.
- Note workflows commit to main concurrently; read fresh head and check for new refresh runs before editing/updating.

## v119 completed: G13 primary exchange identity
- Found authentic SGX issuer/securities historical announcement `https://links.sgx.com/1.0.0/corporate-announcements/NF6GZEGGD4XBFOVY/`, GENTING SINGAPORE LIMITED, ticker `G13`, ISIN `SGXE21576413`, ref `SG260130OTHRZ1XN`, broadcast `30-Jan-2026 17:20:38`.
- Added `SGX_PDF_connection_probe/sgx_g13_primary_identity_v119.py`, adversarial tests and `.github/workflows/value-hunter-v119.yml`.
- CI https://github.com/osawamas/value-hunter-ai/actions/runs/43560729765 **SUCCESS**; direct SGX original HTTP fetched, issuer/ticker/ISIN/ref/date matched. Published `docs/data/sgx-g13-official-identity-v119.json` with source SHA256 `10988ce9e47e8414110c210f49db4e97c6b13d2c8b01c42a55751fc79c6630a1`.
- This proves only historical G13 identity. Does NOT verify current active listing, current share count, quote price, independent accounting checks, or ranking eligibility. All such flags false.

## Still outstanding (highest-value v120+)
1. Move at least one industrial company G13 or S63 to fully independently corroborated source *without weakening ranking rules*. For G13 current public quote and 2026-06-30 share count are not sufficiently verified for valuations; look for recent exchange original shares and exchange quote evidence.
2. UOB 2026-11-13 `SG261113OTHRHOAF` and OCBC 2026-11-12 `SG261112OTHRXH64` official SGX original and OCBC PDF `Anno_12Nov2026.pdf` still not verified.
3. Complete SGX-listed issuer/security master still unavailable. 182 third-party StocksSG candidates NOT an official full SGX universe. Need actual export and provenance.
4. Actual independently authenticated exchange-timestamped quotes (Yahoo daily and intraday are secondary research only); align with source-verified shares and independent finance before market cap/PER/PBR.
5. Future v117 workflow may race v29 or another update: compare `updated_at_utc` when displaying sidecar, and ensure diagnostics are re-run if stale. Keep first rank eligible zero until all independent checks complete.

## Short next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv119から継続。main、最新Actions、`docs/data/latest.json`、`docs/data/sgx-ranking-readiness-v117.json`、`docs/data/sgx-g13-official-identity-v119.json`、`docs/development-checkpoint-v119.md`を読む。v117は登録7社のランキング除外理由を銀行/一般事業会社別に診断、CI #43560417817成功。v118は日本語画面に7社の検証不足一覧を追加、CI #43560563204成功。v29完了後にv117診断を再生成するGitHub Actions連携も追加しCI #43560666186成功、最新確認時に財務JSONと診断の日時が一致。v119はG13のSGX公式発表から銘柄G13・ISIN SGXE21576413・発表番号SG260130OTHRZ1XNを実HTTP照合しCI #43560729765成功。ただし過去の識別確認だけ。第三者企業候補182社、財務登録7社、ランキング適格0社。次はG13またはS63の財務独立検証・最新自己株式控除後株数・SGX実株価を優先。UOB11/13・OCBC11/12原本、公式全銘柄マスターも未完。検証を緩めず時価総額・PER/PBR/ランキングに未検証値を昇格しない。GitHubに実装、テスト、原本ハッシュとチェックポイントを保存。
