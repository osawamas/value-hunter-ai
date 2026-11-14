"use strict";
const assert=require("node:assert/strict"),{validate}=require("./ocbc-allowance-v157.js");
function f(){
 const source="https://links.sgx.com/test.pdf",sha="a".repeat(64);
 const feed={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
   records:[{symbol:"O39",ranking_eligible:false}]};
 const breakdown={schema_version:"sgx-ocbc-allowances-probe-v156",
   status:"OCBC_9M26_ALLOWANCE_BREAKDOWN_RECONCILED_IN_PRIMARY_PDF",
   record:{schema_version:"sgx-ocbc-9m26-allowance-components-v156",
    symbol:"O39",period_end_date:"2026-09-30",unit:"SGD_millions",
    impaired_asset_allowances_9m26:190,non_impaired_asset_allowances_9m26:234,
    total_allowances_9m26:424,computed_composition_difference:0,
    original_sgx_sha256:sha,original_sgx_pdf_url:source,
    exact_text_original_same_issuer_confirmed:true,
    full_expected_credit_loss_validation:false,
    independent_third_party_financial_verification:false,
    current_quote_or_shares_verified:false,ranking_eligible:false}};
 const income={status:"OCBC_3Q26_9M26_PRIMARY_BANK_INCOME_COMPONENTS_PARSED",
  record:{original_pdf_sha256:sha,original_pdf_url:source,
   bank_statements:{"9M26":{allowances_charged:424}}}};
 return [feed,breakdown,income];
}
assert.equal(validate(...f()).total,424);
for(const mutate of [
 ([a,b,c])=>b.record.impaired_asset_allowances_9m26=191,
 ([a,b,c])=>b.record.independent_third_party_financial_verification=true,
 ([a,b,c])=>c.record.bank_statements["9M26"].allowances_charged=500,
 ([a,b,c])=>a.ranking_eligible_count=1
]){
 const x=f();mutate(x);assert.throws(()=>validate(...x));
}
console.log("v157 OCBC allowance original breakdown display safe");
