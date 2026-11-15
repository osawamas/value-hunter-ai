# VALUE HUNTER AI — v264 checkpoint (2026-11-15 JST)

## Start from current GitHub, not stale version numbers
- Repository `osawamas/value-hunter-ai`. Start of this user request latest checkpoint `docs/development-checkpoint-v262.md` at commit `334140185ebf5e2f15f76a05de277feba11ed3f9`, but background refresh workflows concurrently push `docs/data/latest.json` and commit v117/132/137/140/161. **Always re-read latest main, recent Actions and feed and checkpoint before new commits.**
- Feed at start: `docs/data/latest.json` `2026-11-15T00:02:07.133237+00:00`, **seven** registered financial securities `S68,G13,S20,S63,D05,O39,U11`, eligible ranking **0**. Some background feed jobs completed and updated main during this run.
- v262 included 30 historically researched SGX original-source counters, 19 direct SGXNet original HTML SHA256 validations, 11 official reduced-boardlot-table subset; 60/60 CI. Site requires owner Pages activation; working downloadable ZIP available in Actions.

## v263: make the code browser FINANCIALLY useful, not a separate identity-only catalog
- Extended `docs/sgx-historical-code-search-v258.js` `buildWithOriginalProof()` to **join 30 SGX researched trading codes by exact symbol** with seven registered financial records, no fuzzy company-name match.
- Four exact overlap securities: **D05, O39, S68, U11**. The 26 other listed-in-research counters have no matched registered financial data, and financial feed also has G13/S20/S63 beyond this limited 30-counter set.
- Every displayed code row now has a **財務登録** column, either `財務登録済・ランキング除外` or `財務未登録`. A tooltip holds actual exclusion reason codes from the financial feed for each of the four. Input class fail-closed requires all financial records with nonempty exclusion reasons and ranking flag false.
- HTML `docs/index.html` updated with sixth financial column; empty/error spans corrected to 6.
- Created `docs/test_sgx_financial_join_v263.js` with exact symbol overlap checks and rejection of duplicate finance symbols, fabricated investment eligibility, missing exclusions and ranking promotion.
- Commits `9b08e96a2650e06d9b569a147a8cbf1179b47638` JS, `12f6c6386c8541ad7795858a9f84e4b5cae02355` HTML, `dc069e32f5b27c0e867e8fd646dc3fabef631112` test, `30dc96324071efd5188c0d278fa4a5c7229f08b1` suite, `9f0087603d6824c9851c1a07f49101e9cd9bf92d` workflow. Initial CI failed **60/61** only because v262 assertion expected previous Japanese source-verification sentence, not a functional data failure. Fixed while preserving text `SGXNet原本HTMLの直接再取得で19銘柄`; commit `74c8efe125cb117e1aa2e81899c9e5feb86ba348`.

## v264: one-click coverage filters in that same browser
- Added finance filter dropdown in `docs/index.html`: all, **財務登録済み**, **財務未登録**. Combined with existing SGX name/code/ISIN substring search and listing-board filter.
- Updated `docs/sgx-historical-code-search-v258.js` `search(rows,query,boardFilter,financialFilter="ALL")` backward-compatible default. UI responds to select change. Filter shows 4 registered vs 26 unregistered, and 3 of the registered subset are in UNKNOWN board category because board-lot static source does not contain board assertion.
- New `docs/test_sgx_financial_filter_v264.js` tests combinations and no ranking eligibility, loaded in evidence suite and workflow paths.
- Commits: `0737eddb9c8e8223f9c839e90e6f2de09b7305cd` JS, `a308015eb6d8c457ff542375fd7f514398f6a6bf` HTML, `ab294ac490cc78504fc3ddde7899d85440eb597e` test, `fece81e5777939835ab4670208639a724c1371e6` suite, `3e0b31ad2155ce7e89e84fa808167823fe938b31` workflow.
- Final actual Node20 GitHub Actions [43657700568](https://github.com/osawamas/value-hunter-ai/actions/runs/43657700568), job 132639821433 completed **SUCCESS**; logs `PASS docs/test_sgx_financial_join_v263.js`, `PASS docs/test_sgx_financial_filter_v264.js`, `Evidence smoke suite: 62/62 passed; rankings remain independently gated.`
- Overnight hourly autonomous automation `Automation_5cb3f22c5da88191a2dc9365d7a365d1` is enabled, scheduling hourly (frequency max). It already mandates high-impact user-facing functionality, source evidence, actual CI, no repeated completed work, and no unlicensed prices. Do NOT create duplicate tasks or claim work happens continuously between scheduled invocations.

## Next high-impact work to reach finished product
1. Integrate usable provenance-aware finance **details navigation**, as the 4 registered research rows now expose eligibility/exclusion state but need direct path to full existing finance details.
2. Acquire SGX authorized complete dated security-code master. SGX Aug 2026 aggregate 604 listed securities, indexed corporate 727 company hits, and 30 researched counters differ in scope/date. Do not compute fictitious coverage.
3. Acquire an **authorized SGX stock quote feed**, accurate timestamps, permitted web display and calculation rights; independent issuer accounting/parent equity and share-date validation for meaningful PER/PBR. No fabricated data, ranking remains 0.
4. Original SGXNet UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` still unavailable, don't guess URLs.
5. Check current listing/delist for 5WA P11, no false date claims. Public Pages owner settings prerequisite; don't mistake green preview workflow for published website.
6. Avoid adding another minor proof-only panel. Focus on production UX, data licensing, source acquisition, and real pipeline defects. Need real external-source verification before market numbers.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv264から継続。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v264.md`を読む。v262までSGXNet原本HTML19件SHA256検証・限定30銘柄コード検索/60テスト。v263でコード30件と財務登録7件を正式SGXコードで突き合わせ、共通 D05/O39/S68/U11 の4件の財務登録・ランキング除外状態を検索表へ表示。v264で財務登録済み4件／未登録26件で絞り込めるUI追加。旧テスト文言不整合修正済み。GitHub Actions #43657700568 は62/62 PASS。財務7、ランキング適格0。GitHub本番公開はPages設定待ち。次は検索から財務詳細への直接移動、公式全SGX銘柄と許諾付き株価、独立会計検証、未取得SGX原本を優先し、完成に直結する実装を複数進める。
