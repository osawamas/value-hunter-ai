"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const old=JSON.parse(fs.readFileSync("docs/data/sgx-official-multicurrency-subset-v220.json","utf8"));
const ext=JSON.parse(fs.readFileSync("docs/data/sgx-dual-currency-research-v224.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
const script=fs.readFileSync("docs/official-multicurrency-v221.js","utf8");
const {validate,validateExpanded}=require("./official-multicurrency-v221.js");
assert.ok(html.includes('id="officialCurrencyPairRows"'));
assert.ok(html.includes('src="./official-multicurrency-v221.js"'));
assert.ok(script.includes("./data/sgx-dual-currency-research-v224.json"));
assert.equal(validate(old,candidates,feed).length,3);
const rows=validateExpanded(old,ext,candidates,feed);
assert.equal(rows.length,21);
assert.equal(new Set(rows.flatMap(x=>[x.primary_code,x.secondary_code])).size,42);
assert.deepEqual(rows.filter(x=>x.primary_third_party||x.secondary_third_party)
 .map(x=>x.primary_code).sort(),["AWX","BS6","CFA"]);
assert.equal(rows.filter(x=>x.category==="POTENTIAL_EQUITY").length,2);
assert.equal(rows.filter(x=>x.category==="ETF").length,16);
assert.equal(rows.filter(x=>x.category==="BUSINESS_TRUST").length,1);
assert.equal(rows.filter(x=>x.category==="STAPLED_SECURITY").length,1);
assert.equal(rows.filter(x=>x.category==="REIT").length,1);
assert.ok(rows.every(x=>x.eligible_for_ranking===false));
assert.ok(rows.every(x=>x.independently_verified_as_unique_issuer===false));
for(const edit of [
 (a,b,c,d)=>{b.new_pairs[0].secondary.code="AWX"},
 (a,b,c,d)=>{b.new_pairs[1].instrument_category="POTENTIAL_EQUITY"},
 (a,b,c,d)=>{b.new_pairs[0].primary.currency="JPY"},
 (a,b,c,d)=>{b.public_redistribution_rights_verified=true},
 (a,b,c,d)=>{b.new_pairs[0].ranking_eligible=true},
 (a,b,c,d)=>{c.candidates.push({symbol:"XWA"})},
 (a,b,c,d)=>{d.ranking_eligible_count=1}
]){
 const a=structuredClone(old),b=structuredClone(ext),
 c=structuredClone(candidates),d=structuredClone(feed);
 edit(a,b,c,d);assert.throws(()=>validateExpanded(a,b,c,d));
}
console.log("v225 PASS: renderable 21 official instrument pairs / 42 trade counters, 3 third-party overlaps, no ranking promotion");
