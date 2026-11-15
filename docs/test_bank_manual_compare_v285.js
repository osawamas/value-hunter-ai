"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {compareManual}=require("./bank-manual-compare-v285.js");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const entries=["D05","O39","U11"].map((symbol,i)=>({
 symbol,price:String(35+i*5),shares:String(1800000000+i*100000000),
 priceAsOf:"2026-11-13",sharesAsOf:"2026-11-13"
}));
const r=compareManual(feed,entries);
assert.equal(r.rows.length,3);
assert.deepEqual(new Set(r.rows.map(x=>x.symbol)),new Set(["D05","O39","U11"]));
assert.deepEqual(r.rows.map(x=>x.illustrativePBR),r.rows.map(x=>x.illustrativePBR).slice().sort((a,b)=>a-b));
assert.equal(r.crossCompanyDateMismatch,false);
assert.equal(r.rankedInvestmentRecommendation,false);
assert.equal(r.licensedMarketQuotesAvailable,false);
assert.equal(r.independentFinancialEvidenceComplete,false);
assert.equal(r.comparisonIsIllustrativeOnly,true);
for(const row of r.rows){
 assert.equal(row.rankingEligible,false);
 assert.equal(row.quoteSelfDeclared,true);
 assert.equal(row.sharesBasisSelfDeclared,true);
 assert.match(row.issuerSource,/^https:\/\//);
 assert.match(row.issuerSourceSHA256,/^[a-f0-9]{64}$/);
 assert.ok(row.illustrativePER>0);
 assert.ok(row.illustrativePBR>0);
}
const mismatch=entries.map(x=>({...x}));
mismatch[2].sharesAsOf="2026-11-12";
assert.equal(compareManual(feed,mismatch).crossCompanyDateMismatch,true);
for(const mutant of [
 e=>{e.pop()},
 e=>{e[0].symbol="O39"},
 e=>{e[0].symbol="FAKE"},
 e=>{e[0].price="0"},
 e=>{e[2].priceAsOf="2026-02-30"},
 e=>{e[1].shares="1.5"}
]){
 const copy=entries.map(x=>({...x}));mutant(copy);
 assert.throws(()=>compareManual(feed,copy));
}
const changed=structuredClone(feed);changed.ranking_eligible_count=1;
assert.throws(()=>compareManual(changed,entries));
const html=fs.readFileSync("docs/index.html","utf8");
for(const name of ["manualBankCompareForm","manualBankCompareStatus","manualBankCompareResults"])assert.ok(html.includes('id="'+name+'"'));
for(const sym of ["D05","O39","U11"])
 for(const key of ["price","shares","priceDate","sharesDate"])
  assert.ok(html.includes('name="'+key+sym+'"'));
assert.match(html,/bank-manual-compare-v285\.js/);
const core=fs.readFileSync("docs/bank-scenario-v277.js","utf8");
assert.match(core,/VALUE_HUNTER_MANUAL_BANK_CALCULATE=calculate/);
console.log("v285 PASS: local three-bank scenario comparison source-consistent, date mismatch checked, PBR sorted, never official ranking");
