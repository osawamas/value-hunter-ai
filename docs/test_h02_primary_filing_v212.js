"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const data=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const prior=JSON.parse(fs.readFileSync("docs/data/sgx-h02-group-statement-v208.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const script=fs.readFileSync("scripts/probe-issuer-financial-pdf-v210.js","utf8");
function verify(d,p,f,s){
 assert.equal(d.schema_version,"sgx-h02-official-primary-document-v212");
 assert.equal(d.symbol,"H02");
 assert.equal(d.isin,"SG1D25001158");
 assert.equal(d.announcement_reference,"SG260227OTHRQ304");
 assert.equal(d.broadcast_sgt,"2026-02-27T17:23:27+08:00");
 assert.equal(d.period_end,"2025-12-31");
 assert.equal(d.original_pdf_total_pages,25);
 assert.deepEqual(d.source_pages_zero_based,{income:1,balance:2});
 assert.equal(d.source_pdf_page_images_reviewed,true);
 assert.equal(d.source_pdf_sha256,null);
 assert.equal(d.source_pdf_bytes_independently_downloaded,false);
 assert.equal(d.full_external_independent_numeric_audit_completed,false);
 assert.equal(d.authorized_timestamped_quote_verified,false);
 assert.equal(d.ranking_eligible,false);
 assert.equal(d.financial_feed_modified,false);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.ok(!f.records.some(r=>r.symbol==="H02"));
 assert.ok(s.includes(d.original_pdf_url));
 assert.match(d.original_pdf_url,/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/R2V7WFBB9WQMBBP4\//);
 assert.equal(d.verified_from_primary_pdf_visual.unit,p.unit);
 const i=d.verified_from_primary_pdf_visual.income_FY2025;
 const b=d.verified_from_primary_pdf_visual.balance_FY2025;
 assert.deepEqual([i.revenue,i.gross_profit,i.profit_before_tax,i.profit_after_tax],
 [p.income.FY2025.revenue,p.income.FY2025.gross_profit,p.income.FY2025.profit_before_tax,p.income.FY2025.profit_after_tax]);
 assert.deepEqual([b.total_assets,b.total_liabilities,b.net_assets,b.total_equity],
 [p.balance.FY2025.total_assets,p.balance.FY2025.total_liabilities,p.balance.FY2025.net_assets,p.balance.FY2025.total_equity]);
 assert.deepEqual(d.verified_from_primary_pdf_visual.balance_FY2024,p.balance.FY2024);
 assert.equal(b.total_assets-b.total_liabilities,b.net_assets);
 assert.equal(d.comparison_document_is_another_issuer_document_not_independent_auditor,true);
 return true;
}
verify(data,prior,feed,script);
for(const change of [
 (d,p,f,s)=>{d.source_pdf_sha256="a".repeat(64)},
 (d,p,f,s)=>{d.full_external_independent_numeric_audit_completed=true},
 (d,p,f,s)=>{d.verified_from_primary_pdf_visual.balance_FY2025.total_assets++},
 (d,p,f,s)=>{d.source_pages_zero_based.balance=3},
 (d,p,f,s)=>{d.announcement_reference="INVALID"},
 (d,p,f,s)=>{d.ranking_eligible=true},
 (d,p,f,s)=>{f.ranking_eligible_count++}
]){
 const d=structuredClone(data),p=structuredClone(prior),f=structuredClone(feed);
 change(d,p,f,script);assert.throws(()=>verify(d,p,f,script));
}
console.log("v212 PASS: H02 official SGX filing visual financial evidence matches v208; PDF digest and independent audit remain unknown");
