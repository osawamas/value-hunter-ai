/* v184: 9M26 versus 9M25 SGX primary issuer bank group profits. */
"use strict";
(function(root){
 function validate(feed,dbs,ocbc,uob){
  if(feed?.schema_version!=="value_hunter_web_v29"||feed.ranking_enabled!==false||
     feed.ranking_eligible_count!==0||
     dbs?.status!=="DBS_3Q26_9M26_PRIMARY_SGX_TABLE_COLUMNS_RECONCILED"||
     dbs.record?.schema_version!=="sgx-dbs-exact-3q-9m-original-v180"||
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
    throw Error("9M period and original issuer source not verified");
  const expected=[["D05","DBS",8822,8675],["O39","OCBC",6237,5677],["U11","UOB",4165,3271]];
  const profitSource=dbs.record.exact_original_table_rows?.["Net profit"]?.source_column_values;
  const extracted=[
   [dbs.record.net_profit_9m26_sgd_millions,
    Number(profitSource?.[6]?.replace(/,/g,""))],
   [ocbc.income_statement_sgd_millions?.["9M26"]?.group_net_profit,
    ocbc.income_statement_sgd_millions?.["9M26"]?.group_net_profit_previous_year],
   [uob.record.period_specific_table_rows?.["Net profit"]?.["9m26"],
    uob.record.period_specific_table_rows?.["Net profit"]?.["9m25"]]
  ];
  const hashes=[dbs.record.original_pdf_sha256,ocbc.sgx_original_pdf_sha256,uob.record.official_pdf_sha256];
  return expected.map(([symbol,name,current,prior],i)=>{
   if(extracted[i][0]!==current||extracted[i][1]!==prior||
      !/^[a-f0-9]{64}$/.test(hashes[i])||
      feed.records.filter(x=>x.symbol===symbol&&x.ranking_eligible===false).length!==1)
     throw Error("9M bank group profit or security registration invalid");
   return {symbol,name,current,prior,changePct:(current-prior)/prior*100};
  });
 }
 async function render(){
  const tbody=document.getElementById("bankNineMonthRows");
  const note=document.getElementById("bankNineMonthStatus");
  if(!tbody||!note)return;
  try{
   const paths=["./data/latest.json","./data/sgx-dbs-exact-table-v180.json",
      "./data/sgx-ocbc-bank-research-v166.json","./data/sgx-uob-exact-bank-table-v175.json"];
   const data=await Promise.all(paths.map(async path=>{
    const response=await fetch(path,{cache:"no-store"});
    if(!response.ok)throw Error("Missing official research record");
    return response.json();
   }));
   tbody.replaceChildren();
   for(const r of validate(...data)){
    const tr=document.createElement("tr");
    for(const txt of [r.symbol+" / "+r.name,r.prior.toLocaleString("ja-JP"),
      r.current.toLocaleString("ja-JP"),(r.changePct>=0?"+":"")+r.changePct.toFixed(2)+"%",
      "2026年1〜9月・発行会社原本"]){
     const td=document.createElement("td");td.textContent=txt;tr.append(td);
    }
    tbody.append(tr);
   }
   note.textContent="単位：百万SGD。9か月累計の純利益を前年同期と比較。別企業の会計方針・非経常要因や第三者検証の不足があり、割安ランキングには使用しない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="9か月累計利益の原本確認待ち";tr.append(td);
   tbody.replaceChildren(tr);note.textContent="不完全な比較は非表示";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
