/* v169: Bank evidence coverage, not an annual/interim earnings comparison. */
"use strict";
(function(root) {
 function validate(feed, bundle) {
  if(feed?.schema_version!=="value_hunter_web_v29"||feed.ranking_enabled!==false||
    feed.ranking_eligible_count!==0||!Array.isArray(feed.records)||
    bundle?.schema_version!=="sgx-ocbc-bank-research-bundle-v166"||
    bundle.symbol!=="O39"||bundle.quarter_end!=="2026-09-30"||
    bundle.independent_third_party_financial_reperformance!==false||
    bundle.authenticated_current_exchange_quote_verified!==false||
    bundle.current_treasury_shares_verified!==false||
    bundle.per_pbr_and_ranking_permitted!==false||
    bundle["2026_interim_covered_by_fy2025_audit"]!==false||
    !/^[0-9a-f]{64}$/.test(bundle.sgx_original_pdf_sha256))
    throw Error("Bank evidence inconsistent");
  const banks={};
  for(const symbol of ["D05","O39","U11"]) {
    const rows=feed.records.filter(x=>x.symbol===symbol);
    if(rows.length!==1||rows[0].ranking_eligible!==false||
       rows[0].bank_financial_state?.status!=="AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"||
       rows[0].bank_financial_state.third_party_numerical_verification!==false||
       rows[0].bank_financial_state.current_quote_verified!==false)
      throw Error("Bank registration unverified");
    banks[symbol]=rows[0];
  }
  const dbs=banks.D05.banking_evidence;
  if(dbs?.status!=="BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED"||
     dbs.scope!=="GROUP_BANKING_NOT_INDUSTRIAL_FINANCIALS"||
     dbs.fiscal_year!==2025||dbs.unit!=="SGD_millions"||
     dbs.income?.["2025"]?.profit_attributable_to_parent!==10933||
     dbs.balance?.["2025"]?.parent_shareholders_funds!==68867||
     dbs.independent_cross_source_verification!==false||dbs.ranking_eligible!==false)
    throw Error("DBS audited issuer table mismatch");
  const q=bundle.income_statement_sgd_millions?.["3Q26"];
  if(q?.group_net_profit!==2042||
     bundle.bank_balance_2026_09_30_sgd_millions?.ordinary_equity!==60899||
     !/^https:\/\/links\.sgx\.com\//.test(bundle.sgx_original_pdf_url))
    throw Error("OCBC interim original mismatch");
  return [
   {symbol:"D05",name:"DBS",fy:"10,933",q3:"未照合",equity:"68,867（2025年末・親会社株主持分）",source:dbs.source_url,
    note:"FY2025発行会社資料・独立数値検証待ち"},
   {symbol:"O39",name:"OCBC",fy:"未照合",q3:"2,042",equity:"60,899（2026年9月末・普通株主持分）",source:bundle.sgx_original_pdf_url,
    note:"2026年3Q発行会社資料・FY2025とは比較不可"},
   {symbol:"U11",name:"UOB",fy:"未照合",q3:"未照合",equity:"未照合",source:banks.U11.bank_financial_state.source_url,
    note:"年次資料は登録済み・同条件の数値照合待ち"}
  ];
 }
 async function render() {
  const body=document.getElementById("bankCoverageRows");
  const info=document.getElementById("bankCoverageStatus");
  if(!body||!info)return;
  try {
   const [f,b]=await Promise.all(["./data/latest.json","./data/sgx-ocbc-bank-research-v166.json"].map(async url=>{
     const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
   }));
   body.replaceChildren();
   for(const item of validate(f,b)){
     const tr=document.createElement("tr");
     for(const value of [item.symbol+" / "+item.name,item.fy,item.q3,item.equity,item.note]){
       const td=document.createElement("td");td.textContent=value;tr.append(td);
     }
     const td=document.createElement("td");
     if(/^https:\/\//.test(item.source)){
       const a=document.createElement("a");a.href=item.source;a.textContent="原本資料";
       a.target="_blank";a.rel="noopener noreferrer";td.append(a);
     }else td.textContent="未登録";
     tr.append(td);body.append(tr);
   }
   info.textContent="単位：百万SGD。2025年度と2026年3Qの異なる期間・普通株持分と親会社帰属持分は直接比較できない。株価・株式数・第三者独立数値検証は未完。";
  } catch(e) {
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="資料の照合待ちのため非表示";tr.append(td);
   body.replaceChildren(tr);info.textContent="過去の原本数値は自動的に正式評価へ昇格しない";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
