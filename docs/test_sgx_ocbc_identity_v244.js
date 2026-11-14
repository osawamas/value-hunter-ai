"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const identity=JSON.parse(fs.readFileSync("docs/data/sgx-ocbc-issuer-identity-v244.json","utf8"));
const actions=JSON.parse(fs.readFileSync("docs/data/sgx-bank-corporate-actions-v190.json","utf8"));
const readiness=require("../scripts/build-bank-evidence-readiness-v243.js");
const sources=[
 "docs/data/sgx-uob-official-buyback-v242.json",
 "docs/data/sgx-bank-corporate-actions-v190.json",
 "docs/data/sgx-source-rights-review-v222.json",
 "docs/data/latest.json"
].map(p=>JSON.parse(fs.readFileSync(p,"utf8")));
function verify(i,a,src){
 assert.equal(i.schema_version,"sgx-ocbc-official-issuer-identity-v244");
 assert.equal(i.source_url,"https://links.sgx.com/1.0.0/corporate-information/1943");
 assert.equal(i.issuer_name,"OVERSEA-CHINESE BANKING CORPORATION LIMITED");
 assert.equal(i.security_name,"OVERSEA-CHINESE BANKING CORP");
 assert.equal(i.symbol,"O39");
 assert.equal(i.isin,"SG1S04926220");
 assert.equal(i.listing_board,"MAINBOARD");
 assert.equal(i.company_information_source,"SGX_OFFICIAL_CORPORATE_INFORMATION");
 assert.equal(i.scope,"ISSUER_IDENTITY_ONLY_NOT_CURRENT_SHARES_OR_PRICE");
 assert.match(i.official_company_information_last_updated,/^2026-11-13T08:45:28\+08:00$/);
 for(const k of [
  "official_daily_treasury_change_notice_2026_11_12_obtained",
  "official_treasury_attachment_2026_11_12_obtained",
  "latest_issued_excluding_treasury_shares_verified",
  "complete_sgx_security_master_verified",
  "licensed_quote_available","ranking_eligible"
 ])assert.equal(i[k],false,"illegal issuer-identity promotion "+k);
 assert.equal(a.ocbc.symbol,i.symbol);
 assert.equal(a.ocbc.outstanding_change_notice.official_attachment_obtained,false);
 assert.equal(a.ocbc.outstanding_change_notice.share_change_verified,false);
 const output=readiness.derive(...src);
 assert.equal(output.source_consistency_passed,true);
 assert.equal(output.banks.find(x=>x.symbol===i.symbol).historical_ex_treasury_shares,null);
 assert.equal(output.ranking_eligible_count,0);
}
verify(identity,actions,sources);
for(const edit of [
 (i,a,s)=>{i.isin="SG1M31001969"},
 (i,a,s)=>{i.symbol="U11"},
 (i,a,s)=>{i.source_url="https://thirdparty.example"},
 (i,a,s)=>{i.latest_issued_excluding_treasury_shares_verified=true},
 (i,a,s)=>{i.official_treasury_attachment_2026_11_12_obtained=true},
 (i,a,s)=>{i.licensed_quote_available=true},
 (i,a,s)=>{i.complete_sgx_security_master_verified=true},
 (i,a,s)=>{i.ranking_eligible=true},
 (i,a,s)=>{a.ocbc.outstanding_change_notice.share_change_verified=true},
 (i,a,s)=>{s[3].ranking_eligible_count=1}
]){
 const i=structuredClone(identity),a=structuredClone(actions),s=sources.map(x=>structuredClone(x));
 edit(i,a,s);assert.throws(()=>verify(i,a,s));
}
console.log("v244 PASS: official SGX OCBC issuer identity cannot upgrade missing treasury PDF or dated shares");
