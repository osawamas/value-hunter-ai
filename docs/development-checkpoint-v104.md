# VALUE HUNTER AI — v104 checkpoint (2026-11-14 JST)

## First read on next turn
Read GitHub main, latest Actions, `docs/data/latest.json`, `docs/data/sgx-universe-candidates.json`, `docs/data/sgx-provider-quality-v103.json`, `docs/development-checkpoint-v103.md`, and this document. Avoid repeating v97–v104 work.

## Completed v104
- Added research-only fail-closed typed bank quote validation `SGX_PDF_connection_probe/sgx_quote_gate_v104.py`, adversarial regression tests `test_sgx_quote_gate_v104.py`, and `.github/workflows/value-hunter-v104.yml`.
- Main commits: `c2bc361514bf8d1eba10a9a6cda8858cd1648e8b`, `d2c604ec5fae40c3b570540a963742c1af1dbe6e`, `3874973756c1a7285ff304c141d30dee1a9d9d01`.
- GitHub Actions CI #43547815940 SUCCESS: https://github.com/osawamas/value-hunter-ai/actions/runs/43547815940.
- Reject wrong SGX ticker+ISIN, currency, exchange MIC, source kind or URL, out-of-range / NaN / infinite prices, date without explicit +08:00, future/stale timestamp, conservative out-of-session timestamp, extra payload fields, repeated symbols.
- Outputs explicitly distinguish **input structural validation** from **genuine SGX quote acquisition or independent market data verification**. No parser or live quote download is claimed; test values are synthetic fixtures.
- CI confirms registered 7 issuers; 3 bank prices, shares and market caps remain null; ranking eligible remains zero. No `docs/data/latest.json` write, no PER/PBR or rankings promoted.
- Inputs are NOT assumed to come from a working current official SGX machine API. v104 is a validation gate only.

## v103 retained
- Third-party StocksSG 183 rows, 182 company candidates, 1 index `^STI` rejected. 182 provider `is_active=true`; this is NOT SGX official active status. Original API snapshot SHA agrees with sidecar, Actions #43547438813 succeeded.

## Research remaining
1. Dated, downloadable, complete SGX official listed-security master with observed ISINs, symbol, security type and board; independently reconcile against the **partial** 182 candidates. Official SGX securities prices page https://www.sgx.com/securities/securities-prices?code=stocks advertises Download, but no tested machine-readable official master identified yet.
2. UOB 2026-11-13 SG261113OTHRHOAF original: only secondary SGXNet mirrors available so far. 2026-11-12 official original confirmed, 34,000 share delta arithmetically agrees, not primary-source proof for 13-Nov.
3. OCBC 2026-11-12 SG261112OTHRXH64 attachment `Anno_12Nov2026.pdf`: secondary link found, SGX original attachment not yet acquired.
4. Real exchange-timestamped SGD quote automatic acquisition; v104 only tests hypothetical input structure. Need authenticated original snapshots, schema & timestamp provenance, stale checks, cross-source verification. Do not promote to market cap/PER/PBR until independently verified.
5. Pages activation still requires owner setting if not already enabled; CI does not prove live Pages URL.

## Next-thread copy
VALUE HUNTER AI `osawamas/value-hunter-ai` のv104の続きから開発。最初にmain、Actions、`docs/data/latest.json`、`docs/data/sgx-universe-candidates.json`、`docs/data/sgx-provider-quality-v103.json`、`docs/development-checkpoint-v104.md`を読む。v103で除外1件=株価指数 `^STI` と判明、候補182社は第三者APIによる未検証。v104では日時・銘柄・ISIN・SGD・取引所・取得元の厳格な検証ゲートと負例テストを実装しActions #43547815940成功。実株価の取得はまだ未実装。登録7社・ランキング0社、銀行価格・時価総額・PER/PBR未検証のまま。次は公式SGX銘柄マスター照合、UOB11/13とOCBC11/12のSGX原本、日時付き株価の実取得・独立照合に進み、GitHubに保存。未検証値をランキングに使わない。
