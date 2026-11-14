"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validate}=require("./bank-fy-interim-bridge-v195.js");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const bank=JSON.parse(fs.readFileSync("docs/data/sgx-big3-bank-research-v186.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
assert.ok(html.includes('src="./bank-fy-interim-bridge-v195.js"'));
assert.ok(html.includes('id="bankFyBridgeRows"'));
assert.ok(html.includes('id="bankFyBridgeStatus"'));
const rows=validate(feed,bank);
assert.deepEqual(rows.map(x=>[x.symbol,x.fy2025_total_income_m_sgd,
 x.fy2025_parent_profit_m_sgd,x.q3_2026_profit_m_sgd]),[
 ["D05",22900,10933,2813],["O39",14614,7422,2042],["U11",13808,4682,1250]
]);
for(const x of rows){
 assert.match(x.fy_pdf_sha256,/^[a-f0-9]{64}$/);
 assert.match(x.q3_pdf_sha256,/^[a-f0-9]{64}$/);
 assert.equal(typeof x.fy_source_url,"string");
 assert.equal(typeof x.q3_source_url,"string");
}
for(const edit of [
 (f,b)=>{f.records.find(r=>r.symbol==="D05").bank_financial_state.banking_metrics_parsed=false},
 (f,b)=>{f.records.find(r=>r.symbol==="O39").banking_audited.income.total_income["2025"]++},
 (f,b)=>{f.records.find(r=>r.symbol==="U11").banking_interim_2026.pdf_sha256="forged"},
 (f,b)=>{f.records.find(r=>r.symbol==="D05").bank_financial_state.third_party_numerical_verification=true},
 (f,b)=>{f.records.find(r=>r.symbol==="O39").ranking_eligible=true},
 (f,b)=>{b.entries.find(r=>r.symbol==="U11").q3profit++},
 (f,b)=>{b.authentic_current_sgx_execution_quotes_verified=true}
]){
 const f=structuredClone(feed),b=structuredClone(bank);edit(f,b);
 assert.throws(()=>validate(f,b));
}
console.log("v195 PASS: bank-only audited FY2025 values and interim 3Q2026 are source-bound, period separate and not ranked");
