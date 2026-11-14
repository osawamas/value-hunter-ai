"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),child=require("node:child_process");
const {integrate}=require("../scripts/integrate-sgx-twenty-v256.js");
const {derive:deriveOld}=require("../scripts/reconcile-sgx-official-code-v254.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const indexed=read("docs/data/sgx-corporate-indexed-page-v253.json");
const previous=read("docs/data/sgx-official-issuer-code-filings-v255.json");
const additional=read("docs/data/sgx-net-eleven-codes-v256.json");
const feed=read("docs/data/latest.json");
const old=deriveOld(indexed,read("docs/data/sgx-official-batch-seed-v196.json"),feed);
function assertResult(a){
 const result=integrate(...a);
 assert.equal(result.count_indexed_companies,20);
 assert.equal(result.distinct_dated_trading_codes,20);
 assert.equal(result.issuer_codes_from_announcement_index,19);
 assert.equal(result.issuer_codes_from_static_sgx_table,1);
 assert.equal(result.records.length,20);
 assert.equal(new Set(result.records.map(x=>x.code)).size,20);
 assert.deepEqual(result.records.map(x=>x.code),[
 "579","43A","HQU","KUX","5CF","VC2","5ML","5SY","O08","OTS",
 "5WA","LJ3","TS0U","AJ2","O39","RQ1","5UX","TVV","P11","P15"
 ]);
 assert.equal(result.official_complete_sgx_security_master,false);
 assert.equal(result.direct_original_html_bytes_retrieved_for_all,false);
 assert.equal(result.all_current_sgx_issuers_or_counters_present,false);
 assert.equal(result.full_quote_and_redistribution_licence,false);
 assert.equal(result.ranking_eligible_count,0);
 assert.ok(result.records.every(x=>x.current_listing_verified===false&&x.ranking_eligible===false));
}
const base=[indexed,previous,additional,old,feed];
assertResult(base);
for(const mutate of [
 a=>{a[2].records[0].code="XXX"},
 a=>{a[2].records[0].isin="FAKE"},
 a=>{a[2].records[0].source_url="https://fake.test/f"},
 a=>{a[2].records[0].identity_observed_in_sgxnet_filing=false},
 a=>{a[2].records[0].current_listing_verified=true},
 a=>{a[2].records[0].ranking_eligible=true},
 a=>{a[2].records[1].code=a[2].records[0].code},
 a=>{a[2].records[1].issuer_name=a[2].records[0].issuer_name},
 a=>{a[2].all_current_listing_status_verified=true},
 a=>{a[0].records[0].trading_code="579"},
 a=>{a[1].records[0].ranking_eligible=true},
 a=>{a[3].matches[0].code="O38"},
 a=>{a[4].ranking_eligible_count=1}
]){
 const x=base.map(v=>structuredClone(v));mutate(x);
 assert.throws(()=>integrate(...x));
}
const run=child.spawnSync(process.execPath,["scripts/integrate-sgx-twenty-v256.js"],{encoding:"utf8",timeout:30000});
assert.equal(run.status,0,run.stderr);
const actual=read("build/research/sgx-twenty-codes-v256.json");
assert.deepEqual(actual,integrate(...base));
console.log("v256 PASS: 20/20 indexed page issuer codes linked by SGX source identifiers, without inventing live listing or ranking");
