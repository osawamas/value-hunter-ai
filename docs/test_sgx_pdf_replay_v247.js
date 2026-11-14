"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const crypto=require("node:crypto");
const {expectedRows,reconcile,replay}=require("../scripts/replay-sgx-original-pdf-v247.js");
const raw=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const annual=JSON.parse(fs.readFileSync("docs/data/sgx-annual-report-sha-v237.json","utf8"));
const source=expectedRows(raw,annual);
assert.equal(source.length,4);
assert.deepEqual(source.map(x=>x.symbol+" "+x.kind),[
 "H02 FY2025_RESULTS","V03 FY2025_RESULTS","H02 FY2025_ANNUAL","V03 FY2025_ANNUAL"
]);
assert.equal(source[0].expected_bytes,706174);
assert.equal(source[1].expected_bytes,520231);
assert.equal(source[2].expected_bytes,4754838);
assert.equal(source[3].expected_bytes,8502570);
for(const row of source){
 assert.match(row.expected_sha256,/^[0-9a-f]{64}$/);
 assert.match(row.url,/^https:\/\/links\.sgx\.com\//);
}
const mock=Buffer.concat([Buffer.from("%PDF-1.7\n"),Buffer.alloc(100,32)]);
const fake={...source[0],expected_sha256:crypto.createHash("sha256").update(mock).digest("hex"),expected_bytes:mock.length};
const seen=reconcile(fake,{bytes:mock,finalUrl:fake.url});
assert.equal(seen.matched_previously_observed_sha256,true);
assert.equal(seen.independent_financial_numeric_audit,false);
assert.equal(seen.ranking_eligible,false);
for(const corrupt of [
 () => ({...fake,expected_sha256:"a".repeat(64)}),
 () => ({...fake,expected_bytes:mock.length+1}),
 () => ({...fake,expected_sha256:"invalid"})
]) assert.throws(()=>reconcile(corrupt(),{bytes:mock,finalUrl:fake.url}));
assert.throws(()=>reconcile(fake,{bytes:Buffer.from("NOT PDF"),finalUrl:fake.url}));
assert.throws(()=>reconcile(fake,{bytes:mock,finalUrl:"https://example.com/evil.pdf"}));
for(const edit of [
 (a,b)=>a.records[0].sha256="bad",
 (a,b)=>a.records.push(structuredClone(a.records[0])),
 (a,b)=>b.records[0].ranking_eligible=true,
 (a,b)=>b.records[0].bytes=0,
 (a,b)=>a.schema_version="invalid"
]){
 const a=structuredClone(raw),b=structuredClone(annual);edit(a,b);
 assert.throws(()=>expectedRows(a,b));
}
(async()=>{
 const results=await replay([fake,fake,fake,fake],async url=>({bytes:mock,finalUrl:url}));
 assert.equal(results.sources_checked,4);
 assert.equal(results.all_original_bytes_match_existing_evidence,true);
 assert.equal(results.ranking_eligible_count,0);
 assert.equal(results.independent_accounting_audit_complete,false);
 assert.equal(results.quote_rights_verified,false);
 assert.equal(results.records.every(x=>x.ranking_eligible===false),true);
 await assert.rejects(()=>replay([fake],async url=>({bytes:Buffer.from("broken"),finalUrl:url})));
 console.log("v247 PASS: offline tests reject original-PDF digest, length, issuer and provenance tampering");
})().catch(e=>{console.error(e);process.exitCode=1});
