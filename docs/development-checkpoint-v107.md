# VALUE HUNTER AI — v107 checkpoint (2026-11-14 JST)

## Restart instructions
Read current main and latest GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-provider-quality-v103.json`, `docs/data/sgx-master-reconciliation-v105.json`, `docs/data/sgx-issuer-s68-v106.json`, `docs/data/sgx-d05-primary-code-link-v107.json`, and this checkpoint. Do NOT repeat prior v97–v107 work.

## v106 achieved, verified by live CI
- Added `SGX_PDF_connection_probe/sgx_issuer_page_v106.py`, `test_sgx_issuer_page_v106.py`, `.github/workflows/value-hunter-v106.yml`.
- Run https://github.com/osawamas/value-hunter-ai/actions/runs/43548528998 **success**; live direct HTTP GET to `https://links.sgx.com/1.0.0/corporate-information/1637` succeeded.
- Published `docs/data/sgx-issuer-s68-v106.json`: issuer SINGAPORE EXCHANGE LIMITED, ISIN SG1J26887955, MAINBOARD, page updated text 11/11/2026 08:45:30 AM, HTML SHA256 d8bfdf8ef4c227cc3b03700ef2fb36613042b68843a8b0b73a6e0a3b6ffb6008.
- Important: the official issuer page **did not directly state S68 ticker**, so `symbol_directly_observed_on_sgx_page=false`, `symbol_to_isin_official_master_join_verified=false`. No total SGX listing count/quote/valuation/eligibility inference.

## v107 achieved, verified by live CI
- Found SGX official issuer and securities announcement page `https://links.sgx.com/1.0.0/corporate-announcements/U6RBLH1JFNDV1QZT/4d07e8c30959620ceca55f7e574d69cf8270329fdcd719a5a2992624f3474f80`. It explicitly prints `DBS GROUP HOLDINGS LTD - SG1L01001701 - D05`, and announcement reference SG260309OTHROF8R, broadcast 09-Mar-2026 07:33:28.
- Added `SGX_PDF_connection_probe/sgx_announcement_link_v107.py`, `test_sgx_announcement_link_v107.py`, `.github/workflows/value-hunter-v107.yml`.
- Early CI #43548653869 **failure** because duplicate negative case wasn't rejected. Attempted fix #43548709546 **failure** due to over-escaped Python regex. Corrected `\s` escaping and reran; CI https://github.com/osawamas/value-hunter-ai/actions/runs/43548766668 **SUCCESS**.
- Live SGX HTTP succeeded and published `docs/data/sgx-d05-primary-code-link-v107.json`: explicit D05 <=> ISIN SG1L01001701 <=> DBS GROUP HOLDINGS LTD with exact announcement reference, HTML SHA256 367ed57b88378fb053e004c28d9b3d9a68bd19251cb853f201394951cecd7842.
- Critical limitations: this is **one historical SGX announcement** linking ticker/ISIN, not proof of current live trading, active security as of today, or a complete exchange master. It changes neither `docs/data/latest.json` nor valuation/eligibility.

## Live primary research / discovery
- UOB individual SGX company profile: `https://links.sgx.com/1.0.0/corporate-information/1131/1000`, UNITED OVERSEAS BANK LIMITED, ISIN SG1M31001969, Mainboard, update 09/10/2026 according to search. This is not a direct U11 symbol binding; seek a security-bearing official announcement.
- DBS profile `https://links.sgx.com/1.0.0/corporate-information/991`; OCBC `https://links.sgx.com/1.0.0/corporate-information/1943` (OCBC full name, ISIN SG1S04926220, MAINBOARD, updated 11/13/2026). SGX official announcement URLs with security code and ISIN are preferable for explicit binding.
- UOB 2026-11-13 `SG261113OTHRHOAF` and OCBC 2026-11-12 `SG261112OTHRXH64` original announcements/attachments still NOT located in this session; secondary syndication not promotable.
- Official downloadable full master still not found; `docs/data/sgx-master-reconciliation-v105.json` retains NOT_AVAILABLE and 0 exchange-master confirmed of 182 partial third-party candidates.
- v104 quote date/identity validator is only a test gate; no stable live exchange automatic quote collection completed.

## Remaining priorities
1. Generalize v107 parser safely for UOB/O39 and other candidates only with *known exact SGX URLs* and sufficient official source identity evidence, independent cross-source reconciliation; do not guess numeric page IDs or treat third-party names as official confirmations.
2. Try SGX official securities download / master (authentic file schema, date and source); adapt v105 schema from actual official download if found.
3. Find UOB Nov13 and OCBC Nov12 original SGXNet docs/attachment; verify announcement ref and issuer.
4. Reliable SGX timestamped SGD quote actual ingestion and independent checks, no valuations without independently verified updated shares.
5. Maintain third-party company candidates 182, registered financial universe 7, ranking eligible 0.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` をv107から継続。まずmain、最新Actions、`docs/data/latest.json`、`docs/data/sgx-universe-candidates.json`、`docs/data/sgx-issuer-s68-v106.json`、`docs/data/sgx-d05-primary-code-link-v107.json`、`docs/development-checkpoint-v107.md`を読む。v106でSGX公式S68発行体ページを実HTTP取得し企業名・ISIN・Mainboardを確認、CI #43548528998成功（S68コード直接対応は未照合）。v107でSGX公式DBS発表の企業名・ISIN SG1L01001701・銘柄D05の同一ページ対応を実HTTP確認、重複対策を修正後CI #43548766668成功。候補182社は第三者API、SGX全銘柄マスター未取得。財務登録7社・ランキング0社、株価と現在株式数は未検証。次はUOB/OCBC等の公式銘柄コード・ISIN照合、UOB11/13とOCBC11/12原本、完全公式マスター、時間付き実株価取得を進め、未検証値をPER/PBR・ランキングに使わずGitHubへ保存。
