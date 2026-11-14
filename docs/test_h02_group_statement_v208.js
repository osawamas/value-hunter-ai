"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const d=JSON.parse(fs.readFileSync("docs/data/sgx-h02-group-statement-v208.json","utf8"));
const f=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const seed=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
function check(x,feed,official){
 assert.equal(x.schema_version,"sgx-h02-group-statement-v208");
 assert.equal(x.symbol,"H02");assert.equal(x.period_end,"2025-12-31");
 assert.equal(x.unit,"SGD_thousands");
 assert.equal(x.pdf_sha256,null);
 assert.equal(x.source_pdf_bytes_locally_verified,false);
 assert.equal(x.independent_third_party_numeric_verification,false);
 assert.equal(x.parent_attributable_profit_from_this_staging_verified,false);
 assert.equal(x.operating_profit_specific_line_extracted,false);
 assert.equal(x.financial_feed_registered,false);
 assert.equal(x.investment_ranking_eligible,false);
 assert.equal(x.ranking_eligibility_permitted,false);
 assert.equal(feed.ranking_enabled,false);
 assert.equal(feed.ranking_eligible_count,0);
 assert.ok(!feed.records.some(r=>r.symbol==="H02"));
 assert.ok(official.rows.some(r=>r.symbol==="H02"));
 assert.deepEqual([x.source_pdf_page_indices_zero_based.income,x.source_pdf_page_indices_zero_based.balance],[1,2]);
 const annuals={FY2025:[229967,128765,281649,265462,4417906,126830,4291076],
                FY2024:[244824,134087,246118,228274,4277008,128474,4148534]};
 for(const [year,expected] of Object.entries(annuals)){
  const i=x.income[year],b=x.balance[year];
  assert.deepEqual([i.revenue,i.gross_profit,i.profit_before_tax,i.profit_after_tax,
   b.total_assets,b.total_liabilities,b.net_assets],expected);
  assert.equal(b.total_assets-b.total_liabilities,b.net_assets);
  assert.equal(b.net_assets,b.total_equity);
  assert.ok(i.revenue>i.gross_profit);
 }
 return true;
}
check(d,f,seed);
for(const mutate of [
 (d,f,s)=>{d.balance.FY2025.total_assets++},
 (d,f,s)=>{d.balance.FY2024.net_assets++},
 (d,f,s)=>{d.parent_attributable_profit_from_this_staging_verified=true},
 (d,f,s)=>{d.pdf_sha256="f".repeat(64)},
 (d,f,s)=>{d.financial_feed_registered=true},
 (d,f,s)=>{d.income.FY2025.profit_after_tax=281649},
 (d,f,s)=>{f.ranking_eligible_count=1},
 (d,f,s)=>{s.rows=s.rows.filter(r=>r.symbol!=="H02")}
]){
 const a=structuredClone(d),b=structuredClone(f),c=structuredClone(seed);
 mutate(a,b,c);assert.throws(()=>check(a,b,c));
}
console.log("v208 PASS: H02 audited FY2025/24 group balance sums and income labels; no verified parent-profit or valuation promotion");
