/* v185: explain exact ranking blockers, never silently activate a valuation. */
"use strict";
(function(root){
 const labels={
  fy2025_external_auditor_opinion:"2025年外部監査意見",
  parent_equity_independent_reperformance:"親会社株主持分の独立再計算",
  financial_numerical_independent_reperformance:"財務主要数値の独立再計算",
  authenticated_sgx_execution_quote:"SGX正規約定価格",
  authenticated_quote_exact_trade_time:"正確な約定時刻",
  latest_treasury_adjusted_shares:"最新自己株式控除後株数",
  quote_share_effective_date_compatible:"株価と株式数の基準日一致",
  current_earnings_period_applicable:"現在の業績期間と評価の整合",
  bank_independent_financial_check:"銀行財務の独立数値検証",
  current_bank_quote_verified:"銀行株の正規SGX株価",
  current_bank_shares_verified:"銀行株の最新自己株式控除後株数"
 };
 function validate(feed,gate,readiness){
  if(feed?.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     gate?.schema_version!=="sgx-first-issuer-evidence-gate-v137"||
     gate.feed_updated_at_utc!==feed.updated_at_utc||
     gate.eligible_count!==0||gate.ranking_activation_permitted!==false||
     !Array.isArray(gate.required_evidence_fields)||gate.required_evidence_fields.length!==8||
     readiness?.schema_version!=="sgx-ranking-readiness-evidence-v117"||
     readiness.published_feed_updated_at_utc!==feed.updated_at_utc||
     readiness.ranking_eligible_count!==0)
    throw Error("Ranking evidence inconsistent with current feed");
  const out=[];
  for(const symbol of ["G13","S63"]){
   const matches=gate.records?.filter(x=>x.symbol===symbol);
   if(matches?.length!==1||matches[0].eligible_for_ranking!==false)
    throw Error("Industrial issuer audit gate missing");
   const data=matches[0];
   const missing=gate.required_evidence_fields.filter(key=>data.evidence_requirements?.[key]!==true);
   const passed=gate.required_evidence_fields.length-missing.length;
   if(passed!==1||missing.length!==7||
      data.evidence_requirements.fy2025_external_auditor_opinion!==true||
      feed.records.filter(x=>x.symbol===symbol&&x.ranking_eligible===false).length!==1)
    throw Error("Industrial issuer evidence changed, rules need re-validation");
   out.push({symbol,kind:"一般事業会社",passed,total:8,missing:missing.map(x=>labels[x]||x)});
  }
  for(const symbol of ["D05","O39","U11"]){
   const matches=readiness.records?.filter(x=>x.symbol===symbol);
   if(matches?.length!==1||matches[0].sector_model!=="BANKING"||
      matches[0].eligible_for_ranking!==false)
    throw Error("Bank evidence record missing");
   const missing=matches[0].remaining_verification_tasks;
   if(!Array.isArray(missing)||missing.length!==3||
      missing.some(x=>!labels[x])||
      feed.records.filter(x=>x.symbol===symbol&&x.ranking_eligible===false).length!==1)
    throw Error("Bank remaining verification tasks cannot be inferred");
   out.push({symbol,kind:"銀行",passed:0,total:3,missing:missing.map(x=>labels[x])});
  }
  return out;
 }
 async function render(){
  const tbody=document.getElementById("rankingBlockerRows"),status=document.getElementById("rankingBlockerStatus");
  if(!tbody||!status)return;
  try{
   const paths=["./data/latest.json","./data/sgx-first-issuer-gate-v137.json","./data/sgx-ranking-readiness-v117.json"];
   const items=await Promise.all(paths.map(async url=>{
    const res=await fetch(url,{cache:"no-store"});if(!res.ok)throw Error("HTTP");return res.json();
   }));
   tbody.replaceChildren();
   const data=validate(...items);
   for(const r of data){
    const tr=document.createElement("tr");
    for(const value of [r.symbol,r.kind,r.passed+"/"+r.total+"項目",
      r.missing.join("、"),"ランキング除外"]){
     const td=document.createElement("td");td.textContent=value;tr.append(td);
    }
    tbody.append(tr);
   }
   status.textContent="検証条件が異なるため、一般事業会社と銀行の達成項目数は比較できない。残項目は公式原本の収集だけでなく、独立した財務検証と正規市場データ取得を要する。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="最新検証と公開データが一致しないため、未完了条件を非表示";
   tr.append(td);tbody.replaceChildren(tr);status.textContent="ランキング検証データの同期待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
