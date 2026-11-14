"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
const {validate}=require("./primary-issuer-reconciliation-v214.js");
function verify(f,h,v){
 assert.ok(html.includes('src="./primary-issuer-reconciliation-v214.js"'));
 assert.ok(html.includes('id="primaryIssuerReconciliationRows"'));
 assert.ok(html.includes('id="primaryIssuerReconciliationStatus"'));
 const rows=validate(f,h,v);
 assert.deepEqual(rows.map(x=>[x.symbol,x.assets,x.liabilities,x.total_equity]),[
   ["H02",4417906,126830,4291076],["V03",3602219,804386,2797833]]);
 assert.deepEqual(rows.map(x=>x.noncontrolling_equity),[null,5092]);
 assert.deepEqual(rows.map(x=>x.owner_profit),[null,226958]);
 assert.deepEqual(rows.map(x=>x.group_profit),[265462,227635]);
 assert.ok(rows.every(x=>x.source.startsWith("https://links.sgx.com/")));
 return true;
}
verify(feed,h02,v03);
for(const mutate of [
 (f,h,v)=>{h.verified_from_primary_pdf_visual.balance_FY2025.net_assets++},
 (f,h,v)=>{v.group.FY2025.noncontrolling_equity++},
 (f,h,v)=>{v.group.FY2025.profit_attributable_to_owners++},
 (f,h,v)=>{h.source_pdf_sha256="a".repeat(64)},
 (f,h,v)=>{v.independent_auditor_external_source_verified=true},
 (f,h,v)=>{f.ranking_enabled=true},
 (f,h,v)=>{f.records.push({...f.records[0],symbol:"V03"})}
]){
 const f=structuredClone(feed),h=structuredClone(h02),v=structuredClone(v03);
 mutate(f,h,v);assert.throws(()=>verify(f,h,v));
}
console.log("v214 PASS: H02/V03 exact primary statement research screen remains source-bound and does not promote valuations");
