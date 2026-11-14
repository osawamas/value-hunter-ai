"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const original=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const batch1=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-research-v224.json","utf8"));
const batch2=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-extra-v227.json","utf8"));
const candidate=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function validate(a,b,d,c,f){
 assert.equal(a.schema_version,"sgx-official-multicurrency-subset-v220");
 assert.equal(b.schema_version,"sgx-dual-currency-identity-research-v224");
 assert.equal(d.schema_version,"sgx-official-dual-currency-extra-research-v227");
 assert.equal(d.source_url,"https://www.sgx.com/securities/trading");
 assert.equal(d.scope,"SECOND_SELECTED_BATCH_STATIC_IDENTITY_ONLY");
 assert.equal(d.not_a_complete_sgx_security_master,true);
 assert.equal(d.free_public_market_data_redistribution_authorized,false);
 assert.equal(d.current_sgx_listing_independently_authenticated,false);
 assert.equal(d.financial_feed_modified,false);
 assert.equal(d.ranking_eligible_count,0);
 assert.equal(d.new_pair_count,20);
 assert.equal(d.new_counter_count,40);
 assert.equal(d.pairs.length,20);
 assert.equal(a.groups.length,3);
 assert.equal(b.new_pairs.length,18);
 assert.equal(c.full_sgx_listing_completeness_verified,false);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 const expected=[
  "SRT|SGD|SRU|USD|ETF","ESG|SGD|ESU|USD|ETF",
  "LCU|USD|LCS|SGD|ETF","CXS|SGD|CXU|USD|ETF",
  "SQU|USD|SQQ|SGD|ETF","VND|USD|VNM|SGD|ETF",
  "ICU|USD|ICM|SGD|ETF","GRO|SGD|GRU|USD|ETF",
  "JJJ|SGD|JUS|USD|ETF","MCN|SGD|MCS|USD|ETF",
  "YLD|SGD|YLU|USD|ETF","JK8|SGD|VK8|USD|ETF",
  "EAA|SGD|EAU|USD|ETF","INC|SGD|ICH|CNH|ETF",
  "A93|SGD|A94|USD|ETF","CXN|RMB|CXO|USD|ETF",
  "SBO|SGD|SBV|USD|ETF","MXNU|GBP|MENU|SGD|REIT",
  "GLU|USD|GLS|SGD|ETF","ULG|USD|UGS|SGD|POTENTIAL_EQUITY"
 ];
 const codes=new Set([
  ...a.groups.flatMap(g=>g.counter_pair.map(x=>x.code)),
  ...b.new_pairs.flatMap(g=>[g.primary.code,g.secondary.code])
 ]);
 assert.equal(codes.size,42);
 for(let i=0;i<20;i++){
  const g=d.pairs[i],key=[g.primary.code,g.primary.currency,g.secondary.code,
   g.secondary.currency,g.instrument_category].join("|");
  assert.equal(key,expected[i]);
  assert.equal(g.official_table_source,"SGX_SECURITIES_TRADING_DUAL_CURRENCY");
  assert.equal(g.issuer_entity_identity_independently_verified,false);
  assert.equal(g.valuation_ready,false);
  assert.equal(g.ranking_eligible,false);
  assert.ok(g.underlying_name.length>=5);
  for(const id of [g.primary.code,g.secondary.code]){
   assert.ok(!codes.has(id));codes.add(id);
  }
 }
 assert.equal(codes.size,82);
 assert.equal(d.excluded_ambiguous_source_rows.length,1);
 assert.match(d.excluded_ambiguous_source_rows[0],/UPD\/UPU/);
 const third=new Set(c.candidates.map(x=>x.symbol));
 const overlap=[...codes].filter(x=>third.has(x)).sort();
 assert.deepEqual(overlap,["AWX","BS6","CFA","MXNU"]);
 return {groups:41,counters:82,candidate_match:overlap,missing_from_third_party:78,ranked_issuers:0};
}
validate(original,batch1,batch2,candidate,feed);
for(const mutate of [
 (a,b,d,c,f)=>{d.pairs[0].secondary.code="AWX"},
 (a,b,d,c,f)=>{d.pairs[17].instrument_category="POTENTIAL_EQUITY"},
 (a,b,d,c,f)=>{d.pairs[13].secondary.currency="SGD"},
 (a,b,d,c,f)=>{d.not_a_complete_sgx_security_master=false},
 (a,b,d,c,f)=>{d.pairs[0].valuation_ready=true},
 (a,b,d,c,f)=>{d.new_pair_count++},
 (a,b,d,c,f)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(original),b=structuredClone(batch1),d=structuredClone(batch2),
 c=structuredClone(candidate),f=structuredClone(feed);
 mutate(a,b,d,c,f);assert.throws(()=>validate(a,b,d,c,f));
}
console.log("v227 PASS: selected official SGX 41 groups/82 currency counters, 4 third-party overlaps, no ranking or rights promotion");
