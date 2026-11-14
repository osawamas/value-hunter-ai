/* v182: original-source Q3 group profits YoY, no investment ranking. */
"use strict";
(function(root){
 function validate(feed,dbs,ocbc,uob){
  if(feed?.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     dbs?.status!=="DBS_3Q26_9M26_PRIMARY_SGX_TABLE_COLUMNS_RECONCILED"||
     dbs.record?.schema_version!=="sgx-dbs-exact-3q-9m-original-v180"||
     dbs.record.financial_period_end!=="2026-09-30"||
     dbs.record.unit!=="SGD_millions"||
     dbs.record.issuer_original_row_and_column_positions_verified!==true||
     dbs.record.independent_numerical_verification!==false||
     dbs.record.ranking_eligible!==false||
     ocbc?.schema_version!=="sgx-ocbc-bank-research-bundle-v166"||
     ocbc.quarter_end!=="2026-09-30"||
     ocbc.independent_third_party_financial_reperformance!==false||
     ocbc.per_pbr_and_ranking_permitted!==false||
     uob?.status!=="UOB_3Q26_9M26_SGX_PRIMARY_TABLE_COLUMNS_VERIFIED"||
     uob.record?.schema_version!=="sgx-uob-exact-3q26-bank-statement-v175"||
     uob.record.table_row_and_column_mapping_verified_in_issuer_pdf!==true||
     uob.record.independent_third_party_numerical_reperformance!==false||
     uob.record.ranking_eligible!==false)
   throw Error("Actual primary source Q3 banking figures unavailable");
  const pairs=[
   ["D05","DBS",dbs.record.net_profit_3q26_sgd_millions,
    Number(dbs.record.exact_original_table_rows?.["Net profit"]?.source_column_values?.[1]?.replace(/,/g,"")),
    dbs.record.original_pdf_sha256],
   ["O39","OCBC",ocbc.income_statement_sgd_millions?.["3Q26"]?.group_net_profit,
    ocbc.income_statement_sgd_millions?.["3Q26"]?.group_net_profit_previous_year,
    ocbc.sgx_original_pdf_sha256],
   ["U11","UOB",uob.record.period_specific_table_rows?.["Net profit"]?.["3q26"],
    uob.record.period_specific_table_rows?.["Net profit"]?.["3q25"],
    uob.record.official_pdf_sha256]
  ];
  const expected=[[2813,2954],[2042,1978],[1250,443]];
  return pairs.map(([symbol,name,current,prior,sha],i)=>{
   if(current!==expected[i][0]||prior!==expected[i][1]||
      !/^[a-f0-9]{64}$/.test(sha)||
      feed.records.filter(x=>x.symbol===symbol&&x.ranking_eligible===false).length!==1)
    throw Error("Bank original comparable Q3 profit missing or incorrect");
   return {symbol,name,current,prior,changePct:(current-prior)/prior*100};
  });
 }
 async function render(){
  const body=document.getElementById("bankProfitYoyRows"),note=document.getElementById("bankProfitYoyStatus");
  if(!body||!note)return;
  try{
   const paths=["./data/latest.json","./data/sgx-dbs-exact-table-v180.json",
    "./data/sgx-ocbc-bank-research-v166.json","./data/sgx-uob-exact-bank-table-v175.json"];
   const files=await Promise.all(paths.map(async p=>{
     const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
   }));
   body.replaceChildren();
   for(const x of validate(...files)){
     const tr=document.createElement("tr");
     const values=[x.symbol+" / "+x.name,x.prior.toLocaleString("ja-JP"),
      x.current.toLocaleString("ja-JP"),(x.changePct>=0?"+":"")+x.changePct.toFixed(2)+"%",
      "発行会社SGX原本表・独立監査ではない"];
     for(const value of values){const cell=document.createElement("td");cell.textContent=value;tr.append(cell)}
     body.append(tr);
   }
   note.textContent="単位：百万SGD。同じ2026年3Qと2025年3Qの純利益をSGX原本の表から比較。UOBは前年同期の一時要因が大きいため、成長率だけでは企業価値や割安さを判定できない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="前年同期の原本照合待ち";tr.append(td);
   body.replaceChildren(tr);note.textContent="財務資料の照合が完了しない限り数値を表示しない";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
