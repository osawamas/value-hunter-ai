"use strict";
const fs=require("node:fs");
const assert=require("node:assert/strict");
const html=fs.readFileSync("docs/index.html","utf8");
const app=fs.readFileSync("docs/app.js","utf8");
for(const phrase of ["参考株価","参考時価総額","参考PER","参考PBR"]){
 assert.ok(html.includes(phrase),"Historical reference label remains qualified: "+phrase);
}
const sortHtml=html.match(/<select id="sortBy"[^>]*>([\s\S]*?)<\/select>/)?.[1];
assert.ok(sortHtml,"Sorter must still be present");
for(const unsafe of ['value="market_cap_sgd"','value="per_reference"','value="pbr_reference_unverified"']){
 assert.ok(!sortHtml.includes(unsafe),"Unverified valuation sort must be removed: "+unsafe);
}
assert.ok(html.includes('src="./reference-valuation-guard-v168.js"'));
assert.ok(app.includes("referenceValuationDisplayPermitted(r)"));
for(const phrase of [
 "参考時価総額（未検証・SGD）",
 "参考PER（未検証）",
 "参考PBR（未検証）",
 "正式な評価値ではない"
])assert.ok(app.includes(phrase),"Detail must mark unverified valuation: "+phrase);
assert.ok(app.includes('r.ranking_eligible ? "対象"'));
assert.ok(html.includes("ランキング1社目に必要な検証"));
console.log("v188 preserved reference disclosures without unsafe comparative sorting");
