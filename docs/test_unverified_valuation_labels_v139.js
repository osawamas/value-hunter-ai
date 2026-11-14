"use strict";
const fs=require("node:fs");
const assert=require("node:assert/strict");
const html=fs.readFileSync("docs/index.html","utf8");
const app=fs.readFileSync("docs/app.js","utf8");
for(const phrase of ["参考株価","参考時価総額","参考PER","参考PBR",
                     "参考時価総額（未検証・大きい順）",
                     "参考PER（未検証・低い順）"]){
 assert.ok(html.includes(phrase),"Expected explicitly qualified table/sort label: "+phrase);
}
for(const phrase of [
 "参考時価総額（未検証・SGD）",
 "参考PER（未検証）",
 "参考PBR（未検証）",
 "正式な評価値ではない"
])assert.ok(app.includes(phrase),"Detail must mark unverified valuation: "+phrase);
assert.ok(app.includes('r.ranking_eligible ? "対象"'));
assert.ok(html.includes("ランキング1社目に必要な検証"));
console.log("v139 valuation reference labels are explicit and original rank gate remains");
