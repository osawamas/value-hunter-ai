"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validate}=require("./fy-third-party-figure-v197.js");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const research=JSON.parse(fs.readFileSync("docs/data/sgx-independent-figure-research-v197.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
assert.ok(html.includes('src="./fy-third-party-figure-v197.js"'));
assert.ok(html.includes('id="thirdPartyFyCompareRows"'));
const rows=validate(feed,research);
assert.deepEqual(rows.map(x=>x.symbol),["G13","S63"]);
assert.deepEqual(rows.map(x=>x.profit_m_sgd),[390.346,462.77]);
assert.ok(research.independent_audit_requirement_satisfied===false);
for(const edit of [
 (f,r)=>{f.records.find(x=>x.symbol==="G13").attributable_profit_sgd_thousands++},
 (f,r)=>{r.records.find(x=>x.symbol==="S63").external_revenue_millions++},
 (f,r)=>{r.records.find(x=>x.symbol==="G13").operating_income_comparable=true},
 (f,r)=>{r.independent_audit_requirement_satisfied=true},
 (f,r)=>{r.records.find(x=>x.symbol==="G13").may_promote_to_ranking=true},
 (f,r)=>{f.ranking_eligible_count=1},
 (f,r)=>{r.records.find(x=>x.symbol==="S63").external_operating_income_millions=843.116}
]){
 const f=structuredClone(feed),r=structuredClone(research);edit(f,r);
 assert.throws(()=>validate(f,r));
}
console.log("v197 PASS: G13/S63 third-party rounded matches do not certify independent audit or operating-income equivalence");
