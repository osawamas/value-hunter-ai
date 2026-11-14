"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const d=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const old=JSON.parse(fs.readFileSync("docs/data/sgx-v03-balance-v209.json","utf8"));
const f=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const probe=fs.readFileSync("scripts/probe-issuer-financial-pdf-v210.js","utf8");
function check(x,r,feed,script){
 assert.equal(x.schema_version,"sgx-v03-official-primary-statements-v213");
 assert.equal(x.symbol,"V03");
 assert.equal(x.isin,"SG0531000230");
 assert.equal(x.announcement_reference,"SG260226OTHRP753");
 assert.equal(x.period_end,"2025-12-31");
 assert.equal(x.reporting_unit,"SGD_thousands");
 assert.equal(x.primary_pdf_pages,13);
 assert.deepEqual(x.primary_pdf_visual_pages_zero_based,{income:0,balance:2});
 assert.equal(x.source_pdf_page_images_reviewed,true);
 assert.equal(x.original_pdf_sha256,null);
 assert.equal(x.original_pdf_bytes_downloaded,false);
 assert.equal(x.second_issuer_document_not_independent_numerical_audit,true);
 assert.equal(x.noncontrolling_equity_from_official_line_now_visually_matched,true);
 assert.equal(x.independent_auditor_external_source_verified,false);
 assert.equal(x.official_current_ex_treasury_shares_verified,false);
 assert.equal(x.timestamped_licensed_quote_verified,false);
 assert.equal(x.financial_feed_modified,false);
 assert.equal(x.ranking_eligible,false);
 assert.equal(feed.ranking_enabled,false);
 assert.equal(feed.ranking_eligible_count,0);
 assert.ok(!feed.records.some(y=>y.symbol==="V03"));
 assert.ok(script.includes(x.primary_pdf_url));
 for(const year of ["FY2025","FY2024"]){
  const a=x.group[year],h=r.historical[year];
  assert.equal(a.profit_for_year,a.profit_attributable_to_owners+a.profit_attributable_to_nci);
  assert.equal(a.total_equity,a.parent_equity+a.noncontrolling_equity);
  assert.equal(a.assets,a.current_liabilities+a.noncurrent_liabilities+a.total_equity);
  for(const [rounded,exact] of [
   [h.revenue,a.revenue],[h.parent_profit,a.profit_attributable_to_owners],
   [h.assets,a.assets],[h.liabilities,a.current_liabilities+a.noncurrent_liabilities],
   [h.parent_equity,a.parent_equity]
  ])assert.ok(Math.abs(rounded-exact/1000)<=0.051);
 }
 assert.deepEqual([x.group.FY2025.noncontrolling_equity,x.group.FY2024.noncontrolling_equity],[5092,4511]);
 assert.deepEqual([x.group.FY2025.profit_attributable_to_owners,x.group.FY2024.profit_attributable_to_owners],[226958,245029]);
 return true;
}
check(d,old,f,probe);
for(const edit of [
 (d,r,f,s)=>{d.group.FY2025.noncontrolling_equity++},
 (d,r,f,s)=>{d.group.FY2024.profit_attributable_to_nci++},
 (d,r,f,s)=>{d.group.FY2025.parent_equity++},
 (d,r,f,s)=>{d.original_pdf_bytes_downloaded=true},
 (d,r,f,s)=>{d.official_current_ex_treasury_shares_verified=true},
 (d,r,f,s)=>{d.ranking_eligible=true},
 (d,r,f,s)=>{f.ranking_eligible_count++},
 (d,r,f,s)=>{r.historical.FY2025.parent_equity++}
]){
 const a=structuredClone(d),b=structuredClone(old),c=structuredClone(f);
 edit(a,b,c,probe);assert.throws(()=>check(a,b,c,probe));
}
console.log("v213 PASS: V03 official FY2025 and FY2024 audited-scope issuer results reconcile parent equity, NCI, total equity and profit");
