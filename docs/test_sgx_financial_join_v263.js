"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof,search}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const src=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const rows=buildWithOriginalProof(...src);
const registered=rows.filter(r=>r.financialRegistered);
assert.equal(rows.length,30);
assert.deepEqual(registered.map(r=>r.code).sort(),["D05","O39","S68","U11"]);
assert.ok(rows.every(r=>r.financialRankingEligible===false));
assert.ok(registered.every(r=>r.financialExclusionReasons.length>0));
assert.ok(rows.filter(r=>!r.financialRegistered).every(r=>r.financialExclusionReasons.length===0));
assert.equal(search(rows,"O39","ALL")[0].financialRegistered,true);
assert.equal(search(rows,"5WA","ALL")[0].financialRegistered,false);
assert.equal(src[5].ranking_eligible_count,0);
for(const edit of [
 a=>{a[5].records[0].ranking_eligible=true},
 a=>{a[5].records[0].exclusion_reasons=[]},
 a=>{a[5].records[0].symbol="D05"},
 a=>{a[5].records.push(structuredClone(a[5].records[0]))},
 a=>{a[5].ranking_eligible_count=1}
]){const x=src.map(v=>structuredClone(v));edit(x);assert.throws(()=>buildWithOriginalProof(...x))}
const html=fs.readFileSync("docs/index.html","utf8");
const ui=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
assert.match(html,/根拠の確認状態<\/th><th>財務登録/);
assert.match(ui,/financeTd\.textContent=item\.financialRegistered/);
assert.match(ui,/financialExclusionReasons\.join/);
console.log("v263 PASS: research SGX codes joined by exact symbol to four financial records, exclusion reasons remain guarded");
