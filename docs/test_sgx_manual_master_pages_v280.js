"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {parseCSV,stageCSV,pageOf}=require("./sgx-manual-master-v278.js");
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const finance=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const header="Trading Code,Trading Name,Listing Board,Traded Currency";
const lines=Array.from({length:1200},(_,i)=>{
 const code=i.toString(36).toUpperCase().padStart(4,"0");
 return code+",Sample Test Counter "+i+",MAINBOARD,SGD";
});
const csv=header+"\r\n"+lines.join("\r\n")+"\r\n";
const staged=stageCSV(csv,"https://www.sgx.com/securities/trading","2026-11-15",candidates,finance);
assert.equal(staged.number_of_rows,1200);
assert.equal(staged.ranking_eligible_count,0);
const first=pageOf(staged,"",0);
assert.equal(first.records.length,50);
assert.equal(first.pageCount,24);
assert.equal(first.page,0);
assert.equal(first.hasNext,true);
assert.equal(first.hasPrevious,false);
assert.equal(first.records[0].code,"0000");
const middle=pageOf(staged,"",11);
assert.equal(middle.records.length,50);
assert.equal(middle.page,11);
assert.equal(middle.records[0].code,(550).toString(36).toUpperCase().padStart(4,"0"));
const last=pageOf(staged,"",999);
assert.equal(last.page,23);
assert.equal(last.records.length,50);
assert.equal(last.hasNext,false);
assert.equal(last.hasPrevious,true);
const found=pageOf(staged,"Sample Test Counter 1199",0);
assert.equal(found.matched,1);
assert.equal(found.records[0].code,(1199).toString(36).toUpperCase().padStart(4,"0"));
assert.equal(found.pageCount,1);
const missing=pageOf(staged,"NO_MATCH_ABC",0);
assert.equal(missing.matched,0);
assert.equal(missing.records.length,0);
assert.equal(missing.pageCount,1);
assert.equal(pageOf(staged,"",999,100).records.length,100);
for(const tamper of [
 d=>{d.ranking_eligible_count=1},
 d=>{d.full_current_sgx_universe_confirmed=true},
 d=>{d.records.pop()},
 d=>{d.sgx_source_url_actually_fetched=true}
]){
 const x=structuredClone(staged);tamper(x);
 assert.throws(()=>pageOf(x,"",0));
}
for(const n of [-1,1.5,NaN])assert.throws(()=>pageOf(staged,"",n));
for(const n of [0,101,-1])assert.throws(()=>pageOf(staged,"",0,n));
const tooBig=header+"\r\n"+Array.from({length:1201},(_,i)=>i.toString(36).toUpperCase().padStart(4,"0")+",Test "+i+",MAINBOARD,SGD").join("\r\n");
assert.throws(()=>stageCSV(tooBig,"https://www.sgx.com/securities/trading","2026-11-15",candidates,finance));
assert.ok(staged.records.every(r=>r.investmentRankingEligible===false&&!r.activeListingConfirmed));
const html=fs.readFileSync("docs/index.html","utf8");
for(const id of ["sgxManualMasterSearch","sgxManualMasterPrevious","sgxManualMasterNext","sgxManualMasterPageStatus","sgxManualMasterTemplate"])
 assert.ok(html.includes('id="'+id+'"'));
const ui=fs.readFileSync("docs/sgx-manual-master-v278.js","utf8");
assert.match(ui,/search\.addEventListener\("input"/);
assert.match(ui,/pageOf\(staged,search\.value,visiblePage\)/);
assert.match(ui,/sgx-source-template-unverified\.csv/);
assert.match(ui,/return "\\uFEFF"/);
console.log("v280 PASS: private 1200-code browse/search, 24-page navigation, boundaries, CSV template and no verified/ranking promotion");
