/* v138: strictly informational first issuer eligibility checklist (G13/S63). */
"use strict";
(function(root){
 const REQUIRED={
  fy2025_external_auditor_opinion:"FY2025の外部監査意見",
  parent_equity_independent_reperformance:"親会社株主持分の独立再検証",
  financial_numerical_independent_reperformance:"財務数値の独立再計算",
  authenticated_sgx_execution_quote:"SGX約定価格の認証",
  authenticated_quote_exact_trade_time:"正確な約定時刻の確認",
  latest_treasury_adjusted_shares:"最新の自己株式控除後株式数",
  quote_share_effective_date_compatible:"株価・株数の基準日整合",
  current_earnings_period_applicable:"直近利益の評価期間整合"
 };
 function validate(feed,gate){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !gate||gate.schema_version!=="sgx-first-issuer-evidence-gate-v137"||
     gate.feed_updated_at_utc!==feed.updated_at_utc||
     gate.checked_issuers!==2||gate.eligible_count!==0||
     gate.ranking_activation_permitted!==false||gate.no_financial_feed_changes!==true||
     !Array.isArray(gate.records)||gate.records.length!==2||
     JSON.stringify(gate.required_evidence_fields)!==JSON.stringify(Object.keys(REQUIRED)))
   throw Error("ランキング検証の版または安全状態が不一致");
  const rows=[];
  for(const symbol of ["G13","S63"]){
   const items=gate.records.filter(x=>x.symbol===symbol);
   const f=feed.records?.filter(x=>x.symbol===symbol);
   if(items.length!==1||f?.length!==1)throw Error("銘柄の重複または欠落");
   const v=items[0],state=v.evidence_requirements;
   if(!state||Object.keys(state).length!==8||
      Object.keys(state).some(key=>!Object.hasOwn(REQUIRED,key) || typeof state[key]!=="boolean")||
      !Array.isArray(v.unmet_requirements)||
      JSON.stringify(v.unmet_requirements)!==JSON.stringify(Object.keys(REQUIRED).filter(key=>!state[key]))||
      state.fy2025_external_auditor_opinion!==true||
      v.eligible_for_ranking!==false||v.promoted_market_cap_per_pbr!==false||
      f[0].ranking_eligible!==false||
      v.historical_share_snapshot_is_not_current!==true)
     throw Error("ランキングの未検証項目を認証済みとして扱えない");
   rows.push({symbol,items:Object.entries(state).map(([key,ok])=>({label:REQUIRED[key],ok}))});
  }
  return rows;
 }
 async function render(){
  const el=document.getElementById("firstIssuerGateRows");
  const message=document.getElementById("firstIssuerGateStatus");
  if(!el||!message)return;
  try{
   const [feed,gate]=await Promise.all([
    "./data/latest.json","./data/sgx-first-issuer-gate-v137.json"
   ].map(async path=>{
    const r=await fetch(path,{cache:"no-store"});
    if(!r.ok)throw Error("HTTP "+r.status);
    return r.json();
   }));
   const records=validate(feed,gate);
   el.replaceChildren();
   for(const record of records){
    const tr=document.createElement("tr");
    const name=document.createElement("td");name.textContent=record.symbol;tr.append(name);
    const summary=document.createElement("td");
    summary.textContent=record.items.filter(x=>x.ok).length+"／8項目（投資判断の進捗率ではない）";
    tr.append(summary);
    const detail=document.createElement("td");
    detail.textContent=record.items.map(x=>(x.ok?"確認済：":"未確認：")+x.label).join(" ／ ");
    tr.append(detail);
    const status=document.createElement("td");status.textContent="ランキング対象外";tr.append(status);
    el.append(tr);
   }
   message.textContent="監査意見は2025年度のみ。現在のSGX約定価格・最新株式数・独立数値検証が揃うまでは評価しない。";
  }catch(error){
   el.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=4;td.textContent="財務データと診断の版が異なるため非表示。";
   tr.append(td);el.append(tr);
   message.textContent="最新のランキング条件検証結果が未反映。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
