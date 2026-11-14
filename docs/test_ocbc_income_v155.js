"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ocbc-income-v155.js");
function sample(){
 const sha="a".repeat(64);
 const feed={schema_version:"value_hunter_web_v29",ranking_enabled:false,
  ranking_eligible_count:0,records:[{symbol:"O39",ranking_eligible:false}]};
 const profits={status:"OCBC_Q3_EXACT_PROFIT_ROWS_PRIMARY_PDF_RECONCILED",
  record:{official_press_sha256:sha,official_press_pdf_url:"https://links.sgx.com/official.pdf"}};
 const records={"3Q26":[2313,1420,3733,2211,52],"9M26":[6798,4933,11731,7129,424]};
 const components={status:"OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED",
  schema_version:"sgx-ocbc-bank-components-probe-v154",
  record:{schema_version:"sgx-ocbc-bank-income-components-v154",
   symbol:"O39",period_end_date:"2026-09-30",original_pdf_sha256:sha,
   original_pdf_url:"https://links.sgx.com/official.pdf",
   reported_income_components_arithmetically_added:true,
   same_issuer_primary_unaudited_2026_research:true,
   independent_third_party_numerical_verification:false,
   bank_loan_loss_full_reperformance:false,validated_fy2025_audited_per:false,
   current_quote_shares_verified:false,ranking_eligible:false,
   bank_statements:Object.fromEntries(Object.entries(records).map(([k,v])=>[k,{
     unit:"SGD_millions",net_interest_income:v[0],non_interest_income:v[1],
     combined_interest_and_noninterest_income:v[2],operating_profit_before_allowances:v[3],
     allowances_charged:v[4]}]))}};
 return [feed,components,profits];
}
const x=validate(...sample());
assert.equal(x[0].combined_interest_and_noninterest_income,3733);
assert.equal(x[1].combined_interest_and_noninterest_income,11731);
for(const change of [
 ([f,c,p])=>c.record.independent_third_party_numerical_verification=true,
 ([f,c,p])=>c.record.bank_statements["3Q26"].net_interest_income=999,
 ([f,c,p])=>c.record.bank_statements["9M26"].allowances_charged=0,
 ([f,c,p])=>c.record.original_pdf_sha256="b".repeat(64),
 ([f,c,p])=>f.ranking_eligible_count=1,
]){
 const a=sample();change(a);assert.throws(()=>validate(...a));
}
console.log("v155 OCBC banking-only income component UI safely verified");
