"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const proof=JSON.parse(fs.readFileSync("docs/data/sgx-two-document-crosscheck-v238.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-group-statement-v208.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const annual=JSON.parse(fs.readFileSync("docs/data/sgx-annual-report-sha-v237.json","utf8"));
const original=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
// v240: immutable observed original-PDF identity. Intentional source replacement
// requires reviewing a NEW provenance version, never silent sidecar substitution.
const sourcePins=Object.freeze({
 H02:Object.freeze({
  issuer:"Haw Par Corporation Limited",
  annualSha:"75328b273799863390e35a626e8e3679fe79ab853ef0a00f2775dd159364cfb8", annualBytes:4754838,
  resultSha:"94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5",resultBytes:706174,
  annualUrl:"https://links.sgx.com/FileOpen/Haw%20Par%20Corp%20Annual%20Report%202025.ashx?App=Announcement&FileID=881713",
  resultUrl:"https://links.sgx.com/1.0.0/corporate-announcements/R2V7WFBB9WQMBBP4/876566_FY25%20Haw%20Par%20SGX%20Announcementl.pdf"
 }),
 V03:Object.freeze({
  issuer:"Venture Corporation Limited",
  annualSha:"eaebb6f4192ceb478c819b991eb18a3c34e43bf573388b9098b5e48b73b26a97",annualBytes:8502570,
  resultSha:"b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794",resultBytes:520231,
  annualUrl:"https://links.sgx.com/FileOpen/VCL_Annual_Report_2025.ashx?App=Announcement&FileID=881699",
  resultUrl:"https://links.sgx.com/1.0.0/corporate-announcements/G8XZA2TO5M07X8S0/876221_Venture%20FY2025%20Financial%20Results.pdf"
 })
});
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
  const ar=a.records.filter(x=>x.symbol===symbol);
  const fr=o.records.filter(x=>x.symbol===symbol);
  assert.equal(ar.length,1,"exactly one annual source for "+symbol);
  assert.equal(fr.length,1,"exactly one results source for "+symbol);
  assert.equal(ar[0].source_report_retrieved_and_hashed,true);
  assert.equal(fr[0].source_pdf_byte_digest_calculated,true);
  assert.match(ar[0].sha256,/^[a-f0-9]{64}$/);
  assert.match(fr[0].sha256,/^[a-f0-9]{64}$/);
  assert.notEqual(ar[0].sha256,fr[0].sha256,"annual and results source must be distinct");
  assert.ok(ar[0].bytes>0&&fr[0].byte_length>0);
  assert.ok(ar[0].source_url.startsWith("https://links.sgx.com/"));
  assert.ok(fr[0].pdf_url.startsWith("https://links.sgx.com/"));
  assert.equal(ar[0].issuer_numerical_audit_independently_verified,false);
  assert.equal(fr[0].independent_financial_numeric_verification,false);
  const pinned=sourcePins[symbol];
  assert.equal(row.issuer,pinned.issuer,"proof issuer identity drift");
  assert.equal(ar[0].issuer,pinned.issuer,"annual issuer identity drift");
  assert.equal(fr[0].issuer,pinned.issuer,"results issuer identity drift");
  assert.equal(ar[0].sha256,pinned.annualSha,"annual official PDF digest drift");
  assert.equal(ar[0].bytes,pinned.annualBytes,"annual official PDF length drift");
  assert.equal(ar[0].source_url,pinned.annualUrl,"annual official URL drift");
  assert.equal(fr[0].sha256,pinned.resultSha,"results official PDF digest drift");
  assert.equal(fr[0].byte_length,pinned.resultBytes,"results official PDF length drift");
  assert.equal(fr[0].pdf_url,pinned.resultUrl,"results official URL drift");
  for(const [year,fields] of Object.entries(row.fields)){
   const ref=symbol==="H02"?
    {revenue:h.income[year].revenue,gross_profit:h.income[year].gross_profit,
     profit_after_tax:h.income[year].profit_after_tax,total_assets:h.balance[year].total_assets,total_liabilities:h.balance[year].total_liabilities,total_equity:h.balance[year].total_equity}:
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
 (d,h,v,a,o,f)=>{a.records[0].symbol="V03"},
 (d,h,v,a,o,f)=>{o.records[1].symbol="H02"},
 (d,h,v,a,o,f)=>{a.records[1].sha256="bad-digest"},
 (d,h,v,a,o,f)=>{o.records[0].byte_length=0},
 (d,h,v,a,o,f)=>{a.records[0].issuer_numerical_audit_independently_verified=true},
 (d,h,v,a,o,f)=>{a.records[0].sha256=o.records[0].sha256},
 (d,h,v,a,o,f)=>{a.records[0].sha256="a".repeat(64)},
 (d,h,v,a,o,f)=>{a.records[1].bytes++},
 (d,h,v,a,o,f)=>{o.records[1].pdf_url=o.records[0].pdf_url},
 (d,h,v,a,o,f)=>{o.records[0].issuer="Venture Corporation Limited"},
 (d,h,v,a,o,f)=>{d.records[0].issuer="Venture Corporation Limited"},
 (d,h,v,a,o,f)=>{f.ranking_eligible_count=1}
]){
 const args=[proof,h02,v03,annual,original,feed].map(x=>structuredClone(x));
 change(...args);assert.throws(()=>verify(...args));
}
console.log("v238 PASS: two H02/V03 FY-year transcriptions reconcile exactly with prior issuer results, arithmetic and SHA-provenance; independent gate remains false");
