"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const {validate}=require("./ranking-blockers-v185.js");
const files=["latest.json","sgx-first-issuer-gate-v137.json","sgx-ranking-readiness-v117.json"];
const items=files.map(x=>JSON.parse(fs.readFileSync("docs/data/"+x,"utf8")));
const aligned=items[0].updated_at_utc===items[1].feed_updated_at_utc &&
              items[0].updated_at_utc===items[2].published_feed_updated_at_utc;
if(aligned){
  const rows=validate(...items);
  assert.deepEqual(rows.map(x=>x.symbol),["G13","S63","D05","O39","U11"]);
  assert.deepEqual(rows.slice(0,2).map(x=>x.passed),[1,1]);
  assert.deepEqual(rows.slice(2).map(x=>x.total),[3,3,3]);
  assert.ok(rows[0].missing.includes("SGX正規約定価格"));
  assert.ok(rows[2].missing.includes("銀行株の最新自己株式控除後株数"));
}else{
  assert.throws(()=>validate(...items));
  assert.equal(items[0].ranking_eligible_count,0);
  assert.equal(items[1].eligible_count,0);
  assert.equal(items[2].ranking_eligible_count,0);
  console.log("Expected safe hide during asynchronous finance/sidecar refresh");
}
const old=JSON.parse(JSON.stringify(items[1]));old.feed_updated_at_utc="old";
assert.throws(()=>validate(items[0],old,items[2]));
const fake=JSON.parse(JSON.stringify(items[0]));fake.ranking_eligible_count=1;
assert.throws(()=>validate(fake,items[1],items[2]));
console.log("v185 registered issuer evidence blockers bound to up-to-date feed");
