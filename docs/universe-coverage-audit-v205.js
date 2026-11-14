/* v205: compare three DIFFERENT coverage scopes without treating candidate codes
   as an exchange-certified issuer master or a valuation universe. */
"use strict";
(function(root){
 function reconcile(feed,candidates,official){
  if(feed?.schema_version!=="value_hunter_web_v29"||
   feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
   !Array.isArray(feed.records)||feed.coverage?.all_sgx_listed!==false||
   candidates?.schema_version!=="sgx-third-party-company-candidates-v99"||
   candidates.full_sgx_listing_completeness_verified!==false||
   candidates.records_not_added_to_verified_financial_feed!==true||
   candidates.eligible_for_ranking!==false||
   !Array.isArray(candidates.candidates)||
   official?.schema_version!=="sgx-official-first-batch-board-lot-v196"||
   official.source_is_full_security_master!==false||
   official.official_full_security_master_obtained!==false||
   official.ranking_eligible_count!==0||
   !Array.isArray(official.rows))
   throw Error("SGX coverage source classification changed");
  const map=(items,field)=>{const m=new Map();for(const item of items){
   const k=item?.[field];if(typeof k!=="string"||!k||m.has(k))throw Error("Missing or duplicate symbol "+k);m.set(k,item);
  }return m};
  const current=map(feed.records,"symbol"),
        third=map(candidates.candidates,"symbol"),
        officialByCode=map(official.rows,"symbol");
  if(current.size!==feed.coverage.registered_count||
   third.size!==candidates.provider_accepted_candidate_count||
   officialByCode.size!==official.total_official_named_items||
   current.size!==7||officialByCode.size!==11)
   throw Error("Source counts changed without review");
  if([...current.values()].some(r=>r.ranking_eligible!==false)||
     [...third.values()].some(r=>r.ranking_eligible!==false||
       r.source_verification!=="THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED")||
     [...officialByCode.values()].some(r=>r.eligible_for_valuation!==false||
       r.provenance!=="OFFICIAL_SGX_TRADING_PAGE_STATIC_BATCH"))
   throw Error("Unverified candidate promotion");
  const missingFromThird=[],missingFinance=[],both=[];
  for(const [symbol,r] of officialByCode){
   if(!third.has(symbol))missingFromThird.push(symbol);
   if(!current.has(symbol))missingFinance.push(symbol);
   if(third.has(symbol)&&current.has(symbol))both.push(symbol);
  }
  return {financial_records:current.size,third_party_candidates:third.size,
    official_lot_batch:officialByCode.size,
    official_in_third_party:officialByCode.size-missingFromThird.length,
    official_missing_from_third_party:missingFromThird.sort(),
    official_missing_financials:missingFinance.sort(),
    official_also_financial_and_candidate:both.sort(),
    official_master_complete:false,full_company_universe_verified:false,
    quote_or_valuation_permitted:false,ranking_eligible:0};
 }
 async function render(){
  const status=document.getElementById("universeCoverageAuditStatus");
  const body=document.getElementById("universeCoverageAuditRows");
  if(!status||!body)return;
  try{
   const files=await Promise.all(
    ["./data/latest.json","./data/sgx-universe-candidates.json","./data/sgx-official-batch-seed-v196.json"]
    .map(async p=>{const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json()}));
   const d=reconcile(...files);
   const items=[
    ["公式11証券と第三者182候補の一致",String(d.official_in_third_party)+" / "+String(d.official_lot_batch)],
    ["公式11証券のうち第三者候補に欠けるコード",d.official_missing_from_third_party.join("、")||"なし"],
    ["公式11証券のうち財務未登録コード",d.official_missing_financials.join("、")||"なし"]
   ],fragment=document.createDocumentFragment();
   for(const [a,b] of items){const tr=document.createElement("tr");for(const v of [a,b]){
    const td=document.createElement("td");td.textContent=v;tr.append(td);
   }fragment.append(tr)}
   body.replaceChildren(fragment);
   status.textContent="公式の11証券限定資料・第三者の182候補・財務登録7社を別々に照合。母集団は異なり、いずれも公式SGX全銘柄マスターの完成を示さない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=2;td.textContent="台帳の更新差分が未照合のため詳細を非表示";
   tr.append(td);body.replaceChildren(tr);
   status.textContent="台帳の照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={reconcile};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
