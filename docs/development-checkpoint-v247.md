# VALUE HUNTER AI — v247 checkpoint (2026-11-15 JST)

## Baseline and main
- Repository `osawamas/value-hunter-ai`; previous checkpoint `docs/development-checkpoint-v246.md`; initial main `ce322204020d3af38adb77ec2475891edf095232`. Check current main and Actions before changes because development is concurrent.
- Do not repeat v190–v246. Financial feed `docs/data/latest.json` last seen generated `2026-11-14T15:05:20.502940+00:00`; 7 registered verified financial symbols, ranking-eligible 0, rankings disabled. Third-party candidate universe 182 incomplete; fully official SGX master absent.

## Major new VERIFIED milestone — real SGX original PDF downloads
- Implemented `scripts/replay-sgx-original-pdf-v247.js`, using the v246 URL-safe downloader to **actually fetch all four previously-known primary SGX issuer PDF files again**, read v233/v237 source provenance sidecars, compute fresh SHA256 and byte sizes, and require exact equality before writing a v247 report.
- Sources: H02 Haw Par FY2025 results release (706,174 bytes, SHA256 `94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5`); V03 Venture FY2025 results release (520,231 bytes, `b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794`); H02 FY2025 annual report (4,754,838 bytes, `75328b273799863390e35a626e8e3679fe79ab853ef0a00f2775dd159364cfb8`); V03 FY2025 annual report (8,502,570 bytes, `eaebb6f4192ceb478c819b991eb18a3c34e43bf573388b9098b5e48b73b26a97`).
- Separate real-network GitHub Actions workflow `.github/workflows/sgx-original-pdf-replay-v247.yml` triggers on changes and manual workflow_dispatch. Actual run [43614340513](https://github.com/osawamas/value-hunter-ai/actions/runs/43614340513), job 132506000885, **completed SUCCESS**. Job log precisely states `v247 VERIFIED: 4 SGX original PDFs have expected SHA256 and length. No ranking promotion.`
- Actual new artifact: `sgx-original-pdf-live-replay-v247`, GitHub Actions artifact ID **14121073878**, 1,057 bytes (compressed), 30-day retention. It stores only the research JSON, NOT original PDF bytes. An actual retrievable byte-provenance report exists.
- Actual real PDF byte hashes match prior recorded observations, but repeated issuer filings remain SAME ISSUER financial sources, not independent third-party audit. Original files are NOT republished; market data rights absent; rankings 0.

## Engineering and independent offline CI
- Added `docs/test_sgx_pdf_replay_v247.js`, testing original URL allowed domain, expected known figures, hash mismatch, byte count mismatch, PDF magic, malicious final URL, malformed provenance, duplicate sources, illegal ranking promotion, successful mock replay. Integrated with `scripts/verify-evidence-v198.js` and `.github/workflows/bank-corporate-actions-v191.yml`.
- Real Node20 GitHub Actions evidence run [43614361847](https://github.com/osawamas/value-hunter-ai/actions/runs/43614361847), job 132506065309, **completed SUCCESS**: `PASS docs/test_sgx_pdf_replay_v247.js`; `Evidence smoke suite: 47/47 passed; rankings remain independently gated.`
- Commits: feature `1ddbe3428e91de8368af8d0f1b47fb536ddb1f82`; offline test `002d2dcf2c13fddcce2b6affbf4a0127806d89b7`; live workflow `40141240e032a6e52910a39518184cac642c163f`; CI test registration `8fc3a4c16aa0f1d68c41f9e94da1e860500c5b53`; workflow trigger `2566ca36f977f7610038165b4cd380d5e4db9c1c`.

## Remaining blockers, next work
1. UOB U11 2026-11-13 official original SGX announcement `SG261113OTHRHOAF` and OCBC O39 2026-11-12 notice `SG261112OTHRXH64` PDF `Anno_12Nov2026.pdf` still **NOT** obtained. ShareInvestor mirrored metadata/text is not the official original. Don't guess FileOpen file IDs or promote Nov13 shares.
2. Dated official FULL Singapore Exchange securities master unavailable; 11-security official board-lot subset and 182 third-party candidates are insufficient.
3. Current timestamped licensed SGX market quotes and display/redistribution/computation rights unavailable; do not scrape a viewer and call it licensed.
4. Independent accounting verification for issuers and owner equity still lacking. Do not enable ranking eligible status.
5. GitHub Pages live publish remains unverified; GitHub Actions evidence run success is not proof of public website deployment.

## Copyable handoff (Japanese)
VALUE HUNTER AI `osawamas/value-hunter-ai` をv247から継続。main最新、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v247.md`を確認、完了部分はやり直さない。v246でSGX公式原本PDF SHA取得器を作成。v247ではv233/v237のSGX公式原本4件（H02/V03各FY2025決算発表＋年報）をGitHub Actionsで実際に再ダウンロードしSHA256/サイズ照合に全件成功。ライブワークフロー #43614340513 SUCCESS、成果物ID14121073878。新テスト追加で別のNode20 Actions #43614361847も47/47 PASS。まだUOB11/13とOCBC11/12の公式原本URLは未取得、正規株価許諾/全SGX公式一覧/独立監査/Pages公開も未完。財務7社、ランキング0。次はSGX未取得原本と実用的な許諾付き株価取得を優先し、推測で数値を昇格させず開発を続ける。
