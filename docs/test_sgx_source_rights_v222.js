"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const policy=JSON.parse(fs.readFileSync("docs/data/sgx-source-rights-review-v222.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function verify(p,f){
 assert.equal(p.schema_version,"sgx-source-reuse-policy-v222");
 assert.equal(p.must_not_assume_free_api_means_redistribution_rights,true);
 assert.equal(p.financial_feed_modified,false);
 assert.equal(p.ranking_eligible_count,0);
 assert.equal(p.official_full_list_available,false);
 assert.equal(p.licensed_time_stamped_quote_available,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(f.ranking_enabled,false);
 assert.equal(p.feeds.length,3);
 const s=p.feeds.find(x=>x.id==="SGX_OFFICIAL_TRADING_PAGE");
 const a=p.feeds.find(x=>x.id==="STOCKSSG_COMPANY_API");
 const m=p.feeds.find(x=>x.id==="SGX_OFFICIAL_MARKET_DATA");
 assert.ok(s&&a&&m);
 assert.equal(s.official_sgx_source,true);
 assert.equal(s.collected_scope,"STATIC_EXAMPLES_ONLY");
 assert.equal(s.source_identifiers_only,true);
 assert.equal(s.full_security_master_verified,false);
 assert.equal(a.free_api_tier_documented,true);
 assert.equal(a.rate_limit_without_key_per_minute,10);
 assert.equal(a.terms_prohibit_reproducing_redistributing_without_permission,true);
 assert.equal(a.collected_scope,"RESEARCH_ONLY_NO_DATA_CAPTURE");
 assert.equal(a.public_dataset_redistribution_authorized,false);
 assert.equal(m.licensed_feed_contract_obtained,false);
 assert.equal(m.collected_scope,"NOT_CONNECTED");
 for(const x of p.feeds){
  assert.match(x.source_url,/^https:\/\//);
  assert.equal(x.public_quote_redistribution_authorized,false);
  assert.equal(x.market_data_fields_allowed,false);
  assert.equal(x.can_enable_rankings,false);
  assert.equal(x.full_security_master_verified,false);
 }
 return true;
}
verify(policy,feed);
for(const edit of [
 (p,f)=>{p.feeds[1].public_quote_redistribution_authorized=true},
 (p,f)=>{p.feeds[1].collected_scope="FULL_LIST_PUBLIC"},
 (p,f)=>{p.feeds[0].full_security_master_verified=true},
 (p,f)=>{p.feeds[2].licensed_feed_contract_obtained=true},
 (p,f)=>{p.licensed_time_stamped_quote_available=true},
 (p,f)=>{f.ranking_eligible_count=1}
]){
 const p=structuredClone(policy),f=structuredClone(feed);edit(p,f);
 assert.throws(()=>verify(p,f));
}
console.log("v222 PASS: free API does not imply permission to redistribute a third-party exchange master or licensed stock quotes");
