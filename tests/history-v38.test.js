"use strict";
const assert = require("node:assert/strict");
const {historicalObservations} = require("../docs/app.js");

const entries = [
  {date_utc: "2026-11-13", records: [{symbol: "S63", price_sgd: 9.67, quote_timestamp_utc: "2026-11-13T09:00:00+00:00"}]},
  {date_utc: "2026-11-14", records: [{symbol: "S63", price_sgd: 9.67, quote_timestamp_utc: "2026-11-13T09:00:00+00:00"}]},
  {date_utc: "2026-11-15", records: [{symbol: "S63", price_sgd: null, quote_timestamp_utc: "2026-11-15T09:00:00+00:00"}]},
  {date_utc: "2026-11-16", records: [{symbol: "S63", price_sgd: 9.81, quote_timestamp_utc: "2026-11-16T09:00:00+00:00"}]},
  {date_utc: "2026-11-17", records: [{symbol: "S63", price_sgd: 9.81, quote_timestamp_utc: null}]}
];
const results = historicalObservations(entries, "S63", "price_sgd");
assert.equal(results.length, 2, "repeat/undated/missing quotes must not add data points");
assert.deepEqual(results.map(r => r.date), ["2026-11-13", "2026-11-16"]);
assert.deepEqual(results.map(r => r.value), [9.67, 9.81]);
assert.equal(historicalObservations(entries, "G13", "price_sgd").length, 0);
console.log("v38 JS history observation tests passed");
