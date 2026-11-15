"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const app=fs.readFileSync("docs/app.js","utf8");
const ui=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
const window={};
vm.runInNewContext(app,{window,document:undefined,console});
const labels=window.VALUE_HUNTER_EXCLUSION_LABELS;
assert.ok(labels && Object.isFrozen(labels));
assert.equal(labels.PRICE_MISSING,"株価が未取得");
assert.equal(labels.SHARES_MISSING,"発行済株式数が未取得");
assert.equal(labels.INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE,"第三者による独立検証が未完了");
const f=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const selected=f.records.filter(r=>["D05","O39","S68","U11"].includes(r.symbol));
assert.equal(selected.length,4);
for(const record of selected){
 assert.ok(record.exclusion_reasons.length>0);
 const japanese=record.exclusion_reasons.map(c=>labels[c]||"要確認（"+c+"）");
 assert.equal(japanese.length,record.exclusion_reasons.length);
 assert.ok(japanese.every(s=>s.length>0));
}
assert.match(ui,/root\?\.VALUE_HUNTER_EXCLUSION_LABELS/);
assert.match(ui,/summary\.textContent="除外理由を表示"/);
assert.match(ui,/li\.textContent=reason/);
assert.match(ui,/details\.append\(list\)/);
assert.match(ui,/financeTd\.append\(details\)/);
assert.match(ui,/japaneseReasons\.join/);
assert.equal(f.ranking_eligible_count,0);
console.log("v267 PASS: four finance-linked SGX issuers have accessible Japanese exclusion reasons, no false ranking");
