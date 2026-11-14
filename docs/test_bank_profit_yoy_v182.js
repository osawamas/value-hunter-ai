"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const {validate}=require("./bank-profit-yoy-v182.js");
const paths=["latest.json","sgx-dbs-exact-table-v180.json",
 "sgx-ocbc-bank-research-v166.json","sgx-uob-exact-bank-table-v175.json"];
const data=paths.map(p=>JSON.parse(fs.readFileSync("docs/data/"+p,"utf8")));
const rows=validate(...data);
assert.equal(rows.length,3);
assert.ok(rows[0].changePct<-4.7 && rows[0].changePct>-4.9);
assert.ok(rows[1].changePct>3.2 && rows[1].changePct<3.3);
assert.ok(rows[2].changePct>182 && rows[2].changePct<183);
assert.equal(rows[2].prior,443);
const bad=JSON.parse(JSON.stringify(data[3]));bad.record.period_specific_table_rows["Net profit"]["3q25"]=1250;
assert.throws(()=>validate(data[0],data[1],data[2],bad));
const unsafe=JSON.parse(JSON.stringify(data[0]));unsafe.ranking_eligible_count=1;
assert.throws(()=>validate(unsafe,...data.slice(1)));
console.log("v182 actual DBS OCBC UOB comparable quarter YoY growth calculated from original tables");
