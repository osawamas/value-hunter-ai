"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validateSupplemental}=require("./bank-share-evidence-v193.js");
const files=["docs/data/latest.json","docs/data/sgx-bank-corporate-actions-v190.json",
"docs/data/sgx-uob-official-buyback-v242.json","docs/data/sgx-ocbc-issuer-identity-v244.json",
"docs/data/sgx-source-rights-review-v222.json"];
const base=files.map(p=>JSON.parse(fs.readFileSync(p,"utf8")));
function pass(args){
 const res=validateSupplemental(...args);
 assert.equal(res.uob.symbol,"U11");
 assert.equal(res.uob.date,"2026-11-12");
 assert.equal(res.uob.count,1646711591);
 assert.equal(res.ocbc.symbol,"O39");
 assert.equal(res.ocbc.isin,"SG1S04926220");
 assert.equal(res.ocbc.source_url,"https://links.sgx.com/1.0.0/corporate-information/1943");
 assert.equal(args[0].ranking_eligible_count,0);
}
pass(base);
for(const bad of [
 x=>{x[2].rows[2].issued_excluding_treasury_after_purchase++},
 x=>{x[2].rows[1].issued_excluding_treasury_after_purchase++},
 x=>{x[2].rows[2].announcement_ref="SG261113OTHRHOAF"},
 x=>{x[2].rows[2].source_url="https://thirdparty.example"},
 x=>{x[2].official_current_asof_date="2026-11-13"},
 x=>{x[2].latest_2026_11_13_official_original_retrieved=true},
 x=>{x[3].isin="INVALID"},
 x=>{x[3].source_url="https://thirdparty.example/issuer"},
 x=>{x[3].official_treasury_attachment_2026_11_12_obtained=true},
 x=>{x[3].latest_issued_excluding_treasury_shares_verified=true},
 x=>{x[4].licensed_time_stamped_quote_available=true},
 x=>{x[4].feeds[0].public_quote_redistribution_authorized=true},
 x=>{x[1].uob.observations[1].issued_excluding_treasury_after++},
 x=>{x[0].ranking_eligible_count=1}
 ]){
  const a=base.map(v=>structuredClone(v));bad(a);
  assert.throws(()=>pass(a));
}
const ui=fs.readFileSync("docs/bank-share-evidence-v193.js","utf8");
assert.match(ui,/validateSupplemental\(feed,actions,uobOriginal,ocbcIssuer,rights\)/);
assert.match(ui,/公式銘柄識別確認・SGX添付PDF未取得/);
assert.match(ui,/正規株価利用許諾なし/);
assert.match(ui,/SGX会社情報/);
console.log("v245 PASS: browser displays source-reconciled dated UOB and OCBC issuer-only proof, rejects unlicensed valuation");
