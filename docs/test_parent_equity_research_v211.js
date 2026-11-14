"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const data=JSON.parse(fs.readFileSync("docs/data/sgx-parent-equity-research-v211.json","utf8"));
function verify(x,f){
 assert.equal(x.schema_version,"sgx-g13-s63-parent-equity-external-figure-v211");
 assert.equal(x.period_end,"2025-12-31");
 assert.equal(x.cross_publisher_historical_figures_only,true);
 assert.equal(x.external_provider_filing_origin_not_independently_authenticated,true);
 assert.equal(x.parent_equity_independent_audit_completed,false);
 assert.equal(x.independent_source_recalculation_confirmed,false);
 assert.equal(x.original_external_provider_dataset_hash_verified,false);
 assert.equal(x.verified_market_quote_and_same_date_shares,false);
 assert.equal(x.financial_feed_modified,false);
 assert.equal(x.ranking_eligible_count,0);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.equal(x.records.length,2);
 const g=x.records.find(r=>r.symbol==="G13"),s=x.records.find(r=>r.symbol==="S63");
 assert.equal(x.records.filter(r=>r.symbol==="G13").length,1);
 assert.equal(x.records.filter(r=>r.symbol==="S63").length,1);
 const fg=f.records.find(r=>r.symbol==="G13"),fs63=f.records.find(r=>r.symbol==="S63");
 assert.equal(fg.fiscal_year,2025);
 assert.equal(fs63.fiscal_year,2025);
 assert.equal(fg.parent_equity_sgd_thousands,8205416);
 assert.equal(fs63.parent_equity_sgd_thousands,2573638);
 assert.equal(g.provider_unit,"SGD_thousands");
 assert.equal(g.provider_parent_equity,fg.parent_equity_sgd_thousands);
 assert.equal(g.provider_total_assets,fg.assets_sgd_thousands);
 assert.equal(g.provider_total_liabilities,fg.liabilities_sgd_thousands);
 assert.equal(g.issuer_parent_equity_sgd_thousands,fg.parent_equity_sgd_thousands);
 assert.equal(g.provider_total_assets-g.provider_total_liabilities,g.provider_parent_equity);
 assert.equal(s.provider_unit,"SGD_millions_rounded");
 assert.equal(s.provider_scope,"TOTAL_COMMON_EQUITY_DISTINCT_FROM_TOTAL_EQUITY");
 assert.equal(s.issuer_parent_equity_sgd_thousands,fs63.parent_equity_sgd_thousands);
 assert.equal(s.issuer_total_equity_sgd_thousands,fs63.equity_sgd_thousands);
 assert.equal(s.issuer_total_assets_sgd_thousands,fs63.assets_sgd_thousands);
 for(const [rounded,exact] of [
 [s.provider_parent_equity,s.issuer_parent_equity_sgd_thousands],
 [s.provider_total_equity,s.issuer_total_equity_sgd_thousands],
 [s.provider_total_assets,s.issuer_total_assets_sgd_thousands]
 ])assert.ok(Math.abs(rounded-exact/1000)<=0.5);
 for(const r of x.records){
  assert.equal(r.independent_auditor_confirmation,false);
  assert.equal(r.ranking_eligible,false);
  assert.match(r.source_url,/^https:\/\//);
 }
 return true;
}
verify(data,feed);
for(const mutation of [
 (x,f)=>{x.parent_equity_independent_audit_completed=true},
 (x,f)=>{x.records[0].provider_parent_equity++},
 (x,f)=>{x.records[1].provider_parent_equity=3000},
 (x,f)=>{x.records[1].provider_scope="TOTAL_EQUITY"},
 (x,f)=>{x.records[1].independent_auditor_confirmation=true},
 (x,f)=>{x.verified_market_quote_and_same_date_shares=true},
 (x,f)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(data),b=structuredClone(feed);mutation(a,b);
 assert.throws(()=>verify(a,b));
}
console.log("v211 PASS: G13 exact and S63 rounded parent equity match external publisher, not independent audit");
