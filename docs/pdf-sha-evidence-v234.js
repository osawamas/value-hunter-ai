/* v234 source-PDF byte-level provenance display, NOT an audit certification. */
"use strict";
(function(root){
 function validate(data,h02,v03,feed){
  if(data?.schema_version!=="sgx-original-issuer-pdf-sha-evidence-v233"||
     data.source_pdf_sha256_from_raw_sgx_bytes!==true||
     data.sha256_matches_between_two_separate_github_actions_runs_for_both_symbols!==true||
     data.independent_second_github_actions_fetch_same_bytes!==true||
     data.external_independent_numeric_audit_completed!==false||
     data.ranking_enabled!==false||data.ranking_eligible_count!==0||
     data.financial_feed_modified!==false||!Array.isArray(data.records)||
     data.records.length!==2||!Array.isArray(data.repeated_independent_download_runs)||
     data.repeated_independent_download_runs.length!==2||
     h02?.schema_version!=="sgx-h02-official-primary-document-v212"||
     v03?.schema_version!=="sgx-v03-official-primary-statements-v213"||
     feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)
   throw Error("Source PDF provenance not independently ready");
  const expected=[
   {symbol:"H02",sha:"94ad135079c4da21a1c7f22a3dd07807cf21b406873d9414d283a3a25753acb5",
    size:706174,url:h02.original_pdf_url},
   {symbol:"V03",sha:"b1043821f0a335f1d660fa8603aa1bb6b5ca3178fcd32439a1cea699174a5794",
    size:520231,url:v03.primary_pdf_url}
  ];
  if(data.repeated_independent_download_runs.map(x=>x.workflow_run_id).join(",")!=="43598869441,43603411759")
    throw Error("External verification run identifiers changed");
  return expected.map(e=>{
   const matches=data.records.filter(x=>x.symbol===e.symbol);
   if(matches.length!==1)throw Error("Original PDF evidence missing");
   const r=matches[0];
   if(r.sha256!==e.sha||r.byte_length!==e.size||
      r.pdf_url!==e.url||r.source_pdf_byte_digest_calculated!==true||
      r.independent_financial_numeric_verification!==false||
      r.licensed_timestamped_quote_verified!==false||
      r.ranking_eligible!==false)
    throw Error("Original PDF source, digest or gating changed");
   return {symbol:e.symbol,sha:e.sha,bytes:e.size,
    source:e.url,independent_numeric_audit:false,
    valid_original_bytes_digest:true,ranking_eligible:false};
  });
 }
 // v248: combine results releases, annual reports, and real GitHub Actions replay.
 function validateExpanded(results,h02,v03,annual,replay,feed){
  const releases=validate(results,h02,v03,feed);
  if(annual?.schema_version!=="sgx-h02-v03-annual-original-pdf-sha-v237"||
     !Array.isArray(annual.records)||annual.records.length!==2||
     annual.external_independent_numeric_verification_complete!==false||
     annual.ranking_eligible_count!==0||
     replay?.schema_version!=="sgx-four-original-pdf-live-replay-evidence-v248"||
     replay.github_run_id!==43614340513||
     replay.github_job_id!==132506000885||
     replay.github_artifact_id!==14121073878||
     replay.github_url!=="https://github.com/osawamas/value-hunter-ai/actions/runs/43614340513"||
     replay.source_pdf_sha256_recomputed_in_real_actions!==true||
     replay.matching_original_pdf_count!==4||
     replay.financial_fields_independently_recalculated!==false||
     replay.independent_external_financial_audit_complete!==false||
     replay.licensed_timed_quote_verified!==false||
     replay.current_outstanding_shares_verified!==false||
     replay.rankings_enabled!==false||
     replay.ranking_eligible_count!==0||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0)
   throw Error("SGX original PDF replay evidence incomplete");
  const expected=[
   {symbol:"H02",sha:"75328b273799863390e35a626e8e3679fe79ab853ef0a00f2775dd159364cfb8",bytes:4754838},
   {symbol:"V03",sha:"eaebb6f4192ceb478c819b991eb18a3c34e43bf573388b9098b5e48b73b26a97",bytes:8502570}
  ];
  const yearly=expected.map(x=>{
   const recs=annual.records.filter(r=>r.symbol===x.symbol);
   if(recs.length!==1)throw Error("Duplicate or missing annual SGX document");
   const r=recs[0];
   if(r.sha256!==x.sha||r.bytes!==x.bytes||
      r.source_report_retrieved_and_hashed!==true||
      r.issuer_numerical_audit_independently_verified!==false||
      r.ranking_eligible!==false||
      !/^https:\/\/links\.sgx\.com\//.test(r.source_url))
    throw Error("SGX annual PDF digest mismatch");
   return {symbol:x.symbol,kind:"年次報告書 FY2025",sha:x.sha,bytes:x.bytes,
     source:r.source_url,independent_numeric_audit:false,ranking_eligible:false};
  });
  return [
   ...releases.map(x=>({...x,kind:"通期決算発表 FY2025"})),
   ...yearly
  ];
 }
 async function render(){
  const table=document.getElementById("issuerPdfDigestRows");
  const status=document.getElementById("issuerPdfDigestStatus");
  if(!table||!status)return;
  try{
   const sources=[
    "./data/sgx-original-pdf-sha-v233.json",
    "./data/sgx-h02-primary-filing-v212.json",
    "./data/sgx-v03-primary-statements-v213.json",
    "./data/sgx-annual-report-sha-v237.json",
    "./data/sgx-four-pdf-replay-evidence-v248.json",
    "./data/latest.json"
   ];
   const items=await Promise.all(sources.map(async path=>{
    const response=await fetch(path,{cache:"no-store"});
    if(!response.ok)throw Error("PDF provenance fetch "+response.status);
    return response.json();
   }));
   const rows=validateExpanded(...items),frag=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    const values=[r.symbol+" / "+r.kind,r.bytes.toLocaleString("ja-JP"),r.sha,"2026/11/15 4原本再取得一致","未完了"];
    for(const [i,value] of values.entries()){const td=document.createElement("td");td.textContent=i===2?r.sha.slice(0,14)+"…"+r.sha.slice(-12):value;if(i===2)td.title=r.sha;tr.append(td);}
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=r.source;a.textContent="SGX原本";a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);frag.append(tr);
   }
   table.replaceChildren(frag);
   status.textContent="H02・V03の決算発表2件と年次報告書2件、計4件のSGX原本PDFを2026年11月15日にGitHub Actionsで再取得。SHA-256とサイズが以前の記録と一致。会計数値の独立監査ではなく、ランキングは無効。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="SHA-256の照合ができないため非表示";
   tr.append(td);table.replaceChildren(tr);status.textContent="原本のバイト証拠の再照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate,validateExpanded};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
