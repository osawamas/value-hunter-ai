"use strict";
const assert=require("node:assert/strict"),{validate}=require("./bank-nii-v178.js");
const fs=require("node:fs");
const paths=["latest.json","sgx-big3-nii-v177.json","sgx-dbs-2026q3-original-v170.json",
 "sgx-ocbc-bank-research-v166.json","sgx-uob-exact-bank-table-v175.json"];
const items=paths.map(x=>JSON.parse(fs.readFileSync("docs/data/"+x,"utf8")));
const x=validate(...items);
assert.equal(x.total,8302);
assert.equal(x.dbs+x.ocbc+x.uob,x.total);
const fake=JSON.parse(JSON.stringify(items[1]));fake.record.independent_third_party_earnings_audit=true;
assert.throws(()=>validate(items[0],fake,...items.slice(2)));
const bad=JSON.parse(JSON.stringify(items[3]));bad.sgx_original_pdf_sha256="a".repeat(64);
assert.throws(()=>validate(items[0],items[1],items[2],bad,items[4]));
console.log("v178 SGX bank original 8302 SGD million NII consistency UI strict");
