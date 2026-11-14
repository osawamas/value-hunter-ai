"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ocbc-exact-profit-v153.js");
function fixture(){
 const source="https://links.sgx.com/original.pdf",sha="a".repeat(64);
 const f={schema_version:"value_hunter_web_v29",ranking_enabled:false,
  ranking_eligible_count:0,records:[{symbol:"O39",ranking_eligible:false}]};
 const exact={schema_version:"sgx-ocbc-precise-bank-profit-probe-v152",
  status:"OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED",
  record:{schema_version:"sgx-ocbc-q3-exact-bank-profit-v152",
   symbol:"O39",period_end_date:"2026-09-30",official_press_sha256:sha,
   official_press_pdf_url:source,group_profit_3q26_sgd_millions:2042,
   group_profit_9m26_sgd_millions:6237,exact_statement_profit_rows:[
    {current_sgd_millions:2042,comparison_sgd_millions:1978,pdf_page:2},
    {current_sgd_millions:6237,comparison_sgd_millions:5677,pdf_page:4}
   ],same_issuer_rounded_summary_arithmetic_reconciled:true,
   independent_third_party_profit_verification:false,
   fy2025_audit_opinion_applies_to_2026_q3:false,
   current_quote_or_shares_verified:false,annual_per_or_pbr_promoted:false,
   ranking_eligible:false}};
 const rounded={schema_version:"sgx-ocbc-q3-metrics-probe-v146",
   status:"OCBC_2026Q3_PRIMARY_BANK_PROFIT_PARSED",
   record:{original_sgx_pdf_sha256:sha,original_sgx_press_release_url:source}};
 return [f,exact,rounded];
}
const rows=validate(...fixture());
assert.equal(rows.length,2);
assert.ok(rows[0].yoy>3.2&&rows[0].yoy<3.3);
assert.ok(rows[1].yoy>9.8&&rows[1].yoy<10);
for(const change of [
 ([f,e,q])=>e.record.exact_statement_profit_rows[1].comparison_sgd_millions=0,
 ([f,e,q])=>e.record.independent_third_party_profit_verification=true,
 ([f,e,q])=>e.record.current_quote_or_shares_verified=true,
 ([f,e,q])=>e.record.official_press_sha256="b".repeat(64),
 ([f,e,q])=>f.ranking_eligible_count=1
]){
 const v=fixture();change(v);assert.throws(()=>validate(...v));
}
console.log("v153 exact OCBC quarterly and nine-month issuer profit comparison valid");
