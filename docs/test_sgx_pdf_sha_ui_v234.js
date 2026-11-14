"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const proof=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
const {validate}=require("./pdf-sha-evidence-v234.js");
assert.ok(html.includes('src="./pdf-sha-evidence-v234.js"'));
assert.ok(html.includes('id="issuerPdfDigestRows"'));
assert.ok(html.includes('id="issuerPdfDigestStatus"'));
const rows=validate(proof,h02,v03,feed);
assert.equal(rows.length,2);
assert.deepEqual(rows.map(x=>[x.symbol,x.bytes]),[["H02",706174],["V03",520231]]);
assert.deepEqual(rows.map(x=>x.sha),[
 "94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5",
 "b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794"
]);
assert.ok(rows.every(x=>x.valid_original_bytes_digest===true));
assert.ok(rows.every(x=>x.independent_numeric_audit===false));
assert.ok(rows.every(x=>x.ranking_eligible===false));
for(const change of [
 (p,h,v,f)=>{p.records[0].byte_length++},
 (p,h,v,f)=>{p.records[1].sha256="a".repeat(64)},
 (p,h,v,f)=>{p.repeated_independent_download_runs[1].workflow_run_id=0},
 (p,h,v,f)=>{p.independent_second_github_actions_fetch_same_bytes=false},
 (p,h,v,f)=>{p.external_independent_numeric_audit_completed=true},
 (p,h,v,f)=>{p.records[0].licensed_timestamped_quote_verified=true},
 (p,h,v,f)=>{p.records[1].ranking_eligible=true},
 (p,h,v,f)=>{f.ranking_eligible_count=1}
]){
 const p=structuredClone(proof),h=structuredClone(h02),v=structuredClone(v03),f=structuredClone(feed);
 change(p,h,v,f);assert.throws(()=>validate(p,h,v,f));
}
console.log("v234 PASS: exact original SGX PDF SHA visible with two independent Actions runs and no false accounting audit");
