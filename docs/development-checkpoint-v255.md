# VALUE HUNTER AI — v255 checkpoint (2026-11-15 JST)

## Start from latest main
- Repo `osawamas/value-hunter-ai`, initial main `0c2786f449a3d8c1db222c48ba4d0e9237780317` after v254. Always read latest main and Actions, `docs/data/latest.json`, and this checkpoint before next edits; concurrent activity possible.
- Prior v254 linked only OCBC O39/SGD among the 20 v253 search-indexed SGX corporate names, from another official SGX static board-lot table. v254 54/54 CI passed.
- Feed observed `2026-11-14T16:17:42.130634+00:00`, seven financial registered securities, ranking eligibility 0.

## Major new achievement: **8 more issuer code identities from actual SGXNet announcement originals**
- Web research located source `https://links.sgx.com/1.0.0/corporate-announcements/...` official SGXNet announcement HTML pages whose **Issuer & Securities** section explicitly lists company name, ISIN and ticker, rather than third-party guesses:
  - OCEANUS GROUP LIMITED: `579`, `SG1M80907371`, announcement `SG260814OTHROJYF`, 2026-08-14; URL `https://links.sgx.com/1.0.0/corporate-announcements/832MZ2RT52XMRZZU/a904993d72a95b69a3a4d21362022b682f02e0ecf7f91f1bf6cf929b52a3be1c`
  - OILTEK INTERNATIONAL LIMITED: `HQU`, `SGXE21569376`, `SG260410OTHRH0PY`, 2026-04-10; URL `https://links.sgx.com/1.0.0/corporate-announcements/I9AZB0MRAS1VW6F1/`
  - OKP HOLDINGS LIMITED: `5CF`, `SG1M55904841`, `SG260401OTHRXIAW`, 2026-04-01; URL `https://links.sgx.com/1.0.0/corporate-announcements/WRMX0ZXC0RXZZU34/`
  - OLD CHANG KEE LTD.: `5ML`, `SG1W49939232`, `SG261113OTHR9OGS`, 2026-11-13; URL `https://links.sgx.com/1.0.0/corporate-announcements/06B3W0K0MPRLGZLS/64873a5f376fa86f3fae3f7793eaab84d66de830bab81ad049b948c4c24d5dd9`
  - OSSIA INTERNATIONAL LTD: `O08`, `SG1D61018413`, `SG260629OTHR4XNV`, 2026-06-29; URL `https://links.sgx.com/1.0.0/corporate-announcements/5C10OKSACD572VP3/`
  - OUE HEALTHCARE LIMITED: `5WA`, `SG2F86994413`, `SG260824OTHRTOJR`, 2026-08-24; URL `https://links.sgx.com/1.0.0/corporate-announcements/VLW3DK2EY2Q1NFJF`
  - OUE LIMITED: `LJ3`, `SG2B80958517`, `SG261102OTHRXFXJ`, 2026-11-02; URL `https://links.sgx.com/1.0.0/corporate-announcements/9BTTW0YUVV5IONC8/1aab789ab24878459bb0085d34d774205b0b284468136ed333c310a3fa7ed51f`
  - OXPAY FINANCIAL LIMITED: `TVV`, `SGXE15822534`, `SG260813OTHRH7WL`, 2026-08-13; URL `https://links.sgx.com/1.0.0/corporate-announcements/TB7V4NB74JRGHQHR/`
- **As-of announcement** only. In particular, OUE Healthcare had subsequent 2026 scheme-of-arrangement/privatisation disclosures; **do not assume currently listed** from the August code. Latest quote, shares and security-master completeness are still unverified.
- New `docs/data/sgx-official-issuer-code-filings-v255.json`, commit `9eaf500ce220a4cd8cba100470e76f941654fe9b`: eight rows including exact URL, announcement ref/date, ISIN, trading code, explicit no fresh quote/current-listing verification and rank gating.
- New `scripts/reconcile-sgx-filing-codes-v255.js`, commit `e913fcd712c0d8583203ef7e025c8e3af81c43b6`, does exact name and pinned code/ISIN/announcement validation against v253 20-row issuer index; outputs only `build/research/sgx-direct-filing-issuer-code-v255.json`. Eight newly original-sourced code identities from this batch, plus existing OCBC O39 in v254 -> **9 of 20 named issuers have a separately supported code**, 11 lack cross-source verification. Doesn't turn search-index page into original bytes.
- New `docs/test_sgx_filing_codes_v255.js`, commit `4b8966c4727ce34d55063fa7458e7141040476cd`; negative mutations for incorrect ticker, ISIN, announced date, original URL, duplicates, false current price/listed status and illegal ranking. Test invokes real CLI and verifies report.
- Registered in `scripts/verify-evidence-v198.js` commit `fb55511f58ee6548fd5dfaae35b1a6bc09551cb6` and `.github/workflows/bank-corporate-actions-v191.yml` commit `585b79e5c0ad914f67d961f73057f11f34b87045`; new artifact upload `sgx-primary-issuer-codes-v255` retained 30 days commit `2964b66acbc11b02f0b68fdc55392a9ad525eee5`.
- Final real Node20 CI [43623152892](https://github.com/osawamas/value-hunter-ai/actions/runs/43623152892), job 132533077567, **SUCCESS** with `PASS docs/test_sgx_filing_codes_v255.js`, `Evidence smoke suite: 55/55 passed; rankings remain independently gated.`. Source-join report artifact **14124623937** `sgx-primary-issuer-codes-v255`.
- This IS genuine original SGXNet issuer code data, not 8 fake test rows, but it's a tiny dated subset and **not a complete official security master**, legally permissioned live quote feed, independent numeric accounting audit, or current listing status.

## Still blocking practical ranking and deploy
1. Dated full official SGX listed-code master with a permitted/traceable export, not only 20 search-index names, 8 SGXNet filing code samples and 11 board-lot static examples. If continuing SGXNet one-by-one, ensure it helps move toward a real master and avoid equating document identity with active listing.
2. SGX UOB 2026-11-13 `SG261113OTHRHOAF` original buyback source and OCBC 2026-11-12 `SG261112OTHRXH64` original PDF attachment still missing; historical sources must not be upgraded to present-day shares.
3. Explicit SGX quote rights for application redisplay and timestamped analysis; actual provider/API contract, not a public search widget. Independent third-party financial value and parent-equity validation.
4. GitHub Pages owner must enable GitHub Actions as Pages source. A successful overall workflow with `pages=skipped` is not a live website. Local ZIP preview works.

## Next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv255から継続。main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v255.md`を確認。v254はOCBC O39を11銘柄のSGX公式売買単位表と照合。v255でSGXNet公式開示の原本HTMLからさらに8社について会社名・取引コード・ISIN・公告参照番号を実取得し、`docs/data/sgx-official-issuer-code-filings-v255.json`に保存。8社は579/HQU/5CF/5ML/O08/5WA/LJ3/TVV、従来のOCBC O39と合わせ20社中9社に別の公式出典によるコードあり。これは各開示日時点の証拠で、現在上場状況・価格・全銘柄完全性は未確認。Node20 Actions #43623152892 は55/55 PASS、JSON成果物ID14124623937。財務登録7、ランキング0。UOB11/13とOCBC11/12公式原本、SGX公式全銘柄マスター、許諾ある株価、独立監査、Pages本番公開は未完。原本ベースの実データ取得を優先し続行。
