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
 async function render(){
  const table=document.getElementById("issuerPdfDigestRows");
  const status=document.getElementById("issuerPdfDigestStatus");
  if(!table||!status)return;
  try{
   const sources=[
    "./data/sgx-original-pdf-sha-v233.json",
    "./data/sgx-h02-primary-filing-v212.json",
    "./data/sgx-v03-primary-statements-v213.json",
    "./data/latest.json"
   ];
   const items=await Promise.all(sources.map(async path=>{
    const response=await fetch(path,{cache:"no-store"});
    if(!response.ok)throw Error("PDF provenance fetch "+response.status);
    return response.json();
   }));
   const rows=validate(...items),frag=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    const values=[r.symbol,r.bytes.toLocaleString("ja-JP"),r.sha,"GitHub Actions 2回一致","未完了"];
    for(const [i,value] of values.entries()){const td=document.createElement("td");td.textContent=i===2?r.sha.slice(0,14)+"…"+r.sha.slice(-12):value;if(i===2)td.title=r.sha;tr.append(td);}
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=r.source;a.textContent="SGX原本";a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);frag.append(tr);
   }
   table.replaceChildren(frag);
   status.textContent="H02・V03のSGX原本PDFは、2回のActions実行でファイルサイズとSHA-256が一致。これは原本バイト照合であり、第三者による会計数値の独立監査・最新株価/株式数の検証ではない。正式ランキングは無効。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="SHA-256の照合ができないため非表示";
   tr.append(td);table.replaceChildren(tr);status.textContent="原本のバイト証拠の再照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
