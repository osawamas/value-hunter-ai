"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const seed=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
const research=JSON.parse(fs.readFileSync("docs/data/sgx-additional-issuer-fy2025-v206.json","utf8"));
function verify(x,f,s){
 assert.equal(x.schema_version,"sgx-additional-issuer-fy2025-research-v206");
 assert.equal(x.period_end,"2025-12-31");
 assert.equal(x.reported_currency,"SGD");
 assert.equal(x.unit,"SGD_millions");
 assert.equal(x.original_source_pdf_bytes_downloaded,false);
 assert.equal(x.original_source_sha256_verified,false);
 assert.equal(x.independent_third_party_numeric_verification,false);
 assert.equal(x.financial_feed_modified,false);
 assert.equal(x.registered_financial_count_increment,0);
 assert.equal(x.ranking_eligible_count_increment,0);
 assert.equal(x.licensed_timed_sgx_quotes_available,false);
 assert.equal(x.date_matched_ex_treasury_shares_verified,false);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(f.coverage.registered_count,7);
 assert.equal(s.official_full_security_master_obtained,false);
 assert.equal(x.items.length,2);
 const desired={BN4:{r25:5983,r24:5784,p25:789,p24:940,basis:"CONTINUING_OPERATIONS_ONLY"},
                V03:{r25:2534.5,r24:2735.9,p25:227,p24:245,basis:"CONSOLIDATED_GROUP_REPORTED"}};
 for(const code of ["BN4","V03"]){
  const entries=x.items.filter(y=>y.symbol===code);
  assert.equal(entries.length,1);
  const r=entries[0],e=desired[code];
  assert.ok(s.rows.some(y=>y.symbol===code));
  assert.ok(!f.records.some(y=>y.symbol===code));
  assert.equal(r.revenue_2025_m_sgd,e.r25);
  assert.equal(r.revenue_2024_m_sgd,e.r24);
  assert.equal(r.reported_parent_net_profit_2025_m_sgd,e.p25);
  assert.equal(r.reported_parent_net_profit_2024_m_sgd,e.p24);
  assert.equal(r.revenue_basis,e.basis);
  assert.equal(r.adjusted_profit_excluded_from_reported_comparison,true);
  assert.equal(r.financial_feed_registered,false);
  assert.equal(r.latest_shares_and_quote_not_verified,true);
  assert.equal(r.ranking_eligible,false);
  assert.match(r.source_url,/^https:\/\//);
 }
 assert.equal(x.items[0].adjusted_new_keppel_profit_2025_m_sgd,1100);
 assert.equal(x.items[0].reported_parent_net_profit_2025_m_sgd,789);
 return true;
}
verify(research,feed,seed);
const html=fs.readFileSync("docs/index.html","utf8");
const {validate}=require("./additional-issuer-research-v206.js");
assert.ok(html.includes('src="./additional-issuer-research-v206.js"'));
assert.ok(html.includes('id="additionalIssuerResearchRows"'));
assert.ok(html.includes('id="additionalIssuerResearchStatus"'));
const view=validate(feed,seed,research);
assert.deepEqual(view.map(x=>[x.symbol,x.revenue,x.reported_profit]),[
 ["BN4",5983,789],["V03",2534.5,227]
]);

for(const mutate of [
 (x,f,s)=>{x.items[0].reported_parent_net_profit_2025_m_sgd=1100},
 (x,f,s)=>{x.items[1].financial_feed_registered=true},
 (x,f,s)=>{x.items[0].latest_shares_and_quote_not_verified=false},
 (x,f,s)=>{x.original_source_sha256_verified=true},
 (x,f,s)=>{x.items[1].revenue_2024_m_sgd=2357},
 (x,f,s)=>{f.ranking_eligible_count=1},
 (x,f,s)=>{s.official_full_security_master_obtained=true}
 ]){
 const x=structuredClone(research),f=structuredClone(feed),s=structuredClone(seed);
 mutate(x,f,s);assert.throws(()=>verify(x,f,s));
}
console.log("v206 PASS: BN4/V03 FY2025 original issuer research staged without mistaking adjusted profit for reported profit");
