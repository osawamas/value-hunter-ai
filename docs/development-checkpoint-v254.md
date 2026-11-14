# VALUE HUNTER AI — v254 checkpoint (2026-11-15 JST)

## Start safely
- Repository `osawamas/value-hunter-ai`, initial head `f93c6aa8df3781cb5c6dfccd02cbe93c5b8a5aa7` (v253). Before changing files read latest main, Actions, `docs/data/latest.json`, and checkpoint. Other workflows may update main.
- Prior v253 indexed 20 issuer names/boards from search-indexed SGX corporate-info page, without code or original raw page verification; index has unverified 727 count. The August 2026 SGX monthly report's 604 listed securities are a different as-of/scope; don't subtract 727 and 604. Financial feed registered 7 stocks, ranking eligible 0.
- Already recorded 11 issuer/code/currency pairs on SGX official static board-lot page `docs/data/sgx-official-batch-seed-v196.json`. Already recorded 82 examples of multi-currency counters in v220/224/227. Do not double-count codes or infer unique companies. Official source `https://www.sgx.com/securities/trading`.

## Actual v254 feature
- New `scripts/reconcile-sgx-official-code-v254.js`: computes narrow **source-backed issuer name → trading code join** between v253 search-indexed issuer names and v196 official static code list, using a **single explicit reviewed alias**:
  - indexed `OVERSEA-CHINESE BANKING CORP` (MAINBOARD), SGX indexed page `https://www.sgx.com/securities/corporate-information?page=24`
  - official trading-table `Oversea-Chinese Banking Corporation Ltd` (O39 / SGD) on `https://www.sgx.com/securities/trading`
  - One joined OCBC company/counter; **19 other page-24 issuer names remain code=null** and are not guessed/fuzzy matched. Neither official primary page bytes of indexed page nor dated current official security master obtained; source flags distinguish the evidence quality.
- Output local research report `build/research/sgx-indexed-to-official-code-v254.json`, no changes to `docs/data/latest.json`; investor ranking eligible 0. Code commit `438afe8409bc5eeaf4ce031f7f9869b1a5e97a32`.
- New `docs/test_sgx_official_code_join_v254.js`, negative mutations for aliases, board, code, currency, duplicate issuer, source authenticity and ranking; also invokes actual CLI and compares emitted JSON to pure derivation. Test commit `8a3d415ef48056cac1c21f9ca5aca8966fbce9e5`.
- Integrated in `scripts/verify-evidence-v198.js` commit `1c23a59426dbe35e1fc5754f74d6fefed0ab91f5`, CI paths `.github/workflows/bank-corporate-actions-v191.yml` commit `998734d345f3a89284197c6708fc7eec6fac4e7e`.
- CI workflow now saves report `sgx-issuer-code-intersection-v254` as 30-day artifact, added commit `feef324bcd9df236e0797d11936962b185472061`.
- Real GitHub Actions [43622723980](https://github.com/osawamas/value-hunter-ai/actions/runs/43622723980), job 132531757389 **completed SUCCESS**, log `PASS docs/test_sgx_official_code_join_v254.js`, `Evidence smoke suite: 54/54 passed; rankings remain independently gated.` Report artifact `sgx-issuer-code-intersection-v254` ID **14124204390**, test summary `sgx-source-integrity-v218-results` ID 14125011765. See job/run; artifact is research only. Earlier run 43622686086 also 54/54 success.
- Research original web findings: SGX trading official URL presents 11 codes including O39 and many dual-currency counter pairs; SGX Securities Prices viewer search-index contains more code/name rows but direct opening yields unsupported-browser shell; price viewer licensing still NOT obtained.

## Open high-priority tasks
1. Obtain official **dated full** SGX securities master with actual primary source file, codes and permitted reuse. The existing official static 11 and 82 multi-currency counters are subsets, not full listing; indexed 20 issuer names are not primary bytes. For v253 19 unlinked, don't autofill from loosely similar company names.
2. Real SGX originals UOB U11 Nov13 `SG261113OTHRHOAF` and OCBC O39 Nov12 `SG261112OTHRXH64` attachment `Anno_12Nov2026.pdf` still missing. Do not infer current stock count from syndicated secondary pages.
3. Licensed timestamped SGX quote feed with publication/analysis/redisplay rights and independent issuer financial numeric audits; ranking 0 until the data gates are satisfied.
4. GitHub Pages public site deployment still SKIPPED pending repo owner Settings → Pages → Build and deployment → Source: GitHub Actions. Verified local ZIP is not deployed page.
5. Prefer a large authentic primary original source/data capture or actual publish setup rather than more marginal source-only tests.

## Copyable handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv254から継続。最新main、Actions、`docs/data/latest.json`、`docs/development-checkpoint-v254.md`を確認。v253のSGX企業名20件に、v196 SGX公式売買単位資料の取引コードを厳密照合し、OCBCのみ O39/SGD で対応確認、残り19社はコードnullのまま。新CLI `scripts/reconcile-sgx-official-code-v254.js` と負テスト登録、統合CI #43622723980 は54/54 PASS、照合JSON artifact ID14124204390保存。全SGX公式コードマスター、UOB/OCBC最新原本、時刻付き株価ライセンス、第三者独立財務検証、Pages実公開は未完了。財務登録7、ランキング適格0。新しい本物の原本取得を最優先にして次へ。
