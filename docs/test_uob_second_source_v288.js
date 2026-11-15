"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {verify}=require("./uob-second-source-v288.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const src=read("docs/data/uob-issuer-pdf-q3-2026-v288.json");
const bank=read("docs/data/sgx-big3-bank-research-v186.json");
const feed=read("docs/data/latest.json");
const r=verify(src,bank,feed);
assert.deepEqual(r.values.map(v=>v[1]),[1250,4165,2278,6900]);
assert.equal(r.independentAudited,false);
assert.equal(r.rankingEligible,false);
assert.equal(r.hash,"69d0a461f740beb8eea8605c19e5e0e44f6469a4be630287b87ffb035ea89ff5");
for(const mutate of [
 x=>{x[0].issuer_pdf_sha256="0".repeat(64)},
 x=>{x[0].issuer_pdf_size_bytes=1},
 x=>{x[0].issuer_pdf_explicit_table_match=false},
 x=>{x[0].current_share_count_verified=true},
 x=>{x[0].rank_eligible=true},
 x=>{x[0].independent_financial_audit_complete=true},
 x=>{x[0].checked_values_sgd_millions.third_quarter_profit++},
 x=>{x[0].checked_values_sgd_millions.nine_month_net_interest_income++},
 x=>{x[1].entries[2].sha="0".repeat(64)},
 x=>{x[2].ranking_eligible_count=1}
]){
 const copies=[src,bank,feed].map(x=>structuredClone(x));
 mutate(copies);assert.throws(()=>verify(...copies));
}
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["uobSecondaryIssuerStatus","uobSecondaryIssuerRows","uobSecondaryIssuerPdf","uobSecondarySgxPdf"])
 assert.ok(html.includes('id="'+id+'"'));
assert.match(html,/uob-second-source-v288\.js/);
assert.match(html,/独立監査や現在の株式数/);
console.log("v288 PASS: 334KB source original UOB PDF SHA and 4 exact 3Q/9M profit/NII labels, no independent audit/ranking");
