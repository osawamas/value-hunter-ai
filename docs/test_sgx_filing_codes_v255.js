"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),child=require("node:child_process");
const {derive}=require("../scripts/reconcile-sgx-filing-codes-v255.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const base=[read("docs/data/sgx-corporate-indexed-page-v253.json"),
 read("docs/data/sgx-official-issuer-code-filings-v255.json"),read("docs/data/latest.json")];
function verify(a){
 const r=derive(...a);
 assert.equal(r.partial_index_records,20);
 assert.equal(r.issuer_codes_from_sgxnet_filings,8);
 assert.equal(r.issuer_codes_missing_from_original_filings,12);
 assert.deepEqual(r.rows.map(x=>x.code).sort(),["579","5CF","5ML","5WA","HQU","LJ3","O08","TVV"].sort());
 assert.equal(r.current_active_listing_all_verified,false);
 assert.equal(r.official_full_master_verified,false);
 assert.equal(r.ranking_eligible_count,0);
 assert.ok(r.rows.every(x=>x.asof_dated_filing_identity_only && !x.active_current_listing_verified && !x.ranking_eligible));
}
verify(base);
for(const bad of [
 a=>{a[1].records[0].trading_code="580"},
 a=>{a[1].records[0].isin="SG1234567890"},
 a=>{a[1].records[0].source_url="https://evil.test/f"},
 a=>{a[1].records[0].announcement_ref="FAKE"},
 a=>{a[1].records[0].announced_on="unknown"},
 a=>{a[1].records[1].issuer_name=a[1].records[0].issuer_name},
 a=>{a[1].records[0].ranking_eligible=true},
 a=>{a[1].records[0].current_trading_quote_verified=true},
 a=>{a[1].all_codes_currently_listed_verified=true},
 a=>{a[0].records[0].trading_code="579"},
 a=>{a[2].ranking_eligible_count=1}
]){const a=base.map(x=>structuredClone(x));bad(a);assert.throws(()=>verify(a))}
const p=child.spawnSync(process.execPath,["scripts/reconcile-sgx-filing-codes-v255.js"],{encoding:"utf8",timeout:30000});
assert.equal(p.status,0,p.stderr);
const written=read("build/research/sgx-direct-filing-issuer-code-v255.json");
assert.deepEqual(written,derive(...base));
console.log("v255 PASS: eight original SGXNet ISIN/issuer/counter identities matched and saved, zero current-listing promotion");
