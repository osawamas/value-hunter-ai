"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validate}=require("./bank-nine-month-v184.js");
const data=["latest.json","sgx-dbs-exact-table-v180.json","sgx-ocbc-bank-research-v166.json",
 "sgx-uob-exact-bank-table-v175.json"].map(name=>JSON.parse(fs.readFileSync("docs/data/"+name,"utf8")));
const result=validate(...data);
assert.deepEqual(result.map(x=>x.current),[8822,6237,4165]);
assert.deepEqual(result.map(x=>x.prior),[8675,5677,3271]);
assert.ok(result[0].changePct>1.6&&result[0].changePct<1.8);
assert.ok(result[1].changePct>9.8&&result[1].changePct<10.0);
assert.ok(result[2].changePct>27&&result[2].changePct<28);
const modified=JSON.parse(JSON.stringify(data[1]));
modified.record.exact_original_table_rows["Net profit"].source_column_values[6]="9,999";
assert.throws(()=>validate(data[0],modified,data[2],data[3]));
const promoted=JSON.parse(JSON.stringify(data[0]));promoted.ranking_eligible_count=1;
assert.throws(()=>validate(promoted,...data.slice(1)));
console.log("v184 bank original exact nine month same-period profit YoY checks passed");
