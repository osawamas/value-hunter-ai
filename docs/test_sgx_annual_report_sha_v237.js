"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const data=JSON.parse(fs.readFileSync("docs/data/sgx-annual-report-sha-v237.json","utf8"));
const results=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function check(d,r,h,v,f){
 assert.equal(d.schema_version,"sgx-h02-v03-annual-original-pdf-sha-v237");
 assert.equal(d.github_run_id,43609080946);
 assert.equal(d.github_artifact_id,14119453583);
 assert.equal(d.both_annual_report_pdf_byte_hashes_verified,true);
 assert.equal(d.original_pdf_bytes_not_published,true);
 assert.equal(d.two_documents_per_issuer_are_from_same_issuer_not_independent_audit,true);
 assert.equal(d.annual_financial_tables_not_yet_reextracted,true);
 assert.equal(d.external_independent_numeric_verification_complete,false);
 assert.equal(d.financial_feed_modified,false);assert.equal(d.ranking_eligible_count,0);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.equal(d.records.length,2);assert.equal(r.records.length,2);
 const expected={
  H02:{source:h.separate_issuer_annual_pdf,
   sha:"75328b273799863390e35a626e8e3679fe79ab853ef0a00f2775dd159364cfb8",bytes:4754838},
  V03:{source:v.other_issuer_annual_report_url,
   sha:"eaebb6f4192ceb478c819b991eb18a3c34e43bf573388b9098b5e48b73b26a97",bytes:8502570}
 };
 for(const symbol of ["H02","V03"]){
  const items=d.records.filter(z=>z.symbol===symbol),original=r.records.filter(z=>z.symbol===symbol);
  assert.equal(items.length,1);assert.equal(original.length,1);
  const x=items[0],e=expected[symbol];
  assert.equal(x.source_url,e.source);
  assert.equal(x.sha256,e.sha);
  assert.match(x.sha256,/^[a-f0-9]{64}$/);
  assert.equal(x.bytes,e.bytes);
  assert.notEqual(x.sha256,original[0].sha256,"FY report and annual report are distinct original PDFs");
  assert.equal(x.source_report_retrieved_and_hashed,true);
  assert.equal(x.issuer_numerical_audit_independently_verified,false);
  assert.equal(x.ranking_eligible,false);
  assert.ok(!f.records.some(y=>y.symbol===symbol));
 }
 return true;
}
check(data,results,h02,v03,feed);
for(const edit of [
 (d,r,h,v,f)=>{d.records[0].sha256="f".repeat(64)},
 (d,r,h,v,f)=>{d.records[1].bytes++},
 (d,r,h,v,f)=>{d.records[1].source_url="https://example.com/mirror"},
 (d,r,h,v,f)=>{d.annual_financial_tables_not_yet_reextracted=false},
 (d,r,h,v,f)=>{d.external_independent_numeric_verification_complete=true},
 (d,r,h,v,f)=>{d.records[0].ranking_eligible=true},
 (d,r,h,v,f)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(data),b=structuredClone(results),c=structuredClone(h02),
  d=structuredClone(v03),e=structuredClone(feed);
 edit(a,b,c,d,e);assert.throws(()=>check(a,b,c,d,e));
}
console.log("v237 PASS: H02/V03 separately hashed annual PDFs are matched to official SGX sources and not misconstrued as external audits");
