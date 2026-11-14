"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const html=fs.readFileSync("docs/index.html","utf8");
const css=fs.readFileSync("docs/style.css","utf8");
const start=html.indexOf('<details class="ocbc-research-group" id="ocbcResearchGroup">');
const end=html.indexOf('</details>',start);
const next=html.indexOf('<section class="workspace" aria-labelledby="shareDateTitle">');
assert.ok(start>=0&&end>start&&next>end,"OCBC grouping must close before independent source dates");
const grouped=html.slice(start,end);
const sections=[
 "ocbcQuarterTitle","ocbcBankRatiosTitle","ocbcExactProfitTitle",
 "ocbcIncomeTitle","ocbcAllowanceTitle","ocbcBalanceTitle"
];
const rows=[
 "ocbcQuarterRows","ocbcBankRatioRows","ocbcExactProfitRows",
 "ocbcIncomeRows","ocbcAllowanceRows","ocbcBalanceRows"
];
for(const item of sections)assert.equal((grouped.match(new RegExp('aria-labelledby="'+item+'"','g'))||[]).length,1,"missing evidence panel "+item);
for(const id of rows)assert.equal((grouped.match(new RegExp('id="'+id+'"','g'))||[]).length,1,"missing row target "+id);
assert.ok(grouped.includes("独立数値検証は未完"));
assert.ok(grouped.includes("OCBC（O39）"));
assert.ok(html.indexOf('id="shareDateRows"')>end);
assert.ok(css.includes(".ocbc-group-summary:focus-visible"),"accordion should be keyboard focus-visible");
assert.ok(css.includes(".ocbc-group-panels>.workspace"),"nested workspace spacing");
assert.equal((html.match(/id="ocbcResearchGroup"/g)||[]).length,1);
console.log("v165 six OCBC source panels grouped with IDs retained and separate share date visible");
