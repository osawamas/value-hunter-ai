"use strict";
/* v192: cross-check independently stored quarterly, share-action and feed evidence.
   These checks do NOT independently authenticate the PDF or grant SGX market-data rights. */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const bank=JSON.parse(fs.readFileSync("docs/data/sgx-big3-bank-research-v186.json","utf8"));
const actions=JSON.parse(fs.readFileSync("docs/data/sgx-bank-corporate-actions-v190.json","utf8"));
function check(f,b,a){
  assert.equal(f.schema_version,"value_hunter_web_v29");
  assert.equal(f.ranking_enabled,false);
  assert.equal(f.ranking_eligible_count,0);
  assert.ok(f.coverage.all_sgx_listed===false);
  const registered=new Set(f.records.map(r=>r.symbol));
  assert.equal(registered.size,f.records.length,"duplicate financial feed symbol");
  for(const code of ["D05","O39","U11"]){
    assert.ok(registered.has(code),"bank missing from financial feed");
    assert.equal(f.records.find(r=>r.symbol===code).ranking_eligible,false);
  }
  assert.equal(b.period_end,"2026-09-30");
  assert.equal(b.independent_third_party_financial_verification,false);
  assert.equal(b.authentic_current_sgx_execution_quotes_verified,false);
  assert.equal(b.latest_treasury_adjusted_share_counts_verified,false);
  assert.equal(b.current_market_cap_per_pbr_verified,false);
  assert.equal(b.ranking_eligible,false);
  assert.deepEqual(new Set(b.entries.map(e=>e.symbol)),new Set(["D05","O39","U11"]));
  const totals=[
    ["q3profit","total_3q26_bank_net_profit",6105],
    ["nineprofit","total_9m26_bank_net_profit",19224],
    ["q3nii","total_3q26_net_interest_income",8302],
    ["ninenii","total_9m26_net_interest_income",24484]
  ];
  for(const [field,sumKey,expected] of totals){
    assert.equal(b.entries.reduce((s,r)=>s+r[field],0),expected);
    assert.equal(b[sumKey],expected);
  }
  assert.equal(a.uob.symbol,"U11");assert.equal(a.ocbc.symbol,"O39");
  assert.equal(a.verified_as_of_date,"2026-11-12");
  const rows=a.uob.observations;
  assert.equal(rows.length,2);
  assert.deepEqual(rows.map(r=>r.date),["2026-11-11","2026-11-12"]);
  assert.equal(rows[0].issued_excluding_treasury_after-rows[1].issued_excluding_treasury_after,34000);
  assert.equal(rows[1].issued_excluding_treasury_after,1646711591);
  assert.equal(a.uob.latest_unverified.date,"2026-11-13");
  assert.equal(a.uob.latest_unverified.official_verified,false);
  assert.equal(a.uob.latest_unverified.may_enter_ranking,false);
  assert.equal(a.ocbc.outstanding_change_notice.official_attachment_obtained,false);
  assert.equal(a.ocbc.outstanding_change_notice.share_change_verified,false);
  assert.equal(a.ocbc.outstanding_change_notice.may_enter_ranking,false);
  assert.equal(a.source_policy.licensed_timestamped_quotation_available,false);
  assert.equal(a.ranking_eligible,false);
  assert.equal(a.financial_feed_modified,false);
  // A newer secondary report cannot supersede an older verified snapshot.
  assert.ok(a.verified_as_of_date<a.uob.latest_unverified.date);
  return true;
}
check(feed,bank,actions);
for(const edit of [
  (f,b,a)=>{f.ranking_eligible_count=1},
  (f,b,a)=>{b.latest_treasury_adjusted_share_counts_verified=true},
  (f,b,a)=>{b.total_3q26_bank_net_profit++},
  (f,b,a)=>{a.verified_as_of_date="2026-11-13"},
  (f,b,a)=>{a.uob.latest_unverified.official_verified=true},
  (f,b,a)=>{a.ocbc.outstanding_change_notice.share_change_verified=true},
  (f,b,a)=>{a.source_policy.licensed_timestamped_quotation_available=true}
]){
  const f=structuredClone(feed),b=structuredClone(bank),a=structuredClone(actions);
  edit(f,b,a);assert.throws(()=>check(f,b,a));
}
console.log("v192 PASS: financial feed, bank issuer aggregates and historical corporate actions remain separate; official share and market-data permissions unverified");
