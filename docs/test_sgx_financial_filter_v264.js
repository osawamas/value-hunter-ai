"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof,search}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const args=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const rows=buildWithOriginalProof(...args);
assert.deepEqual(search(rows,"","ALL","REGISTERED").map(x=>x.code).sort(),["D05","O39","S68","U11"]);
assert.equal(search(rows,"","ALL","UNREGISTERED").length,26);
assert.equal(search(rows,"","UNKNOWN","REGISTERED").length,3);
assert.equal(search(rows,"O39","MAINBOARD","REGISTERED").length,1);
assert.equal(search(rows,"O39","MAINBOARD","UNREGISTERED").length,0);
assert.equal(search(rows,"","ALL").length,30);
assert.equal(rows.filter(x=>x.financialRankingEligible).length,0);
const html=fs.readFileSync("docs/index.html","utf8");
const ui=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
for(const s of ["sgxHistoricalCodeFinance","REGISTERED","UNREGISTERED"])assert.ok(html.includes(s));
assert.match(ui,/financeFilter\.addEventListener\("change",paint\)/);
console.log("v264 PASS: financial registration and source/market filtering works together; 4 registered versus 26 uncovered");
