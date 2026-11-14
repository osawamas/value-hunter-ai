"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
const seed=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const {validate}=require("./official-batch-v196.js");
assert.ok(html.includes('src="./official-batch-v196.js"'));
assert.ok(html.includes('id="officialSeedRows"'));
assert.ok(html.includes('id="officialSeedStatus"'));
const rows=validate(seed,feed);
assert.equal(rows.length,11);
assert.deepEqual(rows.filter(r=>r.registered_financial_record).map(r=>r.symbol),["D05","O39","S68","U11"]);
assert.deepEqual(rows.filter(r=>r.currency==="USD").map(r=>r.symbol),["J36","K6S"]);
assert.equal(seed.official_full_security_master_obtained,false);
assert.equal(seed.quote_fields_excluded,true);
for(const edit of [
 (s,f)=>{s.source_is_full_security_master=true},
 (s,f)=>{s.rows[0].board_lot_shares=100},
 (s,f)=>{s.rows.push({...s.rows[0]})},
 (s,f)=>{s.rows.find(r=>r.symbol==="J36").trading_currency="SGD"},
 (s,f)=>{s.rows[0].eligible_for_valuation=true},
 (s,f)=>{f.ranking_eligible_count=1},
 (s,f)=>{s.quote_usage_or_redistribution_license_verified=true}
]){
 const s=structuredClone(seed),f=structuredClone(feed);edit(s,f);assert.throws(()=>validate(s,f));
}
console.log("v196 PASS: exact eleven SGX official static lot-size seed; no false full-universe or quote permission claim");
