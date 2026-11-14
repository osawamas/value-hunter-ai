"use strict";
const assert=require("node:assert/strict");
const {csvRows,normalize,decodeOriginalCsv}=require("../scripts/stage-sgx-csv-v199.js");
const csv=[
 "Trading Code,Trading Name,Traded Currency,Listing Board,Security Type,Last,Bid,Ask,Volume",
 'D05,"DBS Group Holdings Ltd",SGD,MAINBOARD,STOCK,37.75,37.70,37.80,10000',
 'J36,"Jardine Matheson, Holdings Ltd",USD,MAINBOARD,STOCK,60.84,60.82,60.90,500',
 'O39,"OCBC Bank",SGD,MAINBOARD,STOCK,28.53,28.50,28.55,8000'
].join("\r\n")+"\r\n";
const meta={as_of_date:"2026-11-14",source_url:"https://www.sgx.com/securities/securities-prices?code=stocks"};
const doc=normalize(csv,meta);
const original=decodeOriginalCsv(Buffer.from(csv,"utf8"));
assert.equal(original.csv,csv);
const invalidBytes=Buffer.from([0xff,0xfe]);
assert.throws(()=>decodeOriginalCsv(invalidBytes));
assert.throws(()=>decodeOriginalCsv(csv));

assert.equal(doc.item_count,3);
assert.deepEqual(doc.items.map(x=>x.trading_code),["D05","J36","O39"]);
assert.equal(doc.items[1].trading_name,"Jardine Matheson, Holdings Ltd");
assert.equal(doc.items[1].trading_currency,"USD");
assert.equal(doc.original_csv_sha256.length,64);
assert.equal(doc.original_csv_sha256,original.sha256);
assert.equal(doc.original_file_is_sgx_verified,false);
assert.equal(doc.full_sgx_universe_verified,false);
assert.equal(doc.quote_columns_stripped,true);
assert.equal(doc.distribution_rights_reviewed,false);
assert.equal(doc.ranking_eligible_count,0);
for(const x of doc.items)assert.deepEqual(Object.keys(x),[
 "trading_code","trading_name","trading_currency","instrument_type","listing_board"
]);
assert.deepEqual(csvRows('name,code\n"First\nSecond",ABC\n'),[
 ["name","code"],["First\nSecond","ABC"]
]);
for(const change of [
 ()=>normalize(csv,{...meta,as_of_date:"2026-02-30"}),
 ()=>normalize(csv,{...meta,source_url:"https://example.org/"}),
 ()=>normalize(csv.replace("Traded Currency","Price"),meta),
 ()=>normalize(csv+"O39,Duplicate,SGD,MAINBOARD,STOCK,9,8,10,20\r\n",meta),
 ()=>normalize(csv.replace("D05,","D0#,"),
  meta),
 ()=>normalize('Trading Code,Trading Name,Traded Currency\nD05,"unfinished,SGD',meta)
])assert.throws(change);
console.log("v199 PASS: manual staging handles quoted CSV, keeps currency-specific counters, drops price columns and never claims complete master");
