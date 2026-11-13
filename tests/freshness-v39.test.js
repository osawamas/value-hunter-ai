"use strict";
const assert = require("node:assert/strict");
const {freshnessState, liveQuality} = require("../docs/app.js");
const NOW = Date.parse("2026-11-13T15:00:00Z");
assert.equal(freshnessState("2026-11-13T09:00:00Z",7,NOW),"RECENT");
assert.equal(freshnessState("2026-11-01T09:00:00Z",7,NOW),"STALE");
assert.equal(freshnessState("2026-11-15T09:00:00Z",7,NOW),"STALE");
assert.equal(freshnessState(null,7,NOW),"MISSING");
assert.equal(freshnessState("invalid",7,NOW),"MISSING");
assert.equal(freshnessState("2026-06-30",180,NOW),"RECENT");
assert.equal(freshnessState("2026-02-27",180,NOW),"STALE");
const feed = {
  updated_at_utc:"2026-11-01T15:00:00Z",
  records:[
    {quote_timestamp_utc:"2026-11-13T09:00:00Z",price_sgd:9.67,shares_as_of_date:"2026-06-30",quality_flags:[]},
    {quote_timestamp_utc:"2026-11-01T09:00:00Z",price_sgd:1.44,shares_as_of_date:"2026-02-27",quality_flags:[]},
    {quote_timestamp_utc:null,price_sgd:null,shares_as_of_date:null,quality_flags:["MARKET_CAP_ARITHMETIC_MISMATCH"]}
  ]
};
assert.deepEqual(liveQuality(feed,NOW),{
 feed:"STALE",staleQuotes:1,missingQuotes:1,staleShares:1,arithmeticIssues:1
});
console.log("v39 live freshness tests passed");
