"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {compare}=require("./bank-annual-compare-v283.js");
const base=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const banks=compare(base);
assert.deepEqual(banks.map(x=>x.code),["D05","O39","U11"]);
const expected={
 D05:{income:[22297,22900],profit:[11289,10933],equity:[68786,68867]},
 O39:{income:[14473,14614],profit:[7587,7422],equity:[59316,61768]},
 U11:{income:[14294,13808],profit:[6045,4682],equity:[49733,51248]},
};
for(const b of banks){
 const e=expected[b.code];
 assert.deepEqual([b.totalIncome2024,b.totalIncome2025],e.income);
 assert.deepEqual([b.parentProfit2024,b.parentProfit2025],e.profit);
 assert.deepEqual([b.parentEquity2024,b.parentEquity2025],e.equity);
 assert.ok(Math.abs(b.incomeGrowthPct-(e.income[1]/e.income[0]-1)*100)<1e-10);
 assert.ok(Math.abs(b.profitGrowthPct-(e.profit[1]/e.profit[0]-1)*100)<1e-10);
 assert.ok(Math.abs(b.approximateAverageEquityROEPct-
  (e.profit[1]/((e.equity[0]+e.equity[1])/2)*100))<1e-10);
 assert.match(b.source,/^https:\/\//);
 assert.match(b.pdfSHA256,/^[0-9a-f]{64}$/);
 assert.equal(b.independentSecondSourceConfirmed,false);
 assert.equal(b.investorRankingEligible,false);
 assert.equal(b.marketPriceUsed,false);
}
for(const mutate of [
 f=>{f.ranking_eligible_count=1},
 f=>{f.records.find(x=>x.symbol==="U11").ranking_eligible=true},
 f=>{f.records.find(x=>x.symbol==="O39").banking_audited.income.parent_profit["2025"]=null},
 f=>{f.records.find(x=>x.symbol==="D05").banking_evidence.pdf_sha256="FAKE"},
 f=>{f.records.find(x=>x.symbol==="U11").banking_audited.independent_cross_source_verification=true},
 f=>{f.records.find(x=>x.symbol==="D05").banking_evidence.balance["2025"].parent_shareholders_funds=99999999999}
]){
 const input=structuredClone(base);mutate(input);assert.throws(()=>compare(input));
}
const html=fs.readFileSync("docs/index.html","utf8");
assert.match(html,/id="bankAnnualCompareRows"/);
assert.match(html,/参考ROE/);
assert.match(html,/bank-annual-compare-v283\.js/);
console.log("v283 PASS: 2024/25 three-bank issuer-PDF income, parent profit, equity and simple ROE comparisons; no rank promotion");
