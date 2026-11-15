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
clean.ranking_eligible_count=1;clean.ranking_enabled=true;
assert.deepEqual(checkFeed(clean), [], "fully evidenced synthetic record accepted");
r.quote_license_non_display_analytics_allowed=false;
assert.ok(checkFeed(clean).some(e=>e.includes("non-display")));
console.log("v289 PASS: published feed and negative/positive ranking-provenance mutations");
