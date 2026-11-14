"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const html=fs.readFileSync("docs/index.html","utf8");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const actions=JSON.parse(fs.readFileSync("docs/data/sgx-bank-corporate-actions-v190.json","utf8"));
const {validate}=require("./bank-share-evidence-v193.js");
assert.ok(html.includes('src="./bank-share-evidence-v193.js"'));
for(const id of ["bankShareEvidenceStatus","bankShareEvidenceRows"])assert.ok(html.includes('id="'+id+'"'));
const result=validate(feed,actions);
assert.deepEqual({symbol:result.symbol,date:result.date,count:result.count,cancelled:result.cancelled},
 {symbol:"U11",date:"2026-11-12",count:1646711591,cancelled:34000});
assert.match(result.source,/^https:\/\/links\.sgx\.com\//);
for(const makeBad of [
  (f,a)=>{f.ranking_enabled=true},
  (f,a)=>{f.records.find(x=>x.symbol==="U11").ranking_eligible=true},
  (f,a)=>{f.coverage.registered_count++},
  (f,a)=>{f.records.push(structuredClone(f.records.find(x=>x.symbol==="O39")))},
  (f,a)=>{a.uob.latest_unverified.official_verified=true},
  (f,a)=>{a.ocbc.outstanding_change_notice.official_attachment_obtained=true},
  (f,a)=>{a.uob.observations[1].issued_excluding_treasury_after++},
  (f,a)=>{a.uob.observations[1].announcement_reference="INVALID"},
  (f,a)=>{a.uob.observations[0].purchased++},
  (f,a)=>{a.uob.observations[0].origin="THIRD_PARTY"},
  (f,a)=>{a.source_policy.licensed_timestamped_quotation_available=true}
]){
 const f=structuredClone(feed),a=structuredClone(actions);
 makeBad(f,a);assert.throws(()=>validate(f,a));
}
console.log("v193 PASS: dated shares UI and incomplete SGX original evidence blocked from valuations");
