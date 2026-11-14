/* v214: primary issuer annual balance reconciliation display; not a valuation feed */
"use strict";
(function(root){
 function validate(feed,h02,v03){
  if(feed?.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     feed.coverage?.registered_count!==7||
     h02?.schema_version!=="sgx-h02-official-primary-document-v212"||
     v03?.schema_version!=="sgx-v03-official-primary-statements-v213"||
     h02.period_end!=="2025-12-31"||v03.period_end!=="2025-12-31"||
     h02.source_pdf_page_images_reviewed!==true||
     v03.source_pdf_page_images_reviewed!==true||
     h02.source_pdf_sha256!==null||v03.original_pdf_sha256!==null||
     h02.full_external_independent_numeric_audit_completed!==false||
     v03.independent_auditor_external_source_verified!==false||
     h02.ranking_eligible!==false||v03.ranking_eligible!==false||
     feed.records.some(x=>["H02","V03"].includes(x.symbol)))
   throw Error("Primary issuer source gating changed");
  const hp=h02.verified_from_primary_pdf_visual.balance_FY2025;
  if(hp.net_assets!==hp.total_equity||
     hp.total_assets-hp.total_liabilities!==hp.net_assets)
    throw Error("H02 net-asset reconciliation mismatch");
  const vp=v03.group.FY2025;
  const rows=[
   {symbol:"H02",issuer:"Haw Par",assets:hp.total_assets,
    liabilities:hp.total_liabilities,parent_equity:hp.total_equity,
    noncontrolling_equity:null,total_equity:hp.total_equity,
    group_profit:h02.verified_from_primary_pdf_visual.income_FY2025.profit_after_tax,
    owner_profit:null,source:h02.original_pdf_url},
   {symbol:"V03",issuer:"Venture",assets:vp.assets,
    liabilities:vp.current_liabilities+vp.noncurrent_liabilities,
    parent_equity:vp.parent_equity,noncontrolling_equity:vp.noncontrolling_equity,
    total_equity:vp.total_equity,group_profit:vp.profit_for_year,
    owner_profit:vp.profit_attributable_to_owners,source:v03.primary_pdf_url}
  ];
  const expected={
    H02:[4417906,126830,4291076,null,4291076,265462,null],
    V03:[3602219,804386,2792741,5092,2797833,227635,226958]
  };
  for(const x of rows){
   const vals=[x.assets,x.liabilities,x.parent_equity,x.noncontrolling_equity,
    x.total_equity,x.group_profit,x.owner_profit];
   if(JSON.stringify(vals)!==JSON.stringify(expected[x.symbol])||
      x.assets!==x.liabilities+x.total_equity||
      (x.noncontrolling_equity!==null&&x.total_equity!==x.parent_equity+x.noncontrolling_equity))
    throw Error("Issuer financial reconciliation mismatch");
  }
  return rows;
 }
 async function render(){
  const body=document.getElementById("primaryIssuerReconciliationRows");
  const status=document.getElementById("primaryIssuerReconciliationStatus");
  if(!body||!status)return;
  try{
   const input=await Promise.all(
    ["./data/latest.json","./data/sgx-h02-primary-filing-v212.json",
     "./data/sgx-v03-primary-statements-v213.json"].map(async p=>{
      const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
     }));
   const rows=validate(...input),frag=document.createDocumentFragment();
   for(const x of rows){
    const tr=document.createElement("tr");
    for(const v of [x.symbol,x.assets,x.liabilities,x.parent_equity,
        x.noncontrolling_equity,x.total_equity,x.group_profit,x.owner_profit]){
     const td=document.createElement("td");
     td.textContent=v===null?"未分離":typeof v==="number"?v.toLocaleString("ja-JP"):v;
     tr.append(td);
    }
    const td=document.createElement("td"),a=document.createElement("a");
    a.href=x.source;a.target="_blank";a.rel="noopener noreferrer";
    a.textContent="SGX原本";td.append(a);tr.append(td);frag.append(tr);
   }
   body.replaceChildren(frag);
   status.textContent="単位：千SGD、FY2025。H02のグループ利益とV03の親会社帰属利益は別指標。原本ページ目視確認・貸借算術一致までで、原本SHA取得と独立財務検証・最新株式数・株価利用許可は未完。正式ランキング対象外。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=9;td.textContent="原本財務の照合状態が変わったため非表示";
   tr.append(td);body.replaceChildren(tr);status.textContent="原本照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
