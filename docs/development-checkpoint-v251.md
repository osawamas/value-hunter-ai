# VALUE HUNTER AI — v251 checkpoint (2026-11-15 JST)

## Resume from latest main
- Repo `osawamas/value-hunter-ai`. At start main `c6fc74f54ea43e2e282a75164046fcc6e25134b7` (v250 checkpoint). Always refresh main, GitHub Actions and `docs/data/latest.json` before editing because other workflows/threads may push commits.
- Prior `docs/development-checkpoint-v250.md`: real ZIP+localhost browser asset validation, 50/50 PASS, GitHub Pages deploy SKIPPED due owner setting. Avoid repeating that.
- Latest initially observed financial feed `2026-11-14T16:17:42.130634+00:00`; 7 registered financial stocks, ranking eligible 0; source licensed SGX price feed and independent audit absent.

## New primary SGX market-size evidence
- Discovered **original SGX Group Monthly Market Statistics Report, August 2026**, available `https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20Update_Aug%202026.ashx?App=Announcement&FileID=903915`.
- Published month-end figures: **SGX Mainboard 406**, **SGX Catalist 198**, total **604 listed securities** at **2026-08-31**. Original statistics PDF section 'Issuer Services: Number of Listings (month-end)' and page 1 summary `Total Number of Listed Securities 604`. The stated security count scope excludes GDRs, hedge funds and debt securities (report footnote).
- An independently retrieved official SGX rulebook specifies that its official list includes Mainboard, Global Listing Board and Catalist; `https://rulebook.sgx.com/rulebook/71-official-list`. Neither this rule nor monthly aggregate is the complete code-level securities directory.
- **Important semantic caveat:** SGX published aggregate **604 securities at Aug 2026** is NOT Nov15 real-time universe, and the app's **182 third-party company candidates** use a potentially different universe/unit. Do not report `182/604` as validated coverage %, and do not simply infer a precise 422 missing companies. Neither dataset is the official full-date security-master file.
- New research sidecar `docs/data/sgx-official-monthend-aug2026-v251.json` records original official PDF URL, month, two board counts and overall total, as-of and scope, and explicitly false full code directory, license, financial/ranking approval. Commit `fc6ac7f21cd9b4cb6f0df365611316e7a45781a4`.
- Updated existing `docs/universe-coverage-audit-v205.js`: adds `compareOfficialMonthEnd` while retaining original `reconcile`, loads the new PDF statistics sidecar and shows dated 604 total, 406/198 split, and separate 182 candidate count on the existing coverage panel, with explicit non-comparability and no ranking promotion. Commit `1e00f686f0fd3071e6151e39cb2e84ec2302b51f`.
- New `docs/test_sgx_official_monthend_v251.js` verifies exact SGX source URL, mainboard+catalist=604, date, null permission/promotion, and tamper/negative cases; added to `scripts/verify-evidence-v198.js` and existing integrity Actions workflow path triggers. Commits `59d83326da06f652cfa6a03846b23f6d851222f2`, `17a6200b97e9966df5ec0fce59de01f4583f0ec7`, `d82d91a32fed8fd4fee54a1790a16bebb2d76270`.
- Actual Node20 GitHub Actions [43616473120](https://github.com/osawamas/value-hunter-ai/actions/runs/43616473120), job `132512516957`, **completed success**. Logs: `PASS docs/test_sgx_official_monthend_v251.js` and `Evidence smoke suite: 51/51 passed; rankings remain independently gated.`

## Major unresolved tasks
1. Acquire dated complete official SGX security master / issuer directory, beyond August aggregate 604 and partial third-party 182.
2. Licensed SGX timestamped quote access + display/processing/redistribution permissions; avoid unauthorized price replay. Independently validate accounting and issuer parent equity.
3. Locate UOB Nov13 `SG261113OTHRHOAF` official original and OCBC Nov12 `SG261112OTHRXH64` official attachment `Anno_12Nov2026.pdf`; no real primary originals found yet. Never promote syndicated data to official.
4. GitHub Pages public deploy still needs owner settings; history showed `pages` job skipped though preview ZIP available. Verify actual deploy job, not the green overall workflow.
5. Focus next iterations on official securities-directory source or source acquisition, not simply duplicating view panels or adding nonfunctional tests. Ranking eligible remains 0.

## Copyable next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv251から継続。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v251.md`を先に確認して、完了済み作業を繰り返さない。v250は実ZIP+localhost HTTP検証50/50 PASS。v251でSGX公式2026年8月月次統計原本から上場証券604件（Mainboard406/Catalist198）を取得し、現在の第三者候補182件とは単位・時点が違うため単純な取得率計算をしない形で既存UIに統合。Actions #43616473120 51/51 PASS。財務7、ランキング0。未取得：SGX公式銘柄コード全リスト、許諾ある時刻付き株価、UOB11/13・OCBC11/12の原本、独立財務監査、Pagesの実公開。これらの本質的な課題から開発続行。
