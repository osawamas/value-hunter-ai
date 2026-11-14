"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const doc=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function validate(d,c,f){
 assert.equal(d.schema_version,"sgx-official-multicurrency-subset-v220");
 assert.equal(d.source_url,"https://www.sgx.com/securities/trading");
 assert.equal(d.complete_sgx_list,false);
 assert.equal(d.quote_fields_included,false);
 assert.equal(d.source_terms_or_market_data_rights_verified,false);
 assert.equal(d.issuer_entity_id_independently_verified,false);
 assert.equal(d.ranking_eligible_count,0);
 assert.equal(d.financial_feed_modified,false);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.equal(c.full_sgx_listing_completeness_verified,false);
 const expected=[
 ["AEM HOLDINGS LTD","POTENTIAL_EQUITY","AWX","SGD","XWA","USD"],
 ["UOB APAC Green REIT ETF","ETF","GRN","SGD","GRE","USD"],
 ["NIKKOAM-STC CHINA EV ETF","ETF","EVS","SGD","EVD","USD"]
 ];
 assert.equal(d.groups.length,expected.length);
 const codes=new Set(),matched=[];
 d.groups.forEach((g,i)=>{
  const e=expected[i];
  assert.equal(g.underlying_display,e[0]);
  assert.equal(g.category,e[1]);
  assert.equal(g.may_count_as_two_issuers,false);
  assert.equal(g.counter_pair.length,2);
  for(let j=0;j<2;j++){
   const x=g.counter_pair[j];
   assert.deepEqual([x.code,x.currency,x.is_primary],[e[2+j*2],e[3+j*2],j===0]);
   assert.ok(!codes.has(x.code));codes.add(x.code);
   assert.ok(typeof x.trading_name==="string"&&x.trading_name.length>3);
   if(c.candidates.some(r=>r.symbol===x.code))matched.push(x.code);
  }
 });
 assert.deepEqual([...codes].sort(),["AWX","EVD","EVS","GRE","GRN","XWA"]);
 assert.deepEqual(matched,["AWX"]);
 assert.equal(d.groups.filter(x=>x.category==="POTENTIAL_EQUITY").length,1);
 assert.equal(d.groups.filter(x=>x.category==="ETF").length,2);
 assert.ok(!f.records.some(r=>codes.has(r.symbol)));
 return {observed_security_counters:codes.size,official_sample_groups:d.groups.length,
  found_in_third_party:matched,unmatched_to_third_party:codes.size-matched.length,
  independently_verified_issuer_count:0,ranking_eligible_count:0};
}
const result=validate(doc,candidates,feed);
for(const m of [
 (d,c,f)=>{d.complete_sgx_list=true},
 (d,c,f)=>{d.groups[0].counter_pair[1].code="AWX"},
 (d,c,f)=>{d.groups[1].category="POTENTIAL_EQUITY"},
 (d,c,f)=>{d.groups[0].may_count_as_two_issuers=true},
 (d,c,f)=>{d.issuer_entity_id_independently_verified=true},
 (d,c,f)=>{d.groups[0].counter_pair[1].currency="SGD"},
 (d,c,f)=>{f.ranking_eligible_count=1}
]){
 const d=structuredClone(doc),c=structuredClone(candidates),f=structuredClone(feed);
 m(d,c,f);assert.throws(()=>validate(d,c,f));
}
console.log("v220 PASS: official 3 multi-currency instrument groups represent 6 counters, only AWX appears in third-party 182 and zero issuers are independently verified");
