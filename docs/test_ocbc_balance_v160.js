"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./ocbc-balance-v160.js");
function inputs(){
 const data={schema_version:"value_hunter_web_v29",ranking_enabled:false,ranking_eligible_count:0,
  records:[{symbol:"O39",ranking_eligible:false}]};
 const items={
 ordinary_equity:{sgd_millions:60899},
 equity_attributable_to_bank_equity_holders:{sgd_millions:63347},
 total_assets:{sgd_millions:731689},
 net_customer_loans:{sgd_millions:366929},
 deposits_nonbank_customers:{sgd_millions:461462}};
 const bank={schema_version:"sgx-ocbc-q3-balance-probe-v159",status:"OCBC_Q3_PRIMARY_BANK_BALANCE_ROWS_PARSED",
  record:{schema_version:"sgx-ocbc-q3-bank-balance-selected-v159",symbol:"O39",period_end_date:"2026-09-30",
   unit:"SGD_millions",selected_bank_items:items,attributable_equity_less_ordinary_equity:2448,
   difference_is_not_identified_as_noncontrolling_interest:true,
   bank_ordinary_equity_not_assumed_group_equity:true,not_full_audited_bank_statement:true,
   independent_third_party_numbers_verified:false,current_treasury_adjusted_shares_verified:false,
   current_sgx_quote_verified:false,pbr_eligible:false,ranking_eligible:false,
   official_source_pdf_url:"https://links.sgx.com/1.0.0/corporate-announcements/A9CW58STOPTDX0HG/original.pdf"}};
 return [data,bank];
}
assert.equal(validate(...inputs()).ordinary,60899);
for(const mutate of [
 ([f,b])=>b.record.selected_bank_items.ordinary_equity.sgd_millions=63347,
 ([f,b])=>b.record.difference_is_not_identified_as_noncontrolling_interest=false,
 ([f,b])=>b.record.pbr_eligible=true,
 ([f,b])=>b.record.current_sgx_quote_verified=true,
 ([f,b])=>f.ranking_eligible_count=1
]){
 const x=inputs();mutate(x);assert.throws(()=>validate(...x));
}
console.log("v160 dated original bank shareholder equity safely separate from PBR");
