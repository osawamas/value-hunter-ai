"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {compareOfficialMonthEnd}=require("./universe-coverage-audit-v205.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const base=[
 read("docs/data/latest.json"),read("docs/data/sgx-universe-candidates.json"),
 read("docs/data/sgx-official-batch-seed-v196.json"),
 read("docs/data/sgx-official-monthend-aug2026-v251.json")
];
function check(a){
 const result=compareOfficialMonthEnd(...a);
 assert.equal(result.official_historical_listed_securities,604);
 assert.equal(result.official_historical_mainboard+result.official_historical_catalist,604);
 assert.equal(result.third_party_candidates,182);
 assert.equal(result.historical_count_issuer_universe_comparable,false);
 assert.equal(result.historical_count_not_current,true);
 assert.equal(result.official_master_complete,false);
 assert.equal(result.quote_or_valuation_permitted,false);
 assert.equal(result.ranking_eligible,0);
}
check(base);
for(const edit of [
 a=>{a[3].reported_total_listed_securities=605},
 a=>{a[3].reported_mainboard_listings=405},
 a=>{a[3].reported_catalist_listings=199},
 a=>{a[3].report_month="2026-11"},
 a=>{a[3].source_url="https://example.com/SGX.pdf"},
 a=>{a[3].official_security_master_complete=true},
 a=>{a[3].not_issuer_level_registry=false},
 a=>{a[3].not_current_asof_2026_11_15=false},
 a=>{a[3].ranking_eligible=true},
 a=>{a[1].full_sgx_listing_completeness_verified=true},
 a=>{a[0].ranking_eligible_count=1}
]){
 const args=base.map(x=>structuredClone(x));edit(args);assert.throws(()=>check(args));
}
const html=fs.readFileSync("docs/index.html","utf8");
const js=fs.readFileSync("docs/universe-coverage-audit-v205.js","utf8");
assert.match(html,/id="universeCoverageAuditRows"/);
assert.match(js,/SGX公式2026年8月末の上場証券604/);
assert.match(js,/182\/604を取得率や未収録銘柄数に換算しない/);
assert.match(js,/sgx-official-monthend-aug2026-v251\.json/);
console.log("v251 PASS: SGX historical 604 aggregate never equated to partial 182-company candidate coverage or investability");
