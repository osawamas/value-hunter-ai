# VALUE HUNTER AI — v160 development checkpoint (2026-11-14 JST)

## Next work startup
Read current main, newest GitHub Actions, `docs/data/latest.json`, `docs/data/sgx-ranking-readiness-v117.json`, `docs/data/sgx-fy2025-audit-assurance-v132.json`, `docs/data/sgx-first-issuer-gate-v137.json`, `docs/data/sgx-annual-arithmetic-v140.json`, all OCBC v143–v160 sidecars, and this checkpoint. `docs/development-checkpoint-v150.md` has the v97–v150 history. Do not repeat work already completed; preserve original source SHA and no ranking promotion.

## v151 — real OCBC original PDF line contexts
- Created `SGX_PDF_connection_probe/sgx_ocbc_text_context_v151.py`, negative tests, dedicated workflow.
- Reads exact authentic OCBC Q3 SGX press release identified in v145 (official PDF SHA256 `420c481ac3eb12a667ef25d7ba7b8fb7ef3d62fb048ad673712c50ce7b75af53`).
- Captured bounded important line contexts/page locations in `docs/data/sgx-ocbc-text-context-v151.json`, allowing true bank quarterly accounting table extraction. CI [#43568353641](https://github.com/osawamas/value-hunter-ai/actions/runs/43568353641) **SUCCESS**.
- This diagnostic is text-layout research only and explicitly does not certify precise financial metrics.

## v152–v153 — exact 3Q / 9M group net profits
- `sgx_ocbc_exact_profit_v152.py` reads the actual original PDF, fixed SGX page/period/source SHA and exact unique table rows.
- 3Q26 Group net profit **2,042 million SGD** vs 3Q25 **1,978 million SGD** (arithmetic +3.2356% approximately, rounded issuer text +3%). 9M26 Group net profit **6,237 million SGD** vs 9M25 **5,677 million SGD** (arithmetic +9.864% approximately, rounded issuer text +10%). Values reconcile to v146 rounded issuer summaries 2.04b / 6.24b SGD.
- `docs/data/sgx-ocbc-exact-profit-v152.json`, SGX PDF page2 and page4 evidence, CI [#43568500358](https://github.com/osawamas/value-hunter-ai/actions/runs/43568500358) **SUCCESS**.
- `docs/ocbc-exact-profit-v153.js` Japanese dashboard panel, negatives and Pages tests. CI [#43568680455](https://github.com/osawamas/value-hunter-ai/actions/runs/43568680455) **SUCCESS**.
- These are OCBC issuer 2026 interim figures, not audited FY2025 values; no independently authenticated trading price, no current PER or ranking promotion.

## v154–v155 — 2026 OCBC banking income components
- `sgx_ocbc_bank_components_v154.py` extracts strictly labeled exact table rows from original SGX PDF and same SHA as v152.
- 3Q26 net interest income **2,313** million SGD, non-interest income **1,420**, sum **3,733**, operating profit before allowances **2,211**, allowances **52**.
- 9M26 net interest income **6,798**, non-interest **4,933**, sum **11,731**, operating profit before allowances **7,129**, allowances **424** (all SGD millions).
- `docs/data/sgx-ocbc-income-components-v154.json`; CI [#43568795310](https://github.com/osawamas/value-hunter-ai/actions/runs/43568795310) **SUCCESS** with actual source.
- `docs/ocbc-income-v155.js` safely renders bank-specific table separately from industrial revenue/operating metrics; negative tests and actual source test CI [#43568967493](https://github.com/osawamas/value-hunter-ai/actions/runs/43568967493) **SUCCESS**.

## v156–v157 — OCBC nine-month allowance composition
- `sgx_ocbc_allowances_v156.py` extracts exact 9M26 issuer original page5 text showing impaired-asset allowances **190**, non-impaired **234**, sum **424** SGD million, equal to v154 aggregate allowances.
- `docs/data/sgx-ocbc-allowances-v156.json`; CI [#43569090044](https://github.com/osawamas/value-hunter-ai/actions/runs/43569090044) **SUCCESS**.
- `docs/ocbc-allowance-v157.js` displays figures and refuses independent-credit-loss validation claims. CI [#43569267909](https://github.com/osawamas/value-hunter-ai/actions/runs/43569267909) **SUCCESS**.
- No independent provision adequacy check or current valuation certification.

## v158–v160 — OCBC Q3 bank balance table, selected exact rows
- `sgx_ocbc_balance_rows_v158.py` investigated actual official source's page8 balance table and selected surrounding line evidence; published `docs/data/sgx-ocbc-balance-rows-v158.json`, CI [#43569401358](https://github.com/osawamas/value-hunter-ai/actions/runs/43569401358) **SUCCESS**.
- `sgx_ocbc_bank_balance_v159.py` extracts 2026-09-30 **ordinary equity 60,899**, **equity attributable to equity holders of the Bank 63,347**, **total assets 731,689**, **net loans to customers 366,929**, **deposits of non-bank customers 461,462** (all million SGD), from exact SGX original PDF page8. The difference of **2,448** is NOT classified as non-controlling interests; ordinary equity is not automatically the same as all bank owner equity. `docs/data/sgx-ocbc-bank-balance-v159.json`, CI [#43569528450](https://github.com/osawamas/value-hunter-ai/actions/runs/43569528450) **SUCCESS**.
- `docs/ocbc-balance-v160.js` adds safely labeled Japanese 9/30 bank asset/capital snapshot. CI [#43569712603](https://github.com/osawamas/value-hunter-ai/actions/runs/43569712603) **SUCCESS**, including strict negative data tests. Actual browser screenshot still not independently observed.
- These are issuer interim disclosures only, not an independently audited complete annual bank balance sheet, not a present-day PBR denominator or live valuation. Never promote via v137 strict evidence gate.

## State as last checked
- Last main before saving THIS checkpoint: `a64884e30ec5af1bcd2230d7cc7a11021f667397`; next checkpoint commit will supersede.
- `docs/data/latest.json`, ranking readiness v117, FY2025 audit assurance v132, strict gate v137, annual arithmetic v140 **all matched timestamp `2026-11-14T07:03:38.425439+00:00`**. Check again after any v29 refresh.
- Financial registered 7 issuers; third-party StocksSG partial company candidates 182; ranking eligible **0**. Strict G13/S63 8-category gate remains 1/8 auditor-opinion-only confirmed, seven categories missing.
- Source OCBC bank quarterly 2026 is now a strong same-issuer original evidence set with authentic PDF hash, detailed quarter and 9-month amounts, issuer rounded-to-exact checks, provision breakdown, selected September balance sheet. **0 independent third-party numerical validations**, no 2026 auditor assurance and no authenticated original exchange quote.
- Missing still: OCBC 2026-11-12 treasury-use SGX original ref `SG261112OTHRXH64`, attachment `Anno_12Nov2026.pdf`; UOB 2026-11-13 repurchase SGX original ref `SG261113OTHRHOAF`; official complete current SGX securities master and permitted timestamped market price. A secondary ShareInvestor/SGinvestors listing is NOT authentic exchange source. No invention of URLs or current share counts.
- G13 official June30 ex-treasury 12,063,642,274 shares at 2026-06-30 only, S63 13-Nov-2026 corporate buyback 3,115,847,115 ex-treasury shares historical only. S63 Yahoo/EODData Nov13 closing-price agreement not an exchange execution tape.

## Priority v161+
1. Continue to source precise and independent OCBC current treasury share data from authentic 12 Nov SGX original (ref `SG261112OTHRXH64`), and UOB 13 Nov original (ref `SG261113OTHRHOAF`), maybe investigate issuer IR public SGX-linked document lists rather than guessing announcement URLs.
2. Distinguish OCBC ordinary equity from parent-attributable equity and bank regulatory CET1 ratio; implement fail-closed bank-specific financial schema with historical periods in a **consolidated** research view rather than adding indefinitely more panels.
3. Investigate licensed/authorized timestamped SGX price source and full official dated security master; existing sgx.com pages returned generic SPA HTML fallback, not machine-verifiable issuer lists.
4. Independent FY2025 parent equity / financial table verification G13/S63; keep all v137 strict original source and rank conditions.
5. Tighten data freshness UI: old 2026-06-30 share snapshots should not be tagged current merely because recent pipeline runs refresh; source dates matter.
6. Keep automated v29→v117/v132/v137/v140 sidecars coherent with concurrent commits, and test deployed Pages UI actual browsing when possible.

## Copyable next-thread handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` をv160から継続。最新main、Actions、`docs/data/latest.json`、`docs/data/sgx-ocbc-exact-profit-v152.json`、`docs/data/sgx-ocbc-income-components-v154.json`、`docs/data/sgx-ocbc-allowances-v156.json`、`docs/data/sgx-ocbc-bank-balance-v159.json`、`docs/development-checkpoint-v160.md`を読む。v151実SGX原本テキスト構造抽出。v152でOCBC 3Q26純利益2,042百万SGD、9M26 6,237百万SGD（前年同期1,978/5,677）を原本から精密取得。v153で日本語UI。v154で純金利収入3Q2,313・9M6,798、非金利収入3Q1,420・9M4,933、引当金3Q52・9M424百万SGDを原本解析。v155日本語UI。v156で9M引当金190+234=424を原本照合しv157で日本語表示。v158で銀行貸借行を発見、v159でOCBC 2026年9月末普通株主持分60,899、銀行株主帰属持分63,347、総資産731,689、貸出金366,929、預金461,462百万SGDを原本抽出、v160で日本語UI化。各最終専用Actionsは実データ成功。発行会社の同一原本であり独立第三者検証ではない。財務登録7社、第三者銘柄候補182社、ランキング適格0社を維持。次はOCBC11/12・UOB11/13 SGX原本、最新株式数、正規SGX価格・公式銘柄マスター、独立数値検証、古い株数の鮮度表示を優先。未検証値をPER/PBR/ランキングに昇格させずGitHubに継続保存。
