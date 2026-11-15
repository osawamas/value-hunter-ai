"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {stageCSV,mapHeaders,pageOf}=require("./sgx-manual-master-v278.js");
const c=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const f=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const source="https://www.sgx.com/securities/securities-prices?code=stocks";
const raw="Last,Trading Name,Trading Code,Chng\r\n"+
 "69.90,DBS Group Holdings Ltd,D05,+0.20\r\n"+
 "70.14,United Overseas Bank Limited,U11,-1.00\r\n";
const staged=stageCSV(raw,source,"2026-11-15",c,f);
assert.equal(staged.number_of_rows,2);
assert.equal(staged.matching_registered_financial_records,2);
assert.equal(staged.ignored_unmapped_input_columns,2);
assert.equal(staged.optional_listing_board_supplied,false);
assert.equal(staged.optional_traded_currency_supplied,false);
assert.equal(staged.market_prices_extracted,false);
assert.equal(staged.full_current_sgx_universe_confirmed,false);
assert.deepEqual(staged.records.map(x=>x.code),["D05","U11"]);
assert.deepEqual(staged.records.map(x=>x.board),["UNKNOWN","UNKNOWN"]);
assert.deepEqual(staged.records.map(x=>x.currency),["UNKNOWN","UNKNOWN"]);
assert.ok(staged.records.every(x=>x.investmentRankingEligible===false&&!x.activeListingConfirmed));
assert.equal(JSON.stringify(staged).includes("69.90"),false);
assert.equal(JSON.stringify(staged).includes("70.14"),false);
assert.equal(JSON.stringify(staged).includes("+0.20"),false);
assert.equal(pageOf(staged,"D05",0).matched,1);
const alias=stageCSV("Stock Code,Stock Name,Market Board,Ccy\r\nD05,DBS Group Holdings Ltd,MAIN BOARD,S$\r\n",source,"2026-11-15",c,f);
assert.equal(alias.records[0].board,"MAINBOARD");
assert.equal(alias.records[0].currency,"SGD");
assert.equal(alias.market_prices_extracted,false);
assert.equal(mapHeaders(["Trading Name","Trading Code"]).positions.code,1);
for(const bad of [
 "Trading Code,Stock Code,Trading Name\nD05,D05,DBS Group Holdings Ltd",
 "Last,Chng\n10.5,0.2",
 "Trading Code,Trading Name\nD05,DBS Group Holdings Ltd\nD05,Another Holder",
 "Trading Code,Trading Name,Last\nD05,DBS Group Holdings Ltd,9\nU11,UOB",
])assert.throws(()=>stageCSV(bad,source,"2026-11-15",c,f));
const html=fs.readFileSync("docs/index.html","utf8");
assert.match(html,/Trading Code・Trading Nameの2列が必要/);
console.log("v282 PASS: SGX-like flexible CSV headers, ignored quote columns, explicit unknown board/currency and unchanged ranking gate");
