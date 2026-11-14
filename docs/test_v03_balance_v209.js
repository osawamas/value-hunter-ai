"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const x=JSON.parse(fs.readFileSync("docs/data/sgx-v03-balance-v209.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const seed=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
function verify(d,f,s){
 assert.equal(d.schema_version,"sgx-v03-fy2025-annual-balance-v209");
 assert.equal(d.symbol,"V03");assert.equal(d.period_end,"2025-12-31");
 assert.equal(d.currency,"SGD");
 assert.equal(d.unit,"SGD_millions_rounded_1_decimal");
 assert.equal(d.source_pdf_sha256,null);
 assert.equal(d.original_pdf_bytes_verified,false);
 assert.equal(d.group_statement_independent_numeric_validation,false);
 assert.equal(d.financial_feed_registered,false);
 assert.equal(d.ranking_eligible,false);
 assert.equal(d.total_equity_reported_from_source,false);
 assert.equal(d.noncontrolling_equity_numerically_verified,false);
 assert.equal(d.derived_total_equity_only_from_assets_minus_liabilities,true);
 assert.equal(d.no_current_market_valuation_allowed,true);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.ok(!f.records.some(r=>r.symbol==="V03"));
 assert.ok(s.rows.some(r=>r.symbol==="V03"));
 const expected={FY2025:[2534.5,227.0,3602.2,804.4,2792.7,2797.8,5.1],
                 FY2024:[2735.9,245.0,3699.9,805.6,2889.8,2894.3,4.5]};
 for(const year of ["FY2025","FY2024"]){
  const r=d.historical[year],e=expected[year];
  assert.deepEqual([r.revenue,r.parent_profit,r.assets,r.liabilities,r.parent_equity],e.slice(0,5));
  const derived=Math.round((r.assets-r.liabilities)*10)/10;
  assert.equal(derived,e[5]);
  const residual=Math.round((derived-r.parent_equity)*10)/10;
  assert.equal(residual,e[6]);
  assert.ok(derived>=r.parent_equity);
 }
 return true;
}
verify(x,feed,seed);
for(const mutation of [
 (x,f,s)=>{x.historical.FY2025.assets++},
 (x,f,s)=>{x.historical.FY2024.parent_equity++},
 (x,f,s)=>{x.noncontrolling_equity_numerically_verified=true},
 (x,f,s)=>{x.original_pdf_bytes_verified=true},
 (x,f,s)=>{x.financial_feed_registered=true},
 (x,f,s)=>{x.ranking_eligible=true},
 (x,f,s)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(x),b=structuredClone(feed),c=structuredClone(seed);
 mutation(a,b,c);assert.throws(()=>verify(a,b,c));
}
console.log("v209 PASS: V03 group assets and liabilities reconcile, parent equity remains separate from derived total equity");
