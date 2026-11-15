/* v286 OCBC issuer SGX-PDF vs independently downloaded issuer website:
 * both sources are the SAME issuer. Not an independent audit of statements.
 */
"use strict";
(function(root){
 function check(original,summary,feed){
  if(original?.schema_version!=="ocbc-3q26-issuer-website-corroboration-v286"||
     original.source_checks_passed!==true||
     original.symbol!=="O39"||
     original.period_end!=="2026-09-30"||
     original.website_html_bytes!==73374||
     original.website_html_sha256!=="feab3106bff1f5e769dec67fff50a9d5a28818c0aaae42b87663a622f2629370"||
     original.observed_workflow_url!=="https://github.com/osawamas/value-hunter-ai/actions/runs/43665855039"||
     original.independent_third_party_audit_complete!==false||
     original.source_precision_matches_exact_unrounded_figures!==false||
     original.investment_ranking_eligible!==false||
     original.share_count_current_verified!==false||
     original.quote_display_license_verified!==false||
     summary?.schema_version!=="sgx-big3-normalized-bank-quarters-v186"||
     summary.period_end!==original.period_end||
     summary.unit!=="SGD_millions"||
     summary.ranking_eligible!==false||
     feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0){
    throw Error("OCBC追加出典のSHA・会計期・検証状態に矛盾");
  }
  const e=summary.entries?.find(x=>x.symbol==="O39");
  if(!e||e.source!==original.sgx_filing_url||
     e.sha!==original.sgx_filing_sha256||
     !Array.isArray(original.metric_checks)||original.metric_checks.length!==4)
    throw Error("OCBC SGX元資料の会社・原本情報が異なる");
  const expect={
   "3Q26 net profit":e.q3profit,
   "9M26 net profit":e.nineprofit,
   "3Q26 net interest income":e.q3nii,
   "9M26 net interest income":e.ninenii
  };
  const seen=new Set();
  for(const m of original.metric_checks){
   if(!Object.prototype.hasOwnProperty.call(expect,m.metric)||
      seen.has(m.metric)||m.sgx_precision_millions!==expect[m.metric]||
      m.matched_to_rounded_precision!==true||
      !Number.isFinite(m.issuer_website_rounded_billions)||
      Math.abs(m.sgx_precision_millions-m.issuer_website_rounded_billions*1000)>5)
    throw Error("OCBC2026年数値が丸め幅に一致しない");
   seen.add(m.metric);
  }
  if(seen.size!==4)throw Error("OCBC 3Q/9M照合項目が不足");
  return {metrics:original.metric_checks,source:original.issuer_website_url,
    sgxSource:e.source,websiteSHA:original.website_html_sha256,
    independentAudit:false,currentPrices:false,rankingEligible:false};
 }
 const text=(tag,v)=>{const n=document.createElement(tag);n.textContent=String(v);return n;};
 async function render(){
  const body=document.getElementById("ocbcSecondIssuerSourceRows");
  const status=document.getElementById("ocbcSecondIssuerSourceStatus");
  if(!body||!status)return;
  try{
   const paths=[
    "./data/ocbc-3q26-issuer-website-corroboration-v286.json",
    "./data/sgx-big3-bank-research-v186.json",
    "./data/latest.json"];
   const files=await Promise.all(paths.map(async x=>{
    const res=await fetch(x,{cache:"no-store"});
    if(!res.ok)throw Error("HTTP "+res.status);
    return res.json();
   }));
   const verified=check(...files);
   const fragment=document.createDocumentFragment();
   for(const m of verified.metrics){
    const tr=document.createElement("tr");
    tr.append(text("td",m.metric),text("td",m.sgx_precision_millions.toLocaleString("ja-JP")),
     text("td",m.issuer_website_rounded_billions.toFixed(2)+" billion SGD"),
     text("td","同一発行体の別公開経路・丸め範囲一致"));
    fragment.append(tr);
   }
   body.replaceChildren(fragment);
   status.textContent="OCBC公式サイトの原本HTML（SHA-256照合済み）とSGX掲載の同社決算PDFの概数を照合。同じ発行体なので第三者の独立監査ではない。ランキング適格0社のまま。";
   for(const [id,url,sha] of [
    ["ocbcSecondIssuerWeb",verified.source,verified.websiteSHA],
    ["ocbcSecondIssuerSgx",verified.sgxSource,null]]){
    const anchor=document.getElementById(id);
    if(anchor){anchor.href=url;anchor.target="_blank";anchor.rel="noopener noreferrer";
     if(sha)anchor.title="原本HTML SHA-256："+sha;}
   }
  }catch{
   body.replaceChildren();
   const row=document.createElement("tr"),td=text("td","原本SHA・決算数値の照合不可。未検証の資料は表示しない。");
   td.colSpan=4;row.append(td);body.append(row);
   status.textContent="OCBC公式資料の照合を検証できないため非表示。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={check};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
