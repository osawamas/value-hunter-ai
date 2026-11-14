/* v118: read-only readiness blockers, not an investment ranking. */
"use strict";
(function(root){
 const ORDER=["S68","G13","S20","S63","D05","O39","U11"];
 const LABELS={
  parent_equity_independently_checked:"親会社株主持分の独立照合",
  financials_independently_checked:"財務指標の独立照合",
  quote_independently_exchange_verified:"SGX株価の独立照合",
  updated_treasury_adjusted_shares_independently_checked:"自己株式控除後の株式数の更新・照合",
  same_date_quote_shares_compatible:"株価と株式数の基準日を整合",
  valid_earnings_for_positive_per:"黒字PERに必要な利益（赤字時は非適用）",
  issuer_primary_financial_pdf:"発行企業の公式財務PDF",
  issuer_two_document_revenue_crosscheck:"発行企業資料間の売上照合",
  issuer_two_document_profit_crosscheck:"発行企業資料間の利益照合",
  issuer_bank_financials_parsed:"銀行専用財務資料の解析",
  bank_independent_financial_check:"銀行財務の独立照合",
  current_bank_quote_verified:"銀行株価の独立照合",
  current_bank_shares_verified:"銀行の最新発行済株式数を照合"
 };
 function validate(feed,audit){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_eligible_count!==0||feed.ranking_enabled!==false||
     !Array.isArray(feed.records)||feed.records.length!==7||
     !audit||audit.schema_version!=="sgx-ranking-readiness-evidence-v117"||
     audit.ranking_eligible_count!==0||audit.all_issuers_still_blocked!==true||
     audit.changes_to_financial_feed!==false||
     audit.registered_issuers!==7||
     audit.published_feed_updated_at_utc!==feed.updated_at_utc||
     !Array.isArray(audit.records)||audit.records.length!==7)
    throw new Error("検証診断と財務データの版が合わない");
  const seen=new Set();
  for(const r of audit.records){
   if(!r||!ORDER.includes(r.symbol)||seen.has(r.symbol)||
      r.eligible_for_ranking!==false||r.market_cap_or_per_pbr_promoted!==false||
      r.estimated_completion_percentage!==null||
      !Array.isArray(r.remaining_verification_tasks)||!r.remaining_verification_tasks.length||
      !r.remaining_verification_tasks.every(t=>typeof t==="string"&&!!LABELS[t])||
      !feed.records.some(f=>f.symbol===r.symbol&&f.ranking_eligible===false))
    throw new Error("銘柄別診断が不正");
   seen.add(r.symbol);
  }
  return ORDER.map(s=>{
   const r=audit.records.find(v=>v.symbol===s);
   return {symbol:s,sector:r.sector_model==="BANKING"?"銀行":"一般事業会社",
     missing:r.remaining_verification_tasks.map(t=>LABELS[t]),
     issuerEvidence: r.observed_evidence_signals?.issuer_primary_financial_pdf===true ||
       r.observed_evidence_signals?.issuer_bank_financials_parsed===true};
  });
 }
 async function render(){
  const target=document.getElementById("readinessRows");
  const info=document.getElementById("readinessStatus");
  if(!target||!info)return;
  try{
   const [feed,audit]=await Promise.all([
    "./data/latest.json","./data/sgx-ranking-readiness-v117.json"
   ].map(async url=>{
    const r=await fetch(url,{cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    return r.json();
   }));
   const rows=validate(feed,audit);
   target.replaceChildren();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const value of [r.symbol,r.sector,r.issuerEvidence?"公式財務資料あり":"公式財務資料を確認中",
      r.missing.join("／"),"除外（条件未達）"]){
     const td=document.createElement("td");td.textContent=value;td.className="readiness-cell";tr.append(td);
    }
    target.append(tr);
   }
   info.textContent="7社ともランキング対象外。これは投資判断順位ではなく、データの検証待ち項目。発行企業資料間の照合は独立検証ではない。";
  }catch(error){
   target.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="財務データとの版が異なるため、診断を非表示。";
   tr.append(td);target.append(tr);
   info.textContent="検証診断が未更新または読み込み失敗。古い結果は表示しない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root&&root.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
