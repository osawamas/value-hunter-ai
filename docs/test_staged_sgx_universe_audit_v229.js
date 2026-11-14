"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {normalize}=require("../scripts/stage-sgx-csv-v199.js");
const {audit}=require("../scripts/audit-staged-sgx-universe-v229.js");
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const csv=[
 "Trading Code,Trading Name,Traded Currency,Security Type,Listing Board,Last,Bid,Ask,Volume",
 "AWX,AEM SGD,SGD,STOCK,MAINBOARD,5,4,6,100",
 "XWA,AEM USD,USD,STOCK,MAINBOARD,4,3,5,100",
 "GRN,ETF SGD,SGD,ETF,MAINBOARD,7,6,8,100",
 "GRE,ETF USD,USD,ETF,MAINBOARD,8,7,9,100",
 "G13,Genting,SGD,STOCK,MAINBOARD,1,1,1,100",
 "AAA,Stapled Trust,USD,STAPLED SECURITY,MAINBOARD,2,1,3,100"
].join("\n");
const staged=normalize(csv,{
 as_of_date:"2026-11-14",source_url:"https://www.sgx.com/securities/securities-prices?code=stocks"
});
const out=audit(staged,candidates,feed);
assert.equal(out.staged_security_counters,6);
assert.equal(out.unique_trading_codes,6);
assert.equal(out.duplicate_codes_across_currency_or_type,0);
assert.equal(out.classified_counter_counts.POTENTIAL_EQUITY,3);
assert.equal(out.classified_counter_counts.ETF,2);
assert.equal(out.classified_counter_counts.STAPLED_SECURITY,1);
assert.deepEqual(out.staged_distinct_codes_matching_third_party,["AWX","G13"]);
assert.deepEqual(out.staged_distinct_codes_matching_financial,["G13"]);
assert.equal(out.registered_financial_count_increment,0);
assert.equal(out.source_authenticated,false);
assert.equal(out.full_official_master_verified,false);
assert.equal(out.permitted_to_redistribute_market_data,false);
assert.equal(out.ranking_eligible_count,0);
assert.equal(out.market_prices_extracted,false);
assert.ok(!JSON.stringify(out).includes("AEM SGD"));
assert.ok(!Object.keys(out).some(k=>/price_sgd|market_cap|volume/i.test(k)));
for(const mutate of [
 (s,c,f)=>{s.source_authentication="VERIFIED"},
 (s,c,f)=>{s.full_sgx_universe_verified=true},
 (s,c,f)=>{s.items[0].last_price=5},
 (s,c,f)=>{s.original_csv_sha256="unknown"},
 (s,c,f)=>{s.distribution_rights_reviewed=true},
 (s,c,f)=>{c.candidates.push({...c.candidates[0]})},
 (s,c,f)=>{f.ranking_eligible_count=1}
]){
 const s=structuredClone(staged),c=structuredClone(candidates),f=structuredClone(feed);
 mutate(s,c,f);assert.throws(()=>audit(s,c,f));
}
console.log("v229 PASS: local CSV stage→security classification→reference overlap; rejects price leaks and any ranking promotion");
