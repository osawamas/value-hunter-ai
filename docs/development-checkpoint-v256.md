# VALUE HUNTER AI — v256 checkpoint (2026-11-15 JST)

## Verified current base
- Repo `osawamas/value-hunter-ai`; start main `8f455d24e596e7765d7b06a4e1882004babc2749` (v255 checkpoint). Always fetch latest main, Actions, `docs/data/latest.json`, and checkpoint at next work; other workflows edit main.
- At initial look, `docs/data/latest.json` financial registered 7, ranking eligible 0; v255 55/55 PASS, eight SGXNet issuer/ISIN/code pairs plus OCBC code from SGX official trading table. Do not repeat prior investigations.

## v256: complete *one page* of SGX corporate-information issuer code identity
- SGX's indexed corporate-info page `https://www.sgx.com/securities/corporate-information?page=24` shows **20 company names (entries 461–480)**, but does not publish codes on indexed page. v253 saved these 20 company names, v254 independently cross-referenced OCBC O39, v255 found 8 issuer-code matches with indexed SGXNet announcement sections. v256 located **11 more** on `links.sgx.com/1.0.0/corporate-announcements/...` direct-source-domain indexed SGXNet announcements:
  1. OCTOPUS (APAC) HOLDINGS LTD. / `43A` / `SG1CF0000001` / `SG260812OTHR3OBX` / 2026-08-12
  2. OIO HOLDINGS LIMITED / `KUX` / `SGXE73993458` / `SG260410OTHRZ71Y` / 2026-04-10
  3. OLAM GROUP LIMITED / `VC2` / `SGXE65760014` / corporate action `SG260814DVCACQHU` / 2026-08-14; a separate SGXNet announcement includes a perpetual security `VT0B` belonging to the same issuer; **do not merge multi-securities into issuer counts**
  4. ONEAPEX LIMITED / `5SY` / `SG2C90967473` / replacement capital reduction action `SG260722DECRDHI0` / 2026-10-26; **capital reduction, not proof of unaltered share count**
  5. OTS HOLDINGS LIMITED / `OTS` / `SGXE18096938` / `SG261015OTHR6TIG` / 2026-10-15
  6. OUE REIT / `TS0U` / `SG2G60000004` / `SG260923OTHRY6XX` / 2026-09-23; **REIT, not conventional operating company**
  7. OUHUA ENERGY HOLDINGS LIMITED / `AJ2` / `BMG6843Q1033` / `SG260813OTHR4YWA` / 2026-08-13
  8. OVERSEAS EDUCATION LIMITED / `RQ1` / `SG2F49989922` / `SG260410OTHRPR4P` / 2026-04-10
  9. OXLEY HOLDINGS LIMITED / `5UX` / `SG2F25986140` / `SG260829OTHR94HJ` / 2026-08-29
  10. PACIFIC ANDES RESOURCES DEVLTD / `P11` / `BMG6845B1046` / `SG261016OTHRODOS` / 2026-10-16; **restructuring and potential liquidation/delisting**
  11. PACIFIC CENTURY REGIONAL DEVTS / `P15` / `SG1J17886040` / `SG260331OTHRGORS` / 2026-03-31
- Exact individual source URLs and these announcement dates/ISINs saved in `docs/data/sgx-net-eleven-codes-v256.json`; commit `f692030b4ddf1449dd579c66d697e02122769c61`. Classified `INDEXED_SGXNET_ANNOUNCEMENT_HTML_WITH_ISSUER_SECURITIES_SECTION`; **primary-domain indexed announcement text is NOT independently downloaded+SHA-verified raw HTML bytes**.
- New `scripts/integrate-sgx-twenty-v256.js` merges v253 20 issuer names, v255 eight code filings, v256 eleven code filings and v254 OCBC O39 official boardlot reference; all 20 have distinct historically supported codes, 19 dated SGXNet announcement sources plus OCBC static trading list. **20/20 refers solely to ONE indexed corporate-info page; NOT full current SGX listed universe**. Live listing status, market-data license, finance audit and ranking remain false. Output `build/research/sgx-twenty-codes-v256.json`. Commits `af5dd7815ebc7a271408bdb1e3c88b178a1c8f59`, independent-build fix `78fea08595fde2a74e071f02d3139955b9b4693c`.
- New `docs/test_sgx_twenties_v256.js` tests exact 20 codes, distinct identities, negative modifications and actual standalone CLI; commit `eaa2aeeaaba4e5224a6f15bfebb5ec8e2bee6297`. Included in `scripts/verify-evidence-v198.js` commit `98ab16c9f0f9e2ed96da6869075056ff15fd47d0`, workflow trigger commit `ad15b3a157a3b9097710933f6fc69ade3f62228a`. Upload artifact added commit `063eabca2da49fc8d878dfb0ab2e6f30dacb742f`.
- Real GitHub Actions [43623638606](https://github.com/osawamas/value-hunter-ai/actions/runs/43623638606) job 132534582282 **completed SUCCESS**, logs `PASS docs/test_sgx_twenties_v256.js`, `Evidence smoke suite: 56/56 passed; rankings remain independently gated.`. Actual artifact `sgx-twenty-issuer-codes-v256` ID **14124594837**. Do not conflate report with full SGX universe.

## Outstanding priorities for v257+
1. Need ACTUAL complete dated SGX security-code master in authorized format, not one page at a time; SGX August 2026 604 **securities** vs indexed 727 **company records** refer to different scope/time. Find trusted bulk original and usage terms. If bulk source cannot be obtained, prioritize ability to check active listing and delist/suspension status, particularly P11 and 5WA.
2. Prioritize usable app financial data/quote integration: SGX licensed timestamped market-data access and redistribution/processing rights still absent, issuer accounting independently verified numbers lacking. Do not enable rankings on static code identity.
3. UOB Nov13 `SG261113OTHRHOAF` and OCBC Nov12 `SG261112OTHRXH64` original share-change documents still unacquired.
4. Public GitHub Pages deployment still skipped because owner Settings > Pages > GitHub Actions not enabled. v249/v250 ZIP preview tested locally but not public.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv256から継続。最新main・Actions・`docs/data/latest.json`・`docs/development-checkpoint-v256.md`を読む。v253のSGX企業名20件に、v254 OCBC O39、v255公式SGXNet開示8件、v256さらに11件のコード・ISIN・開示番号を記録して全20社の過去時点コードを厳密照合。v256では43A/KUX/VC2/5SY/OTS/TS0U/AJ2/RQ1/5UX/P11/P15を追加。`scripts/integrate-sgx-twenty-v256.js`と統合CI #43623638606 は56/56 PASS、GitHub Actions JSON artifact 14124594837。20/20は企業情報の1ページだけでSGX全体ではない。非公開化・再編・清算リスク銘柄が含まれるため現在の上場状態も未確定。財務7社、ランキング適格0社。公式全銘柄コード原本、許諾付き株価、第三者財務監査、UOB・OCBC原本、GitHub Pages本公開が未完。次は本物の一括公式台帳か最新上場状態を優先。
