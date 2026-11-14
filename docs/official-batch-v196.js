/* v196: SGX's official 11-security first batch of 10-share board lots.
   This is NOT the exchange's full dated security master, nor a quote feed. */
"use strict";
(function(root){
 const expectedCodes=["BN4","C07","D05","G07","H02","J36","K6S","O39","S68","U11","V03"];
 function validate(seed,feed){
  if(seed?.schema_version!=="sgx-official-first-batch-board-lot-v196"||
   seed.source_url!=="https://www.sgx.com/securities/trading"||
   seed.effective_date!=="2026-10-05"||
   seed.source_is_full_security_master!==false||
   seed.official_full_security_master_obtained!==false||
   seed.quote_fields_excluded!==true||
   seed.quote_usage_or_redistribution_license_verified!==false||
   seed.ranking_eligible_count!==0||
   seed.issued_shares_verified!==false||
   seed.total_official_named_items!==11||
   !Array.isArray(seed.rows)||seed.rows.length!==11||
   feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||
   !Array.isArray(feed.records))
   throw Error("Official SGX list seed not admissible");
  const codes=seed.rows.map(x=>x.symbol).sort();
  if(JSON.stringify(codes)!==JSON.stringify(expectedCodes))throw Error("SGX eleven symbols mismatch");
  const registered=new Set(feed.records.map(x=>x.symbol));
  return seed.rows.map(x=>{
   if(x.board_lot_shares!==10||x.effective_date!=="2026-10-05"||
    !["SGD","USD"].includes(x.trading_currency)||
    x.provenance!=="OFFICIAL_SGX_TRADING_PAGE_STATIC_BATCH"||
    x.eligible_for_valuation!==false||!x.name)
    throw Error("Official seed row incomplete");
   if((x.symbol==="J36"||x.symbol==="K6S")&&x.trading_currency!=="USD")
    throw Error("USD trading currency mismatch");
   if(!["J36","K6S"].includes(x.symbol)&&x.trading_currency!=="SGD")
    throw Error("SGD trading currency mismatch");
   return {symbol:x.symbol,name:x.name,currency:x.trading_currency,
    board_lot_shares:10,registered_financial_record:registered.has(x.symbol)};
  });
 }
 async function render(){
  const body=document.getElementById("officialSeedRows");
  const status=document.getElementById("officialSeedStatus");if(!body||!status)return;
  try{
   const [seed,feed]=await Promise.all(
    ["./data/sgx-official-batch-seed-v196.json","./data/latest.json"].map(async p=>{
     const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json();
    }));
   const rows=validate(seed,feed),frag=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const t of [r.symbol,r.name,r.currency,"10株",r.registered_financial_record?"財務登録あり":"財務未登録"]){
     const td=document.createElement("td");td.textContent=t;tr.append(td);
    }frag.append(tr);
   }
   body.replaceChildren(frag);
   status.textContent="SGX公式・2026年10月5日の売買単位10株への変更対象11銘柄のみ。SGX公式全上場銘柄の完全な一覧ではない。取引価格や投資ランキングの証拠ではない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="公式銘柄コードの確認用データが不整合のため非表示";tr.append(td);
   body.replaceChildren(tr);status.textContent="照合未完了";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
