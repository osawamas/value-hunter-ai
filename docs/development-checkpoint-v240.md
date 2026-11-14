# VALUE HUNTER AI — v240 checkpoint (2026-11-15 JST)

## Source of truth and non-duplication
Repository `osawamas/value-hunter-ai`. Read current main and `docs/development-checkpoint-v239.md`, `docs/development-checkpoint-v238.md`, `docs/data/latest.json`, `docs/data/sgx-big3-bank-research-v186.json` before future work. Another thread already completed v190–v238; never restart from v189 simply because a stale user prompt says v189.

## CI findings
- v239 exact per-symbol evidence source test **genuinely passed**, push Actions run [43609899227](https://github.com/osawamas/value-hunter-ai/actions/runs/43609899227), job 132492415314. Node20 logs: `PASS docs/test_sgx_two_document_crosscheck_v238.js`, `Evidence smoke suite: 40/40 passed; rankings remain independently gated.`
- Latest observed main before v240: `d9a1a8b39a091dc3db6d6ff5feb34afa1bb9082b` (a concurrent v238 checkpoint after v239); get new head before next modification.
- v240 commit [b9fc0eb3](https://github.com/osawamas/value-hunter-ai/commit/b9fc0eb3d9e676667a3ade1c936c88fb02c2873b): strengthened `docs/test_sgx_two_document_crosscheck_v238.js`, pinning H02/V03 exact issuer name, official SGX annual/results PDF URLs, byte sizes, and all four existing SHA256s. Rejects silent sidecar source substitution even if a plausible different SHA/URL/file passes format checks. Negative tests explicitly mutate digests, bytes, URLs, issuer labels.
- v240 real push Actions [43610436495](https://github.com/osawamas/value-hunter-ai/actions/runs/43610436495), job 132494130588 **completed success**; Node20 logs `PASS docs/test_sgx_two_document_crosscheck_v238.js`, `Evidence smoke suite: 40/40 passed`.
- No new financial input records or valuation promotions. `docs/data/latest.json` last observed generated `2026-11-14T15:05:20.502940+00:00`, financial registered 7, ranking eligible 0.
- Four original-document hashes validated against already recorded GitHub Actions PDF evidence, NOT independently recalculated from newly acquired PDFs in this work. Correctly keep independent third-party verification FALSE. A successful test is not independent audit, current shares, SGX official licensed price feed, or published Pages.

## Priority next
1. Original SGX Nov 2026 UOB/OCBC share buyback announcement source, dated ex-treasury capital; do not treat syndicated mirror as primary.
2. Lawful timestamped SGX licensed quote and distribution rights, official dated full SGX master.
3. Independent, source-qualified accounting verification, especially H02 parent equity/NCI distinction and V03 owner equity; block ranking until validated.
4. Check Pages setting and actual successful deployment (historically pages job SKIPPED even with workflow overall SUCCESS).
5. Reduce UI duplication and increase verifiable coverage instead of adding redundant headline aggregates.

## Compact handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv240から継続。v239でH02/V03の銘柄別原本証拠のテストを厳格化しActions #43609899227 40/40 PASS。v240でH02/V03のSGX年次報告書・決算発表の4 PDFについて発行会社、URL、バイト数、SHA256の厳密固定チェックと偽陽性対策の負テスト追加、commit b9fc0eb3、Actions #43610436495で40/40 PASS。登録7銘柄、ランキング0、許諾あるSGX株価・最新自己株控除後株式数・SGX公式全銘柄一覧・独立財務検証は未完了。Pagesの実公開も未確認。最新mainとActions、`docs/data/latest.json`、`docs/development-checkpoint-v240.md`を読み、完了済み作業を繰り返さず開発を継続。
