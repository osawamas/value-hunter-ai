# VALUE HUNTER AI — v243 checkpoint, 2026-11-15 JST

## Resume from latest main, NOT v189
- Before v243, main was `7b6b521b33588ab55e7b8b8dfa93981dc4129dbb` (v242 checkpoint). Always fetch fresh main and latest GitHub Actions again: work may occur in parallel.
- Read `docs/development-checkpoint-v242.md`, `docs/data/latest.json`, `docs/data/sgx-uob-official-buyback-v242.json`, `docs/data/sgx-bank-corporate-actions-v190.json`, `docs/data/sgx-source-rights-review-v222.json`.

## v243 implemented
- New `scripts/build-bank-evidence-readiness-v243.js`: derives a fail-closed bank provenance/readiness JSON, locally at `build/research/sgx-bank-evidence-readiness-v243.json`. Compares the exact UOB Nov12 official-source share count, announcement ID, source URL, date, cancellation and issuer across independent repository data schemas v190 and v242.
- UOB historical SGX original as of **2026-11-12** is 1,646,711,591 shares excluding treasury. This is NOT a current as-of-Nov15 number; Nov13 SGX original remains unavailable. The derived report never promotes secondary Nov13 figures.
- OCBC 2026-11-12 `SG261112OTHRXH64` secondary announcement exists, with an attachment named `Anno_12Nov2026.pdf`, but the official SGX original attachment remains unacquired. Its quantity is null, not extrapolated. Source reference and pending status are recorded.
- SGX actual quote feed license & redistribution permission unavailable, official complete SGX master unavailable, independent financial audit incomplete, ranking enabled FALSE / eligible 0.
- New `docs/test_bank_evidence_readiness_v243.js` tests 12 source tampering and unsafe promotions, plus runs CLI and checks emitted JSON matches pure derived status. Added to unified Node20 evidence test runner and workflow path triggers. Does NOT change `docs/data/latest.json` or public ranking.
- Commits: source feature `38f22285`, test `97b96148`, suite `723373b2`, workflow `4ce34956`. Initial dedicated CI failures 42/43 were real field-name mismatch between v190 `issued_excluding_treasury_after` and v242 `issued_excluding_treasury_after_purchase`: fixed cross-source comparison `74c578c1`, output field `217b5611`; no tests ignored. Real push CI [43612049277](https://github.com/osawamas/value-hunter-ai/actions/runs/43612049277) **43/43 PASS**.
- Added actual CLI output verification `8f8b7d3088a154eee5502c1a47bf0c724ba9c0e0`. Latest real push CI [43612109408](https://github.com/osawamas/value-hunter-ai/actions/runs/43612109408), job 132499179703 **completed SUCCESS**. Logs: `PASS docs/test_bank_evidence_readiness_v243.js`; `Evidence smoke suite: 43/43 passed`.
- SGX company announcements search `https://www.sgx.com/stock-exchange/company-announcements` locates public disclosures but SGXNet API may be gated for automated access. Third-party SGinvestors.io and ShareInvestor show 2026-11-13 UOB share buyback and 2026-11-12 OCBC treasury-use; these confirm only announcement metadata, not official full text or amounts. Do not infer authorization to scrape or reuse these third-party quotes.

## Next priorities
1. Obtain original UOB 2026-11-13 SGXNet share buyback and original OCBC 2026-11-12 treasury-share attachment. Verify actual issuer, date, shares/cancellation or reissuance changes before updating official outstanding.
2. Obtain authorized timestamped SGX market quote access and explicit appropriate display, computational and redistribution rights. Do not use third-party quote as licensed.
3. Obtain official, dated COMPLETE SGX company/security master; 11-name boardlot official subset and 182-name third-party candidates do not satisfy completeness.
4. Conduct independent numeric financial/source verification; owner-equity vs total-equity for H02, V03 etc. Never count same-issuer two docs as independent outside verification.
5. GitHub Pages owner setting still needs live deployment check; success of evidence tests ≠ Pages publication.

## Thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv243から続ける。最新mainとActionsと`docs/development-checkpoint-v243.md`を読む。v241は公式11銘柄10株単位の部分情報、v242はUOB 11/10-12公式買戻し原本の履歴、v243はv190とv242の発行済株数のソース一致・OCBC原本未取得・市場価格許諾未取得をまとめて機械判定する研究JSON生成CLIを実装、負テスト含めCI 43/43成功（#43612109408）。UOB 11/13、OCBC 11/12原本はまだ未取得。7社財務登録、ランキング適格0、公式全銘柄・合法な時刻付き株価・独立監査も未達。推測で最新PER/PBRを有効化しない。最新の取引日・根拠・許諾を満たすデータを優先してGitHubで開発続行。
