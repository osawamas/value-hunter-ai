"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const first=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const second=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-research-v224.json","utf8"));
const third=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-extra-v227.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
const js=fs.readFileSync("docs/official-multicurrency-v221.js","utf8");
const {validate,validateExpanded,validateAll}=require("./official-multicurrency-v221.js");
assert.equal(validate(first,candidates,feed).length,3);
assert.equal(validateExpanded(first,second,candidates,feed).length,21);
assert.ok(js.includes("./data/sgx-dual-currency-extra-v227.json"));
assert.ok(html.includes("41商品・82取引カウンター"));
assert.ok(html.includes('id="officialCurrencyPairRows"'));
const rows=validateAll(first,second,third,candidates,feed);
assert.equal(rows.length,41);
assert.equal(new Set(rows.flatMap(r=>[r.primary_code,r.secondary_code])).size,82);
assert.deepEqual(rows.filter(x=>x.primary_third_party||x.secondary_third_party)
 .map(x=>x.primary_code).sort(),["AWX","BS6","CFA","MXNU"]);
assert.equal(rows.filter(x=>x.category==="POTENTIAL_EQUITY").length,3);
assert.equal(rows.filter(x=>x.category==="BUSINESS_TRUST").length,1);
assert.equal(rows.filter(x=>x.category==="STAPLED_SECURITY").length,1);
assert.equal(rows.filter(x=>x.category==="REIT").length,2);
assert.equal(rows.filter(x=>x.category==="ETF").length,34);
assert.ok(rows.every(x=>!x.eligible_for_ranking&&!x.independently_verified_as_unique_issuer));
for(const edit of [
 (a,b,d,c,f)=>{d.pairs[0].secondary.code="AWX"},
 (a,b,d,c,f)=>{d.pairs[0].secondary.currency="SGD"},
 (a,b,d,c,f)=>{d.pairs[17].instrument_category="POTENTIAL_EQUITY"},
 (a,b,d,c,f)=>{d.not_a_complete_sgx_security_master=false},
 (a,b,d,c,f)=>{d.pairs[19].issuer_entity_identity_independently_verified=true},
 (a,b,d,c,f)=>{c.candidates.push({symbol:"ULG"})},
 (a,b,d,c,f)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(first),b=structuredClone(second),
 d=structuredClone(third),c=structuredClone(candidates),f=structuredClone(feed);
 edit(a,b,d,c,f);assert.throws(()=>validateAll(a,b,d,c,f));
}
console.log("v228 PASS: UI renders 41 official selected dual-currency products / 82 trade counters without issuer or ranking inflation");
