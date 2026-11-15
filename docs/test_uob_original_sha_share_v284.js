"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validateReplayedOriginal}=require("./bank-share-evidence-v193.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const file=read("docs/data/uob-original-12nov-share-count-v284.json");
const feed=read("docs/data/latest.json");
const action=read("docs/data/sgx-bank-corporate-actions-v190.json");
const chain=read("docs/data/sgx-uob-official-buyback-v242.json");
const verified=validateReplayedOriginal(file,action,chain,feed);
assert.equal(verified.date,"2026-11-12");
assert.equal(verified.count,1646711591);
assert.equal(verified.sha,"02722c970c4200e6507d60fbaa5458a2bcf43d96686f5111853bffb800e6e8e2");
assert.equal(verified.nextDayUnverified,true);
assert.equal(file.original_html_bytes,7612);
assert.equal(file.current_issued_shares_verified,false);
assert.equal(file.stock_ranking_eligible,false);
assert.equal(feed.ranking_eligible_count,0);
for(const alter of [
 x=>{x[0].original_html_sha256="0".repeat(64)},
 x=>{x[0].original_html_bytes=5},
 x=>{x[0].official_source_url="https://evil.example/bad"},
 x=>{x[0].event_date="2026-11-13"},
 x=>{x[0].shares_cancelled_on_event=1},
 x=>{x[0].current_issued_shares_verified=true},
 x=>{x[0].stock_ranking_eligible=true},
 x=>{x[0].next_day_notice_known_but_original_not_confirmed.original_sgxnet_url_verified=true},
 x=>{x[0].next_day_notice_known_but_original_not_confirmed.secondary_reports_issued_excluding_treasury_after_event++},
 x=>{x[1].uob.observations[1].issued_excluding_treasury_after++},
 x=>{x[2].rows[2].source_url="https://evil.example"}
]){
 const args=[file,action,chain,feed].map(x=>structuredClone(x));alter(args);
 assert.throws(()=>validateReplayedOriginal(...args));
}
const ui=fs.readFileSync("docs/bank-share-evidence-v193.js","utf8");
assert.match(ui,/uob-original-12nov-share-count-v284\.json/);
assert.match(ui,/UOBの11月12・13日とOCBCの11月12日のSGX原本/);
assert.match(ui,/原本SHA-256/);
console.log("v284 PASS: real UOB Nov12 raw-SGXNet SHA provenance, labelled share count and guarded unverified Nov13/latest ranking");
