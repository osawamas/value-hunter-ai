"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {calculate,getBank,isDate}=require("./bank-scenario-v277.js");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const expected={D05:[10933,68867],O39:[7422,61768],U11:[4682,51248]};
for(const [symbol,values] of Object.entries(expected)){
 const bank=getBank(feed,symbol);
 assert.ok(bank,symbol+" missing verified issuer source");
 assert.deepEqual([bank.parentProfitMillion,bank.parentEquityMillion],values);
 assert.equal(bank.independentlyVerified,false);
 const input={symbol,price:"40.50",shares:"1800000000",priceAsOf:"2026-11-13",
   sharesAsOf:"2026-11-13",priceSource:"USER_MANUALLY_ENTERED_NOT_RELICENSED",
   sharesBasis:"ISSUED_EXCLUDING_TREASURY_USER_DECLARED"};
 const result=calculate(feed,input);
 const expectedCapital=40.5*1800000000;
 assert.equal(result.marketCapSgd,expectedCapital);
 assert.ok(Math.abs(result.referencePER-expectedCapital/(values[0]*1e6))<1e-10);
 assert.ok(Math.abs(result.referencePBR-expectedCapital/(values[1]*1e6))<1e-10);
 assert.equal(result.timeMismatch,false);
 assert.equal(result.rankingEligible,false);
 assert.equal(result.quoteLicensingVerified,false);
 assert.equal(result.financialIndependentlyVerified,false);
 const mismatch=calculate(feed,{...input,sharesAsOf:"2026-11-12"});
 assert.equal(mismatch.timeMismatch,true);
 assert.ok(mismatch.warnings.some(w=>w.includes("時点不一致")));
 for(const change of [
   {price:"-1"},{price:"1e9"},{price:"0"},{shares:"123.4"},
   {shares:"0"},{shares:"9999999999999999"},{priceAsOf:"2026-02-30"},
   {sharesAsOf:"2026-13-10"},{priceSource:"SGX_LIVE_VERIFIED"},
   {sharesBasis:"UNADJUSTED_ISSUED"},{symbol:"FAKE"}
 ]){
  assert.throws(()=>calculate(feed,{...input,...change}));
 }
}
assert.equal(getBank(feed,"S68"),null);
assert.equal(isDate("2026-11-15"),true);
assert.equal(isDate("2026-02-29"),false);
assert.equal(isDate("invalid"),false);
assert.equal(feed.ranking_eligible_count,0);
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["scenarioBankForm","scenarioBankSymbol","scenarioBankStatus","scenarioBankResult"])
 assert.ok(html.includes('id="'+id+'"'));
assert.match(html,/src="\.\/bank-scenario-v277\.js"/);
assert.match(html,/入力値は端末内でのみ計算/);
console.log("v277 PASS: D05/O39/U11 FY2025 source accounting + explicit manual input what-if, stale/mismatch flags, no licensed quote or rank promotion");
