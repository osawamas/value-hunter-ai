"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const newData=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-research-v224.json","utf8"));
const original=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function inspect(d,o,c,f){
 assert.equal(d.schema_version,"sgx-dual-currency-identity-research-v224");
 assert.equal(d.scope,"SELECTED_OFFICIAL_PAIRS_NOT_EXHAUSTIVE");
 assert.equal(d.source_url,"https://www.sgx.com/securities/trading");
 assert.equal(d.complete_official_sgx_security_master,false);
 assert.equal(d.quote_fields_collected,false);
 assert.equal(d.public_redistribution_rights_verified,false);
 assert.equal(d.original_issuer_entity_relationship_independently_verified,false);
 assert.equal(d.financial_feed_modified,false);
 assert.equal(d.ranking_eligible_count,0);
 assert.equal(o.schema_version,"sgx-official-multicurrency-subset-v220");
 assert.equal(o.complete_sgx_list,false);
 assert.equal(o.groups.length,3);
 assert.equal(d.new_pair_count,18);
 assert.equal(d.new_counter_count,36);
 assert.equal(d.new_pairs.length,18);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(c.full_sgx_listing_completeness_verified,false);
 const expected=[
 ["NS8U","USD","P7VU","SGD","BUSINESS_TRUST"],
 ["M62","USD","QS0","SGD","ETF"],
 ["P5P","USD","QR9","SGD","ETF"],
 ["O9P","USD","QL3","SGD","ETF"],
 ["N6M","USD","QL2","SGD","ETF"],
 ["I98","USD","QK9","SGD","ETF"],
 ["BS6","SGD","SO7","RMB","POTENTIAL_EQUITY"],
 ["BYI","USD","BYJ","SGD","ETF"],
 ["CFA","SGD","COI","USD","ETF"],
 ["SET","EUR","SEB","SGD","STAPLED_SECURITY"],
 ["LG9","USD","TID","SGD","ETF"],
 ["CYC","SGD","CYB","USD","ETF"],
 ["MMS","SGD","MMT","USD","ETF"],
 ["ZHY","RMB","ZHD","USD","ETF"],
 ["HST","SGD","HSS","USD","ETF"],
 ["O87","USD","GSD","SGD","ETF"],
 ["YYY","SGD","YYR","RMB","ETF"],
 ["UD1U","SGD","8U7U","EUR","REIT"]
 ];
 const originalCodes=o.groups.flatMap(x=>x.counter_pair.map(y=>y.code));
 const seen=new Set(originalCodes);
 for(let i=0;i<d.new_pairs.length;i++){
  const x=d.new_pairs[i],e=expected[i];
  assert.deepEqual([x.primary.code,x.primary.currency,x.secondary.code,
   x.secondary.currency,x.instrument_category],e);
  assert.ok(x.underlying_name.length>=5);
  assert.equal(x.same_instrument_pair_source,"SGX_OFFICIAL_STATIC_TRADING_TABLE");
  assert.equal(x.issuer_financial_data_verified,false);
  assert.equal(x.official_current_listing_independently_verified,false);
  assert.equal(x.ranking_eligible,false);
  for(const code of [x.primary.code,x.secondary.code]){
   assert.ok(!seen.has(code),"Duplicate with previous official subset");
   seen.add(code);
  }
 }
 assert.equal(seen.size,42);
 const third=new Set(c.candidates.map(x=>x.symbol));
 const overlap=[...seen].filter(x=>third.has(x)).sort();
 assert.deepEqual(overlap,["AWX","BS6","CFA"]);
 assert.ok(!f.records.some(x=>seen.has(x.symbol)));
 return {pairs:d.new_pairs.length+o.groups.length,counters:seen.size,
  overlap,missing_from_third_party:seen.size-overlap.length,
  verified_full_official_master:false,verified_unique_issuer_count:0,
  ranking_eligible:0};
}
const result=inspect(newData,original,candidates,feed);
for(const mutate of [
 (d,o,c,f)=>{d.new_pairs[0].secondary.code="AWX"},
 (d,o,c,f)=>{d.new_pairs[0].instrument_category="ETF"},
 (d,o,c,f)=>{d.complete_official_sgx_security_master=true},
 (d,o,c,f)=>{d.public_redistribution_rights_verified=true},
 (d,o,c,f)=>{d.new_pairs[0].ranking_eligible=true},
 (d,o,c,f)=>{d.new_counter_count++},
 (d,o,c,f)=>{f.ranking_eligible_count=1}
]){
 const d=structuredClone(newData),o=structuredClone(original),
 c=structuredClone(candidates),f=structuredClone(feed);
 mutate(d,o,c,f);assert.throws(()=>inspect(d,o,c,f));
}
console.log("v224 PASS: 21 official selected dual currency groups/42 counters, 3 in 182 third-party candidates, no issuer/ranking promotion");
