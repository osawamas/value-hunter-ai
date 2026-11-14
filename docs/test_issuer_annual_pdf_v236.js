"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {TARGETS,collect}=require("../scripts/probe-issuer-annual-pdf-v236.js");
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
assert.equal(TARGETS.length,2);
assert.equal(TARGETS[0].url,h02.separate_issuer_annual_pdf);
assert.equal(TARGETS[1].url,v03.other_issuer_annual_report_url);
assert.ok(TARGETS.every(t=>t.source_kind==="FY2025_ISSUER_ANNUAL_REPORT"));
(async()=>{
 let called=0;
 const fixture=async url=>{
  called++;
  assert.ok(TARGETS.some(x=>x.url===url));
  return {digest:{sha256:(called===1?"a":"b").repeat(64),bytes:1000+called},
   fetched_final_url:url};
 };
 const ok=await collect(fixture,"2026-11-14T15:20:00.000Z");
 assert.equal(called,2);
 assert.equal(ok.all_original_bytes_hashed,true);
 assert.equal(ok.records.length,2);
 assert.deepEqual(ok.records.map(x=>x.symbol),["H02","V03"]);
 assert.deepEqual(ok.records.map(x=>x.bytes),[1001,1002]);
 assert.equal(ok.external_independent_financial_audit_completed,false);
 assert.equal(ok.financial_feed_modified,false);
 assert.equal(ok.ranking_eligible_count,0);
 assert.ok(ok.records.every(r=>r.annual_report_raw_bytes_hashed===true));
 assert.ok(ok.records.every(r=>r.accounting_table_values_crosschecked_in_this_run===false));
 assert.ok(ok.records.every(r=>!r.ranking_eligible));
 const fail=await collect(async url=>{
  if(url===TARGETS[0].url)throw Error("403 from SGX");
  return {digest:{sha256:"f".repeat(64),bytes:999},fetched_final_url:url};
 });
 assert.equal(fail.all_original_bytes_hashed,false);
 assert.equal(fail.records[0].sha256,null);
 assert.match(fail.records[0].reason,/403/);
 assert.equal(fail.records[1].sha256,"f".repeat(64));
 const unsafe=await collect(async url=>({digest:{sha256:"f".repeat(64),bytes:999},
  fetched_final_url:"https://example.com/pdf"}));
 assert.equal(unsafe.all_original_bytes_hashed,false);
 assert.ok(unsafe.records.every(x=>!x.annual_report_raw_bytes_hashed));
 console.log("v236 PASS: optional H02/V03 annual report hashing is separately tracked, fail-closed and never an external audit");
})().catch(err=>{console.error(err);process.exitCode=1});
