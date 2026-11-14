"use strict";
const assert=require("node:assert/strict");
const {inspect,typeCategory}=require("../scripts/classify-sgx-counters-v202.js");
const rows=[
 ["D05","SGD","STOCK"],["AAA","USD","REIT"],["BBB","SGD","ETF"],
 ["CCC","SGD","BUSINESS TRUST"],["DDD","SGD","STRUCTURED WARRANT"],
 ["EEE","USD","BOND"],["FFF","SGD","UNKNOWN"],["G07","SGD","COMMON SHARE"],
 ["AAA","SGD","REIT"]
];
const staged={
 schema_version:"sgx-manual-security-list-staging-v199",
 original_file_is_sgx_verified:false,full_sgx_universe_verified:false,
 quote_columns_stripped:true,licensed_quote_access:false,
 distribution_rights_reviewed:false,ranking_enabled:false,ranking_eligible_count:0,
 item_count:rows.length,
 items:rows.map(([trading_code,trading_currency,instrument_type])=>({
 trading_code,trading_currency,instrument_type,trading_name:"Test "+trading_code}))
};
const result=inspect(staged);
assert.equal(result.total_counters,9);
assert.equal(result.candidate_equity_counters_not_verified_issuers,2);
assert.equal(result.counts.REIT,2);
assert.equal(result.counts.ETF,1);
assert.equal(result.counts.BUSINESS_TRUST,1);
assert.equal(result.counts.WARRANT,1);
assert.equal(result.counts.DEBT,1);
assert.equal(result.counts.UNCLASSIFIED,1);
assert.equal(typeCategory("stock"),"POTENTIAL_EQUITY");
assert.equal(typeCategory("unknown"),"UNCLASSIFIED");
assert.equal(result.status,"STAGING_ONLY_NOT_OFFICIAL_MASTER");
assert.ok(result.rows.every(x=>!x.valuation_ready&&!x.ranking_eligible&&!x.is_validated_company_issuer));
for(const mutate of [
 x=>{x.original_file_is_sgx_verified=true},
 x=>{x.ranking_eligible_count=1},
 x=>{x.quote_columns_stripped=false},
 x=>{x.item_count++},
 x=>{x.items[0].trading_currency="SG"},
 x=>{x.items.push({...x.items[0]})},
 x=>{x.licensed_quote_access=true},
 x=>{x.full_sgx_universe_verified=true}
]){
 const bad=structuredClone(staged);mutate(bad);assert.throws(()=>inspect(bad));
}
console.log("v202 PASS: multi-currency security counter classification without company promotion");
