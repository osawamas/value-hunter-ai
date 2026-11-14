"use strict";
const assert=require("node:assert/strict");
const {typeCategory,inspect}=require("../scripts/classify-sgx-counters-v202.js");
const cases={
 "Stapled Security":"STAPLED_SECURITY",
 "STAPLED SECURITIES":"STAPLED_SECURITY",
 "L&I Product":"LEVERAGED_PRODUCT",
 "BUSINESS TRUST":"BUSINESS_TRUST",
 "Daily Leverage Certificate":"LEVERAGED_PRODUCT",
 "REIT":"REIT","ETF":"ETF",
 "STOCK":"POTENTIAL_EQUITY",
 "UNKNOWN_OR_UNMAPPED":"UNCLASSIFIED"
};
for(const [x,expected] of Object.entries(cases))assert.equal(typeCategory(x),expected);
const identities=[
 ["SET","EUR","Stapled Security","STAPLED_SECURITY"],
 ["SEB","SGD","Stapled Security","STAPLED_SECURITY"],
 ["LSS","SGD","L&I Product","LEVERAGED_PRODUCT"],
 ["LSU","USD","L&I Product","LEVERAGED_PRODUCT"],
 ["BS6","SGD","Stock","POTENTIAL_EQUITY"],
 ["SO7","RMB","Stock","POTENTIAL_EQUITY"]
];
const d={schema_version:"sgx-manual-security-list-staging-v199",
 original_file_is_sgx_verified:false,full_sgx_universe_verified:false,
 quote_columns_stripped:true,licensed_quote_access:false,
 distribution_rights_reviewed:false,ranking_enabled:false,
 ranking_eligible_count:0,item_count:identities.length,
 items:identities.map(([trading_code,trading_currency,instrument_type])=>({
  trading_code,trading_currency,instrument_type,trading_name:trading_code,
  listing_board:"UNKNOWN"}))};
const r=inspect(d);
assert.deepEqual(r.rows.map(x=>x.category),identities.map(x=>x[3]));
assert.equal(r.total_counters,6);
assert.equal(r.counts.STAPLED_SECURITY,2);
assert.equal(r.counts.LEVERAGED_PRODUCT,2);
assert.equal(r.candidate_equity_counters_not_verified_issuers,2);
assert.ok(r.rows.every(x=>!x.is_validated_company_issuer&&!x.valuation_ready&&!x.ranking_eligible));
assert.equal(r.status,"STAGING_ONLY_NOT_OFFICIAL_MASTER");
for(const edit of [
 d=>{d.full_sgx_universe_verified=true},
 d=>{d.licensed_quote_access=true},
 d=>{d.ranking_eligible_count=1},
 d=>{d.items[0].instrument_type="Stock";d.item_count++}
]){
 const bad=structuredClone(d);edit(bad);assert.throws(()=>inspect(bad));
}
console.log("v226 PASS: official SGX stapled and L&I product types stay distinct from ordinary equity and rankings");
