/* v133: FY2025 auditor opinion display distinct from current ranking checks. */
"use strict";
(function(root){
 const TYPES=["G13","S63"];
 function validate(feed,assurance){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_eligible_count!==0||feed.ranking_enabled!==false||
     !Array.isArray(feed.records)||feed.records.length!==7||
     !assurance||assurance.schema_version!=="sgx-fy2025-audit-assurance-v132"||
     assurance.linked_published_feed_updated_at_utc!==feed.updated_at_utc||
     assurance.external_auditor_fy2025_opinion_confirmed_count!==2||
     assurance.numeric_recalculation_completed_count!==0||
     assurance.ranking_eligible_count!==0||assurance.financial_feed_modified!==false||
     assurance.external_auditor_opinion_is_not_live_market_verification!==true||
     !Array.isArray(assurance.records)||assurance.records.length!==2)
    throw Error("独立監査資料と公開データの版が一致しない");
  const output=[];
  for(const symbol of TYPES){
   const entry=assurance.records.filter(x=>x.symbol===symbol);
   const published=feed.records.filter(x=>x.symbol===symbol);
   if(entry.length!==1||published.length!==1)throw Error("Issuer mismatch");
   const a=entry[0],f=published[0];
   if(a.fiscal_year!==2025||f.fiscal_year!==2025||
      a.independent_external_audit_opinion_observed!==true||
      a.auditor!=="PricewaterhouseCoopers LLP"||
      a.auditor_scope_end!=="2025-12-31"||
      a.annual_report_primary_source_url!==f.financial_source_url||
      a.annual_report_primary_sha256!==f.financial_pdf_sha256||
      a.reperformed_independent_financial_calculations!==false||
      a["2026_interim_audited_by_same_fy2025_opinion"]!==false||
      a.current_shares_and_quote_independently_verified!==false||
      a.parent_equity_independently_reperformed!==false||
      a.eligible_for_ranking!==false||f.ranking_eligible!==false)
     throw Error("Audit opinion claim not supported");
   output.push({symbol,auditor:"PwC",period:"2025年12月期",
     status:"外部監査意見を確認",
     limitation:"2026年業績・最新株価・株式数・投資ランキングは未検証",
     source:a.annual_report_primary_source_url});
  }
  return output;
 }
 async function render(){
  const body=document.getElementById("externalAuditRows");
  const message=document.getElementById("externalAuditMessage");
  if(!body||!message)return;
  try {
   const [feed,assurance]=await Promise.all([
     "./data/latest.json","./data/sgx-fy2025-audit-assurance-v132.json"
   ].map(async path=>{
    const response=await fetch(path,{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    return response.json();
   }));
   const rows=validate(feed,assurance);
   body.replaceChildren();
   for(const x of rows){
    const tr=document.createElement("tr");
    for(const label of [x.symbol,x.period,x.auditor,x.status,x.limitation]){
     const td=document.createElement("td");td.textContent=label;tr.append(td);
    }
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=x.source;a.textContent="SGX年次報告";a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);body.append(tr);
   }
   message.textContent="G13・S63の2025年度の外部監査意見のみ検証済み。監査意見は2026年の速報数値・株価・最新株式数を保証しない。";
  }catch(error){
   body.replaceChildren();const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="出典の版が一致しないため非表示。";
   tr.append(td);body.append(tr);
   message.textContent="監査原本との照合待ち。古い診断は表示しない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
