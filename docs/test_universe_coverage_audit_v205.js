"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {reconcile}=require("./universe-coverage-audit-v205.js");
const f=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const c=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const o=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
assert.ok(html.includes('src="./universe-coverage-audit-v205.js"'));
assert.ok(html.includes('id="universeCoverageAuditRows"'));
const d=reconcile(f,c,o);
assert.equal(d.financial_records,7);
assert.equal(d.third_party_candidates,182);
assert.equal(d.official_lot_batch,11);
assert.equal(d.official_in_third_party,10);
assert.deepEqual(d.official_missing_from_third_party,["K6S"]);
assert.deepEqual(d.official_missing_financials,["BN4","C07","G07","H02","J36","K6S","V03"]);
assert.deepEqual(d.official_also_financial_and_candidate,["D05","O39","S68","U11"]);
assert.equal(d.official_master_complete,false);
assert.equal(d.quote_or_valuation_permitted,false);
assert.equal(d.ranking_eligible,0);
for(const mutate of [
 (f,c,o)=>{c.candidates[0].ranking_eligible=true},
 (f,c,o)=>{o.rows[0].eligible_for_valuation=true},
 (f,c,o)=>{f.records[0].ranking_eligible=true},
 (f,c,o)=>{c.candidates.push({...c.candidates[0]})},
 (f,c,o)=>{o.official_full_security_master_obtained=true},
 (f,c,o)=>{f.ranking_eligible_count=1}
]){
 const x=structuredClone(f),y=structuredClone(c),z=structuredClone(o);mutate(x,y,z);
 assert.throws(()=>reconcile(x,y,z));
}
console.log("v205 PASS: 10/11 official batch symbols overlap third-party 182; K6S is missing without valuation promotion");
