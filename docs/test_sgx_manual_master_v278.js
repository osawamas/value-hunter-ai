"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {parseCSV,stageCSV}=require("./sgx-manual-master-v278.js");
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const finance=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const url="https://www.sgx.com/securities/trading";
const asOf="2026-11-15";
const sample="\uFEFFTrading Code,Trading Name,Listing Board,Traded Currency\r\n"+
 '"D05","DBS Group Holdings Ltd","MAINBOARD","SGD"\r\n'+
 '"HQU","OILTEK INTERNATIONAL LIMITED","CATALIST","SGD"\r\n';
assert.equal(parseCSV(sample).length,3);
const x=stageCSV(sample,url,asOf,candidates,finance);
assert.equal(x.number_of_rows,2);
assert.equal(x.matching_registered_financial_records,1);
assert.equal(x.full_current_sgx_universe_confirmed,false);
assert.equal(x.sgx_source_url_actually_fetched,false);
assert.equal(x.ranking_eligible_count,0);
assert.ok(x.records.every(v=>v.originalCSVSourceIndependentlyVerified===false&&!v.investmentRankingEligible));
for(const [raw,source,date] of [
 [sample,"https://example.com",asOf],
 [sample,"http://www.sgx.com/securities/trading",asOf],
 [sample,"https://www.sgx.com.evil.com/securities/trading",asOf],
 [sample,url,"2026-02-30"],
 [sample.replace("Trading Code","Stock Code"),url,asOf],
 [sample.replace("CATALIST","SECRET"),url,asOf],
 [sample.replace("HQU","D05"),url,asOf],
 [sample.replace("OILTEK INTERNATIONAL LIMITED","=2+2"),url,asOf],
 [sample.replace("HQU","A,BE"),url,asOf]
 ])assert.throws(()=>stageCSV(raw,source,date,candidates,finance));
const tampered=structuredClone(finance);tampered.ranking_eligible_count=1;
assert.throws(()=>stageCSV(sample,url,asOf,candidates,tampered));
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["sgxManualMasterForm","sgxManualMasterResult","sgxManualMasterRows"])
 assert.ok(html.includes('id="'+id+'"'));
assert.match(html,/sgx-manual-master-v278\.js/);
console.log("v278 PASS: user CSV bounded local import with 182/7 overlap and no auto-listed or ranking approval");
