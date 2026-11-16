"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const {checkFeed,validDate}=require("../scripts/check-ranking-license-evidence-v290.js");
const real=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const research=JSON.parse(fs.readFileSync("docs/data/sgx-market-license-review-v290.json","utf8"));
assert.equal(research.status,"NO_LICENSE_GRANT_OBTAINED");
assert.equal(research.current_sgx_policy_effective_date,"2026-07-01");
assert.equal(research.rights_granted.browser_display,false);
assert.equal(research.rights_granted.backend_non_display_analytics,false);
assert.deepEqual(checkFeed(real),[],"actual feed remains gated");
assert.equal(validDate("2026-02-30"),false);
assert.equal(validDate("2026-11-15"),true);
const data=structuredClone(real);
const row=data.records[0];
row.ranking_eligible=true;row.ranking_score=1;row.exclusion_reasons=[];
row.quote_source_type="LICENSED_SGX_EQUITY";
row.quote_license_display_allowed=true;
row.quote_license_non_display_analytics_allowed=true;
row.independent_cross_source_verification=true;
row.quote_timestamp_utc="2026-11-13T09:00:00Z";
row.shares_as_of_date="2026-11-13";
row.pbr_verified=Number((row.price_sgd*row.shares_outstanding/(1000*row.parent_equity_sgd_thousands)).toFixed(4));
data.ranking_eligible_count=1;data.ranking_enabled=true;
assert.ok(checkFeed(data).some(x=>x.includes("dated grant evidence missing")));
row.market_data_license_evidence={
 grant_status:"EXECUTED",grant_evidence_url:"https://example.org/contract/123",
 licensor:"Test SGX licensed distributor",licensee:"VALUE HUNTER AI demo",
 licensed_product:"SGX cash equities",usage_scopes:["BROWSER_DISPLAY","BACKEND_NON_DISPLAY_ANALYTICS","REDISTRIBUTION"],
 valid_from:"2026-01-01",valid_until:"2026-12-31"
};
assert.deepEqual(checkFeed(data),[],"synthetic structurally valid licensed record");
const midnight=structuredClone(data);
midnight.records[0].quote_timestamp_utc="2026-11-12T16:00:00Z";
midnight.records[0].market_data_license_evidence.valid_from="2026-11-13";
assert.deepEqual(checkFeed(midnight),[],"grant starts on Singapore trading date");
function reject(mutator,phrase){const a=structuredClone(data);mutator(a.records[0]);assert.ok(checkFeed(a).some(x=>x.includes(phrase)),phrase)}
reject(r=>{r.market_data_license_evidence.grant_status="PENDING"},"provenance incomplete");
reject(r=>{r.market_data_license_evidence.grant_evidence_url="http://example.org/proof"},"provenance incomplete");
reject(r=>{r.market_data_license_evidence.usage_scopes=["BROWSER_DISPLAY"]},"usage scopes");
for (const redistributionFlag of [undefined, false, true]) {
  reject(r=>{
    r.quote_publicly_redistributed=redistributionFlag;
    r.market_data_license_evidence.usage_scopes=["BROWSER_DISPLAY","BACKEND_NON_DISPLAY_ANALYTICS"];
  },"usage scopes");
}
reject(r=>{r.market_data_license_evidence.valid_from="2026-02-30"},"validity dates");
reject(r=>{r.market_data_license_evidence.valid_from="2026-11-14";r.market_data_license_evidence.valid_until="2026-11-15"},"outside license validity");
reject(r=>{r.quote_url="invalid"},"origin URL");
console.log("v290 PASS: 2026 official policy research and positive/negative grant evidence guard; no actual rights asserted");
