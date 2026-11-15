"use strict";
const assert = require("node:assert/strict");
const {filterMarketRows} = require("./market-research.js");
const rows = [
  {id:"JP:7203",market:"JP",symbol:"7203",label:"Toyota",financials:{periods:[]}},
  {id:"US:TEST",market:"US",symbol:"TEST",label:"Quarterly issuer",quarterly:{periods:[]}},
  {id:"SG:S63",market:"SG",symbol:"S63",label:"ST Engineering",sgxAnnual:{end:"FY2025"}},
  {id:"US:NONE",market:"US",symbol:"NONE",label:"Missing issuer"},
];
assert.deepEqual(filterMarketRows(rows,"","", "annual").map(x=>x.id),["JP:7203","SG:S63"]);
assert.deepEqual(filterMarketRows(rows,"","", "quarterly").map(x=>x.id),["US:TEST"]);
assert.deepEqual(filterMarketRows(rows,"","", "missing").map(x=>x.id),["US:TEST","US:NONE"]);
assert.deepEqual(filterMarketRows(rows,"US","test", "quarterly").map(x=>x.id),["US:TEST"]);
assert.deepEqual(filterMarketRows(rows,"JP","", "missing"),[]);
assert.equal(filterMarketRows(rows,"","").length,4);
console.log("three-market financial evidence filters: OK");
