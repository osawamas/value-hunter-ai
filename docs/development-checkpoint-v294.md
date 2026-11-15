# VALUE HUNTER AI — v294 checkpoint (2026-11-15 JST)

## Resume first
- Repo `osawamas/value-hunter-ai`. Read actual latest main, GitHub Actions, `docs/data/latest.json`, this checkpoint and v293; hourly autonomous automation can push concurrently. Don't duplicate existing task.
- v293 SGX Group 2026-11-12 October release live HTML retrieval returned shell-only 9,858 bytes, SHA 1a2e1d0a..., no article content and correctly FAILED; original October SGX Monthly Statistics PDF not yet found. v292 primary/research guards 82/82 PASS, ranking 0/7.

## v294 substantive new PRIMARY SGX-ST October IPO evidence
- Found first-party SGX-ST **Equity - Listing Confirmation** originals (not secondary mirrors), from SGXNet:
  1. **Deluge Corporation Limited** Mainboard symbol **9DC**, ISIN **SGXE96931105**, trading begins **2026-10-16 09:00 SGT**. Original issuer/exchange listing confirmation `https://links.sgx.com/1.0.0/corporate-announcements/CVLKKOOOXPT8BOG2/bbddb7499b65b97ca34526cab59adee3f7b34f2be274cc0d38cbd7b74e0ee857`, announcement `SG261016OTHRW0SM`. Separate first-party SGX public listing page `https://www.sgx.com/listing-ceremony/deluge`; SGX release `https://links.sgx.com/FileOpen/20261016%20SGX%20Stock%20Exchange%20welcomes%20Deluge%20Corporation%20Limited%20to%20Mainboard.ashx?App=Announcement&FileID=907236`.
  2. **Mi Material Holding Limited** Mainboard symbol **MIM**, ISIN **SGXE49931863**, trading begins **2026-10-28 14:00 SGT**. Original SGX-ST listing confirmation `https://links.sgx.com/1.0.0/corporate-announcements/7553QXPI35CQ2A7V/fc20bc2859953005b225dc9ffbaf98694e9305222473599a64b927ab90629c7a`, announcement `SG261027OTHR92A1`. Original issuer balloting PDF `https://links.sgx.com/FileOpen/MiMH-%20Balloting%20Press%20Release.ashx?App=Announcement&FileID=909430`; market research report `https://api2.sgx.com/sites/default/files/2026-10/MiM_IPO_27Oct2026_Final.pdf` is third-party analyst despite hosting on SGX domain, NOT an independent audit.
- New `docs/data/sgx-october-ipo-listing-v294.json` stores two original dated SGX listing events with verified symbol + ISIN + board + exact start date/time + direct original URLs and ref; financials, current quote, current listing status, market rights, complete master all flagged unverified. **This removes two IPO symbol/ISIN unknowns from v292 but does not make them investable.**
- New `scripts/verify-sgx-october-ipo-v294.js` enforces strict source identity, scheme, dates/ISIN, no ranking rights. New `docs/test_sgx_october_ipo_v294.js` asserts both records, rejects mutated ISINs/dates/ref URLs/source scope and checks actual seven-record financial feed still rank-eligible zero. Registered in evidence suite & CI workflow watched paths.
- GitHub Actions final evidence suite #43672293390 **SUCCESS 83/83** and #43672291100 SUCCESS. Browser ZIP #43672277870 SUCCESS, actual file:// Chrome #43672277856 SUCCESS, dashboard publish workflow #43672277881 SUCCESS (does not prove public Pages deploy).
- Commits: `cdedefe20d722cff16e106b1c799f5a17db16ad2` data; `304751e054ad37c7eecf29eaa75f7365076358f5` verifier; `816ff8b36958a6fb135974014037403031d50105` test; `70eb8e28c0e2807586fd8fd8999c7905add33fbc` suite; `a8630b2459ef202c0d57dcdb51f0ea877dac988a` workflow.

## Work still blocked
1. Original SGXNet **October 2026 monthly statistics PDF** (attachment name `SGX Monthly Statistics Report Update_Oct 2026.pdf`) not located/hashed. October end-listed count 605 remains third-party reported only; do not infer from two IPOs.
2. Complete current dated official SGX security master with reuse rights not available; v294 two exact historical admission events do not prove all currently active stocks.
3. Licensed current quotes for browser display + non-display analytics + redistribution if needed not granted. Independent financial verification and current ex-treasury share counts incomplete; formal ranking 0/7.
4. Original UOB 2026-11-13 SG261113OTHRHOAF and OCBC 2026-11-12 SG261112OTHRXH64 share filings still missing.

## Next tasks
- Link these two new identities into a *separately staged* candidate universe list, without changing the seven source-verified finance records or claiming official master. Examine existing 30 historical codes to avoid accidental duplicates. Prioritize actual SGXNet October PDF/file and official current active master.
- Improve independent corporate financial verification for 9DC/MIM only with original issuer filings and appropriate source licensing; don't treat the analyst valuation as audited independently.
- Continue regular hourly task, no duplicate automation.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v294から継続。main/Actions/latest.json/development-checkpoint-v294.mdを読む。今回SGX-ST原本上場確認を実際に発見。Deluge 9DC/ISIN SGXE96931105/10月16日09:00、Mi Material MIM/ISIN SGXE49931863/10月28日14:00を各SGXNet原本URLと告知番号で記録し、JSONと検証・テストをGitHubへ実装。CI #43672293390 **83/83 PASS**、ZIP/実Chrome成功。これは10月2社の上場イベントの原本検証であって10月月次全銘柄数605の証明ではない。10月統計PDF原本、最新完全台帳、許諾付き株価、独立財務監査が未完、ランキング0/7。次は公式コード候補の段階的統合と本当の原本取得を優先。既存毎時自動開発タスク有効。
