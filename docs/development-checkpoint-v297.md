# VALUE HUNTER AI — v297 checkpoint (2026-11-15 JST)

## Resume
- Inspect latest main commit, Actions, `docs/data/latest.json`, `docs/development-checkpoint-v297.md`; hourly autonomous task already exists, do not duplicate.
- v296 added fully tested HTTP and file:// browser view of 32 dated historical SGX code identities, including 9DC/MIM IPO original listing evidence. 85/85 integrity suite. Formal ranking eligible 0/7.

## v297 substantive first-party financial primary-source acquisition
**Three NEW first-party original PDFs actually downloaded and byte-hashed by GitHub Actions, not just source links:**
1. Deluge Corporation (9DC): Registered MAS IPO prospectus **6 Oct 2026** https://links.sgx.com/FileOpen/Deluge%20Corporation%20Limited%20-Final%20Prospectus%20%286%20October%202026%29.ashx?App=IPO&FileID=6803 ; **8,575,301 bytes; SHA256 `6472db7e48bc45db8a056d196157d03589bf4ef880ee94eba3fd837b53c028de`**. Contains FY ended March 2024/2025/2026 audited combined financials and independent auditor references; source's audit is HISTORICAL, not independently updated 2026 Nov verification.
2. Mi Material Holding (MIM): Registered MAS IPO prospectus **19 Oct 2026** https://links.sgx.com/FileOpen/Mi%20Material%20Holding%20Limited-MASRegistration-Appendix%28Final%20Prospectus%29.ashx?App=IPO&FileID=6809 ; **8,930,729 bytes; SHA256 `d6b49948af8167e6d2443ae22f7538907c46e94d62b414843e8444abc05f342c`**. Contains audited 2023/2024/2025 FY and unaudited 2026 H1. Source includes FY2023/2024/2025 issuer revenues US$39.8m/46.8m/65.3m and H1 2026 US$53.7m (H1 2025 US$25.6m), but **these numbers not yet converted to investment feed or separately independently audited by app**.
3. MIM issuer 9M2026 29 Oct 2026 update https://links.sgx.com/FileOpen/MiM_9M2026_Press_Release_29102026.ashx?App=Announcement&FileID=909744 ; **160,619 bytes; SHA256 `19d2b43322c36001e560d14f43650b0f6feab5e280770e42bb529ee63cd5ef60`**. Issuer-reported 9M2026 revenue US$91.5m and adjusted PAT US$25.7m; this is *not* third-party audited, adjusted non-IFRS net metric, and a 9M2026-vs-FY2025 comparison is NOT year-on-year growth.

## Actual implemented code and CI
- `docs/data/sgx-ipo-financial-documents-v297.json`: original SGX-hosted file URLs, issuer IDs, dates, audited scope, verified exact hashes, byte sizes, and GH Actions source ID.
- `scripts/replay-sgx-ipo-financial-pdfs-v297.py`: direct remote GET with tight SGX URL checks, strict PDF magic, size max, `pdftotext` content verification, SHA256+byte equality against pinned proof (fail closed on revised source), JSON evidence output in `build/research/sgx-ipo-original-financial-pdfs-v297.json`. Does NOT redistribute underlying PDFs, quote or share counts.
- `scripts/test_sgx_ipo_financial_pdfs_v297.py`: offline mutational security tests reject unofficial URLs/changed schema, invalid SHA, sizes and provenance; HTML masquerading as PDF fails.
- `.github/workflows/sgx-ipo-original-financial-v297.yml`: actual full original PDF replay, preserve proof JSON artifact after success/failure.
- **Initial real PDF replay #43676027936 SUCCESS 3/3**, source bytes SHA captured above; pin hashes commit cbe4d1cb..., rerun with pinned digest and strict enforcement **#43676131428 SUCCESS**. PDF proof artifact in Actions.
- `docs/test_sgx_ipo_pdf_hashes_v297.js` asserts exact three original hashes, documents audit periods, runs negative Python tests, source quote/license and financial feed remains zero. Registered in `scripts/verify-evidence-v198.js` and watched workflow paths.
- **Latest actual SGX source evidence suite #43676207521 SUCCESS 86/86**, as independently read from Actions job logs. Also #43676204386 SUCCESS. Browser ZIP run #43676178391 SUCCESS, file:// Chrome #43676178390 SUCCESS, dashboard publish workflow #43676178372 SUCCESS.
- Latest implementation commits: 9c43de6e source manifest, 809cf5c4 live downloader, 2904688e Python test, 495cb9bf workflow, cbe4d1cb hash manifest, 5b0a1c14 SHA enforcement, f93c77d0 negative mutations, db00fcbf JS test, 45be8349 evidence suite, be0618d1 workflow.
- No edits to `docs/data/latest.json` ranking records, no licensed quotes imported, no new investable symbol; financial feed registered 7, ranking 0/7.

## Next v298 priority
1. Parse audited FY revenue/operating income/net profit and equity precisely from two downloaded and hash-verified originals. Preserve FY-end 31 Mar for Deluge vs 31 Dec for MIM, currency SGD vs USD, scale, and auditor scope; differentiate MIM post-listing 9M2026 issuer-update (non-audited, adjusted PAT) from audited FY2025.
2. Reconcile comparable periods only (MIM FY2024 vs FY2025; H1 2025 vs H1 2026; 9M2026 vs 9M2025 only if source acquired). No annual vs nine-month YoY mislabel.
3. Find October SGXNet monthly statistics original PDF `SG261112OTHREO8V`; full official active security master, licensed both market quote display/non-display usage, and independent financial verification remain missing. Bank UOB Nov13 and OCBC Nov12 original share notices remain missing.
4. Formal ranking eligible 0/7, genuine live valuation not active. Avoid endless source-only gates; focus extracting useful precise issuer finance data next.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` はv297まで開発。main、Actions、latest.json、本checkpointを読む。SGX原本PDF3本をGitHub Actionsから実ダウンロード・PDFテキスト照合・SHA256固定。9DC目論見書8,575,301B SHA6472db7e...、MIM目論見書8,930,729B SHAd6b49948...、MIM 9M業績リリース160,619B SHA19d2b433...。実取得 #43676027936 3/3成功、固定ハッシュ再検証 #43676131428 成功。既存CIへ追加して #43676207521 は86/86 PASS。目論見書の監査対象は過去FYで、MIM9M2026は非監査の発行体資料。次v298では原本から財務値（売上・利益・資本）を年度・通貨・監査種別を厳格に分けて抽出する。正式ランキング0/7、SGX全現行台帳・株価利用許諾未完。毎時自動タスク有効。
