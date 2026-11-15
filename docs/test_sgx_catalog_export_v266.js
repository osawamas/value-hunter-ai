"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {buildWithOriginalProof,search,exportDirectoryCsv}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const input=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const all=buildWithOriginalProof(...input);
const csv=exportDirectoryCsv(all);
assert.equal(csv.charCodeAt(0),0xFEFF);
assert.equal(csv.trim().split("\r\n").length,31);
assert.ok(csv.includes('"financialExclusionReasons"'));
assert.ok(csv.includes('"source"'));
assert.ok(csv.includes('"SGXNET"'));
assert.ok(csv.includes('"SGX_STATIC"'));
assert.ok(csv.includes('"O39"'));
assert.ok(!csv.includes("market_cap_sgd"));
const filtered=search(all,"","ALL","REGISTERED");
assert.equal(filtered.length,4);
const registered=exportDirectoryCsv(filtered);
assert.equal(registered.trim().split("\r\n").length,5);
assert.ok(!registered.includes('"P11"'));
const none=exportDirectoryCsv(search(all,"NONE","ALL","REGISTERED"));
assert.equal(none.trim().split("\r\n").length,1);
assert.throws(()=>exportDirectoryCsv([{...all[0],ranking_eligible:true}]));
assert.throws(()=>exportDirectoryCsv([{...all[0],financialRankingEligible:true}]));
assert.throws(()=>exportDirectoryCsv([{...all[0],all_current_trading_verified:true}]));
const injection=exportDirectoryCsv([{...all[0],name:"=2+2",warning:'say "hi"'}]);
assert.match(injection,/"'=2\+2"/);
assert.match(injection,/"say ""hi"""/);
const html=fs.readFileSync("docs/index.html","utf8");
const js=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
assert.match(html,/id="sgxHistoricalCodeExport"/);
assert.match(js,/exportBtn\.addEventListener\("click"/);
assert.match(js,/const shown=search\(items,input\.value,board\.value,financeFilter\.value\)/);
console.log("v266 PASS: filtered SGX source/financial exclusion CSV with BOM and formula injection protection");
