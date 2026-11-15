"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {check}=require("./ocbc-second-source-v286.js");
const load=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const evidence=load("docs/data/ocbc-3q26-issuer-website-corroboration-v286.json");
const bank=load("docs/data/sgx-big3-bank-research-v186.json");
const feed=load("docs/data/latest.json");
const verified=check(evidence,bank,feed);
assert.equal(verified.metrics.length,4);
assert.equal(verified.independentAudit,false);
assert.equal(verified.currentPrices,false);
assert.equal(verified.rankingEligible,false);
assert.equal(verified.websiteSHA,"feab3106bff1f5e769dec67fff50a9d5a28818c0aaae42b87663a622f2629370");
assert.equal(verified.metrics.find(x=>x.metric==="3Q26 net profit").sgx_precision_millions,2042);
assert.equal(verified.metrics.find(x=>x.metric==="9M26 net profit").sgx_precision_millions,6237);
for(const change of [
 x=>{x[0].website_html_sha256="0".repeat(64)},
 x=>{x[0].website_html_bytes=10},
 x=>{x[0].source_checks_passed=false},
 x=>{x[0].independent_third_party_audit_complete=true},
 x=>{x[0].share_count_current_verified=true},
 x=>{x[0].metric_checks[0].sgx_precision_millions=2050},
 x=>{x[0].metric_checks[0].issuer_website_rounded_billions=2.06},
 x=>{x[0].metric_checks[2].metric="3Q26 net profit"},
 x=>{x[1].entries[1].sha="0".repeat(64)},
 x=>{x[1].period_end="2026-06-30"},
 x=>{x[2].ranking_eligible_count=1}
]){
 const args=[evidence,bank,feed].map(x=>structuredClone(x));
 change(args);assert.throws(()=>check(...args));
}
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["ocbcSecondIssuerSourceRows","ocbcSecondIssuerSourceStatus","ocbcSecondIssuerWeb","ocbcSecondIssuerSgx"])
 assert.ok(html.includes('id="'+id+'"'));
assert.match(html,/ocbc-second-source-v286\.js/);
assert.match(html,/独立監査ではなく/);
console.log("v286 PASS: 4 issuer-owned OCBC FY2026 rounded values cross-checked, raw SHA pinned, no audit/current quote/ranking");
