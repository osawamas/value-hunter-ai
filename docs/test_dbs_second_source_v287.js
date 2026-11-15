"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {verify}=require("./dbs-second-source-v287.js");
const load=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const evidence=load("docs/data/dbs-issuer-newsroom-3q26-v287.json");
const sgx=load("docs/data/sgx-big3-bank-research-v186.json");
const feed=load("docs/data/latest.json");
const result=verify(evidence,sgx,feed);
assert.equal(result.q3,2813);
assert.equal(result.nine,8822);
assert.equal(result.rounded3q,2.81);
assert.equal(result.rounded9m,8.82);
assert.equal(result.independentAudit,false);
assert.equal(result.rankingEligible,false);
assert.equal(result.sha,"3f287a5dc29a61a44fcc1c8f635bd085544bd9dd69d8ad59f23ea170c1369e7d");
for(const alter of [
 a=>{a[0].issuer_html_bytes=7},
 a=>{a[0].issuer_html_sha256="0".repeat(64)},
 a=>{a[0].source_text_identity_date_profit_checks_passed=false},
 a=>{a[0].profit_3q_sgx_millions=3000},
 a=>{a[0].issuer_website_q3_rounded_billions=3.3},
 a=>{a[0].issuer_website_nine_month_rounded_billions=10},
 a=>{a[0].independent_financial_audit_complete=true},
 a=>{a[0].current_ex_treasury_shares_verified=true},
 a=>{a[0].rank_eligible=true},
 a=>{a[1].entries[0].sha="0".repeat(64)},
 a=>{a[1].ranking_eligible=true},
 a=>{a[2].ranking_eligible_count=1}
]){
 const args=[evidence,sgx,feed].map(x=>structuredClone(x));
 alter(args);assert.throws(()=>verify(...args));
}
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["dbsSecondarySourceRows","dbsSecondarySourceStatus","dbsSecondaryIssuerLink","dbsSecondarySgxLink"])
 assert.ok(html.includes('id="'+id+'"'));
assert.match(html,/dbs-second-source-v287\.js/);
console.log("v287 PASS: official DBS 154KB newsroom HTML SHA pinned and 3Q/9M profit rounded source checks; ranking remains 0");
