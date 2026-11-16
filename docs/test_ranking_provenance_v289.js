"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const {checkFeed} = require("../scripts/check-ranking-provenance-v289.js");
const feed = JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
assert.deepEqual(checkFeed(feed), [], "actual published feed must pass");
const clone = () => structuredClone(feed);
function expectFail(mutate, phrase) {
  const f = clone(); mutate(f);
  assert.ok(checkFeed(f).some(e => e.includes(phrase)), phrase);
}
expectFail(f => {f.records[0].ranking_eligible=true;f.ranking_eligible_count=1;f.ranking_enabled=true;f.records[0].ranking_score=1;}, "unofficial quote");
expectFail(f => {f.records[0].ranking_score=12;}, "excluded record");
expectFail(f => {f.ranking_eligible_count=1;}, "eligible count");
expectFail(f => {f.records.push({...f.records[0]});f.coverage.registered_count++;}, "duplicate symbol");
expectFail(f => {f.coverage.registered_count++;}, "registered_count");
expectFail(f => {f.ranking_enabled=true;}, "ranking_enabled");
const clean = clone();
const r = clean.records[0];
r.ranking_eligible=true; r.ranking_score=12; r.exclusion_reasons=[];
r.quote_source_type="LICENSED_SGX_EQUITY";
r.quote_license_display_allowed=true;
r.quote_license_non_display_analytics_allowed=true;
r.independent_cross_source_verification=true;
r.quote_timestamp_utc="2026-11-13T09:00:00Z";
r.shares_as_of_date="2026-11-13";
r.pbr_verified=Number((r.price_sgd*r.shares_outstanding/(1000*r.parent_equity_sgd_thousands)).toFixed(4));
clean.ranking_eligible_count=1;clean.ranking_enabled=true;
assert.deepEqual(checkFeed(clean), [], "fully evidenced synthetic record accepted");
for (const [field, value, label] of [
  ["price_sgd", 0, "invalid price or shares"],
  ["market_cap_sgd", r.market_cap_sgd + 1, "market cap"],
  ["attributable_profit_sgd_thousands", -1, "PER"],
  ["per_reference", r.per_reference + 1, "PER"],
  ["pbr_verified", null, "PBR"],
  ["pbr_verified", r.price_sgd*r.shares_outstanding/(1000*(r.parent_equity_sgd_thousands + 100000)), "PBR"],
]) {
  const invalid=structuredClone(clean);
  invalid.records[0][field]=value;
  assert.ok(checkFeed(invalid).some(e=>e.includes(label)), field);
}
r.quote_timestamp_utc="2026-11-12T16:00:00Z";
assert.deepEqual(checkFeed(clean), [], "Singapore quote day rolls over at midnight local time");
r.shares_as_of_date="2026-11-12";
assert.ok(checkFeed(clean).some(e=>e.includes("same Singapore date")));
r.shares_as_of_date="2026-11-13";
for (const bad of ["2026-02-30T09:00:00Z", "2026-11-13T09:00:00", "2026-11-13T24:00:00Z"]) {
  r.quote_timestamp_utc=bad;
  assert.ok(checkFeed(clean).some(e=>e.includes("missing dated quote/shares")), bad);
}
r.quote_timestamp_utc="2026-11-13T09:00:00Z";
r.shares_as_of_date="2026-11-31";
assert.ok(checkFeed(clean).some(e=>e.includes("missing dated quote/shares")));
r.shares_as_of_date="2026-11-13";
r.quote_license_non_display_analytics_allowed=false;
assert.ok(checkFeed(clean).some(e=>e.includes("non-display")));
console.log("v289 PASS: published feed and negative/positive ranking-provenance mutations");
