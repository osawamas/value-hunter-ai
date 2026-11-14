"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const proof=JSON.parse(fs.readFileSync("docs/data/sgx-two-document-crosscheck-v238.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-group-statement-v208.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const annual=JSON.parse(fs.readFileSync("docs/data/sgx-annual-report-sha-v237.json","utf8"));
const original=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function verify(d,h,v,a,o,f){
 assert.equal(d.schema_version,"sgx-issuer-fy2025-two-document-figure-reconciliation-v238");
 assert.equal(d.financial_period_end,"2025-12-31");
 assert.equal(d.reporting_unit,"SGD_thousands");
 assert.equal(d.research_scope,"SAME_ISSUER_FULL_YEAR_RELEASE_VS_ISSUER_ANNUAL_REPORT");
 assert.equal(d.same_issuer_documents_not_independent_external_data_validation,true);
 assert.equal(d.file_sha_is_not_accounting_assurance,true);
 assert.equal(d.external_independent_auditor_numeric_recalculation_completed,false);
 assert.equal(d.registered_financial_feed_modified,false);
 assert.equal(d.ranking_eligible_count,0);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.equal(d.records.length,2);assert.equal(a.records.length,2);assert.equal(o.records.length,2);
 for(const symbol of ["H02","V03"]){
  const row=d.records.find(x=>x.symbol===symbol);
  assert.ok(row);assert.equal(row.annual_source,"docs/data/sgx-annual-report-sha-v237.json");
  assert.equal(row.interim_source,"docs/data/sgx-original-pdf-sha-v233.json");
  assert.equal(row.accounting_scope.startsWith("CONSOLIDATED_GROUP"),true);
  assert.equal(row.source_figure_values_match_between_issuer_documents,true);
  assert.equal(row.independent_external_numeric_audit_complete,false);
  assert.equal(row.ranking_eligible,false);
  assert.ok(a.records.some(x=>x.symbol===symbol&&x.source_report_retrieved_and_hashed===true));
  assert.ok(o.records.some(x=>x.symbol===symbol&&x.source_pdf_byte_digest_calculated===true));
  for(const [year,fields] of Object.entries(row.fields)){
   const ref=symbol==="H02"?
    {revenue:h.income[year].revenue,gross_profit:h.income[year].gross_profit,
     profit_after_tax:h.income[year].profit_after_tax,...h.balance[year]}:
    {revenue:v.group[year].revenue,profit_before_tax:v.group[year].profit_before_tax,
     profit_for_year:v.group[year].profit_for_year,
     profit_attributable_to_owners:v.group[year].profit_attributable_to_owners,
     profit_attributable_to_nci:v.group[year].profit_attributable_to_nci,
     total_assets:v.group[year].assets,current_liabilities:v.group[year].current_liabilities,
     noncurrent_liabilities:v.group[year].noncurrent_liabilities,
     parent_equity:v.group[year].parent_equity,
     noncontrolling_equity:v.group[year].noncontrolling_equity,
     total_equity:v.group[year].total_equity};
   assert.deepEqual(fields,ref,symbol+" "+year+" differs from earlier issuer PDF transcription");
   if(symbol==="H02"){
    assert.equal(fields.total_assets-fields.total_liabilities,fields.total_equity);
    assert.equal(row.issuer_parent_equity_separately_authenticated,false);
   }else{
    assert.equal(fields.total_assets-fields.current_liabilities-fields.noncurrent_liabilities,fields.total_equity);
    assert.equal(fields.parent_equity+fields.noncontrolling_equity,fields.total_equity);
    assert.equal(fields.profit_attributable_to_owners+fields.profit_attributable_to_nci,fields.profit_for_year);
    assert.equal(row.issuer_parent_equity_separately_authenticated,true);
   }
  }
 }
 return true;
}
verify(proof,h02,v03,annual,original,feed);
for(const change of [
 (d,h,v,a,o,f)=>{d.records[0].fields.FY2025.total_equity++},
 (d,h,v,a,o,f)=>{d.records[1].fields.FY2024.noncontrolling_equity++},
 (d,h,v,a,o,f)=>{d.records[1].fields.FY2025.profit_attributable_to_nci++},
 (d,h,v,a,o,f)=>{d.records[0].issuer_parent_equity_separately_authenticated=true},
 (d,h,v,a,o,f)=>{d.external_independent_auditor_numeric_recalculation_completed=true},
 (d,h,v,a,o,f)=>{d.ranking_eligible_count=1},
 (d,h,v,a,o,f)=>{a.records[0].source_report_retrieved_and_hashed=false},
 (d,h,v,a,o,f)=>{f.ranking_eligible_count=1}
]){
 const args=[proof,h02,v03,annual,original,feed].map(x=>structuredClone(x));
 change(...args);assert.throws(()=>verify(...args));
}
console.log("v238 PASS: two H02/V03 FY-year transcriptions reconcile exactly with prior issuer results, arithmetic and SHA-provenance; independent gate remains false");
