"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const evidence=JSON.parse(fs.readFileSync("docs/data/sgx-original-pdf-sha-v233.json","utf8"));
const h02=JSON.parse(fs.readFileSync("docs/data/sgx-h02-primary-filing-v212.json","utf8"));
const v03=JSON.parse(fs.readFileSync("docs/data/sgx-v03-primary-statements-v213.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function validate(x,h,v,f){
 assert.equal(x.schema_version,"sgx-original-issuer-pdf-sha-evidence-v233");
 assert.equal(x.evidence_origin,"GITHUB_ACTIONS_ORIGINAL_PDF_PROBE_ARTIFACT");
 assert.equal(x.github_workflow_run_id,43603411759);
 assert.equal(x.github_workflow_job_id,132472814864);
 assert.equal(x.github_artifact_id,14117450791);
 assert.equal(x.github_commit_sha,"a79e6d28e842528e35583211f0200f44b5ead3e8");
 assert.equal(x.original_pdf_bytes_preserved_in_repository,false);
 assert.equal(x.source_pdf_sha256_from_raw_sgx_bytes,true);
 assert.equal(x.source_pdf_retrieval_via_allowed_sgx_redirects,true);
 assert.equal(x.independent_second_github_actions_fetch_same_bytes,true);
 assert.equal(x.sha256_matches_between_two_separate_github_actions_runs_for_both_symbols,true);
 assert.equal(x.repeated_independent_download_runs.length,2);
 assert.deepEqual(x.repeated_independent_download_runs.map(z=>z.workflow_run_id),
  [43598869441,43603411759]);
 assert.deepEqual(x.repeated_independent_download_runs.map(z=>z.artifact_id),
  [14115445847,14117450791]);
 assert.equal(x.financial_feed_modified,false);
 assert.equal(x.external_independent_numeric_audit_completed,false);
 assert.equal(x.ranking_enabled,false);
 assert.equal(x.ranking_eligible_count,0);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(x.records.length,2);
 const expected={
  H02:{hash:"94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5",bytes:706174,
   url:h.original_pdf_url,reference:h.announcement_reference},
  V03:{hash:"b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794",bytes:520231,
   url:v.primary_pdf_url,reference:v.announcement_reference}
 };
 for(const symbol of ["H02","V03"]){
  const a=x.records.filter(z=>z.symbol===symbol);
  assert.equal(a.length,1);
  const z=a[0],e=expected[symbol];
  assert.equal(z.ann_ref,e.reference);
  assert.equal(z.pdf_url,e.url);
  assert.equal(z.sha256,e.hash);
  assert.match(z.sha256,/^[0-9a-f]{64}$/);
  assert.equal(z.byte_length,e.bytes);
  assert.equal(z.source_pdf_byte_digest_calculated,true);
  assert.equal(z.independent_financial_numeric_verification,false);
  assert.equal(z.current_issued_ex_treasury_shares_verified,false);
  assert.equal(z.licensed_timestamped_quote_verified,false);
  assert.equal(z.ranking_eligible,false);
  assert.match(z.fetched_final_url,/^https:\/\/links\.sgx\.com\/FileOpen\//);
  assert.ok(!f.records.some(record=>record.symbol===symbol));
 }
 // v212/v213 remain historical research snapshots; overlay is later evidence.
 assert.equal(h.source_pdf_sha256,null);
 assert.equal(v.original_pdf_sha256,null);
 return true;
}
validate(evidence,h02,v03,feed);
for(const edit of [
 (x,h,v,f)=>{x.records[0].sha256="f".repeat(64)},
 (x,h,v,f)=>{x.records[1].byte_length++},
 (x,h,v,f)=>{x.records[0].pdf_url="https://example.com/false.pdf"},
 (x,h,v,f)=>{x.repeated_independent_download_runs.pop()},
 (x,h,v,f)=>{x.external_independent_numeric_audit_completed=true},
 (x,h,v,f)=>{x.records[1].ranking_eligible=true},
 (x,h,v,f)=>{f.ranking_eligible_count=1}
]){
 const x=structuredClone(evidence),a=structuredClone(h02),
 b=structuredClone(v03),f=structuredClone(feed);
 edit(x,a,b,f);assert.throws(()=>validate(x,a,b,f));
}
console.log("v233 PASS: H02/V03 exact original SGX PDF bytes and SHA256 corroborated across 2 Actions runs without ranking promotion");
