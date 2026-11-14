"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),child=require("node:child_process");
const {derive}=require("../scripts/reconcile-sgx-official-code-v254.js");
const input=["docs/data/sgx-corporate-indexed-page-v253.json",
 "docs/data/sgx-official-batch-seed-v196.json","docs/data/latest.json"]
 .map(x=>JSON.parse(fs.readFileSync(x,"utf8")));
function check(args){
 const out=derive(...args);
 assert.equal(out.linked_issuer_count,1);
 assert.equal(out.unlinked_issuer_count,19);
 assert.equal(out.inferred_missing_codes,0);
 assert.deepEqual(out.matches.map(x=>[x.indexed_company_name,x.code,x.currency_from_official_code_source]),
  [["OVERSEA-CHINESE BANKING CORP","O39","SGD"]]);
 assert.equal(out.matches[0].issuer_code_on_official_static_page,true);
 assert.equal(out.matches[0].indexed_page_direct_html_authenticated,false);
 assert.equal(out.matches[0].current_listing_independently_rechecked,false);
 assert.equal(out.full_security_master_verified,false);
 assert.equal(out.licensed_price_feed_verified,false);
 assert.equal(out.ranking_eligible_count,0);
 return out;
}
check(input);
for(const mutate of [
 a=>{a[0].records[14].issuer_name="OVERSEA-CHINESE BANKING CORPORATION LIMITED"},
 a=>{a[0].records[14].trading_code="O39"},
 a=>{a[0].records[14].trading_currency="SGD"},
 a=>{a[0].records[14].listing_board="CATALIST"},
 a=>{a[0].records.push(structuredClone(a[0].records[14]))},
 a=>{a[0].source_page_direct_html_verified=true},
 a=>{a[1].rows.find(x=>x.symbol==="O39").name="OCBC Bank"},
 a=>{a[1].rows.find(x=>x.symbol==="O39").symbol="O38"},
 a=>{a[1].rows.find(x=>x.symbol==="O39").eligible_for_valuation=true},
 a=>{a[1].rows.find(x=>x.symbol==="O39").trading_currency="USD"},
 a=>{a[1].official_full_security_master_obtained=true},
 a=>{a[2].ranking_eligible_count=1}
]){
 const args=input.map(x=>structuredClone(x));mutate(args);assert.throws(()=>check(args));
}
const proc=child.spawnSync(process.execPath,["scripts/reconcile-sgx-official-code-v254.js"],{encoding:"utf8",timeout:30000});
assert.equal(proc.status,0,proc.stderr);
const saved=JSON.parse(fs.readFileSync("build/research/sgx-indexed-to-official-code-v254.json","utf8"));
assert.deepEqual(saved,check(input));
console.log("v254 PASS: real CLI links only source-backed OCBC code; 19 indexed issuers stay uncoded and unranked");
