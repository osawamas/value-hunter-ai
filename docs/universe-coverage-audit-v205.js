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
 // v251 historical aggregate is a scale reference, not a verified issuer directory.
 function compareOfficialMonthEnd(feed,candidates,official,statistics){
  const known=reconcile(feed,candidates,official);
  if(statistics?.schema_version!=="sgx-official-monthend-listed-securities-count-v251"||
     statistics.report_month!=="2026-08"||
     statistics.as_of_date!=="2026-08-31"||
     statistics.reported_total_listed_securities!==604||
     statistics.reported_mainboard_listings!==406||
     statistics.reported_catalist_listings!==198||
     statistics.reported_mainboard_listings+statistics.reported_catalist_listings!==statistics.reported_total_listed_securities||
     statistics.source_kind!=="SGX_ORIGINAL_MONTHLY_MARKET_STATISTICS_PDF"||
     statistics.source_url!=="https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20Update_Aug%202026.ashx?App=Announcement&FileID=903915"||
     statistics.not_current_asof_2026_11_15!==true||
     statistics.not_security_code_list!==true||
     statistics.not_issuer_level_registry!==true||
     statistics.not_licensing_permission!==true||
     statistics.comparison_scope!=="HISTORICAL_SGX_AGGREGATE_VS_PARTIAL_THIRD_PARTY_COMPANY_CANDIDATES_NOT_SAME_UNITS"||
     statistics.official_security_master_complete!==false||
     statistics.ranking_eligible!==false||
     statistics.financial_feed_modified!==false||
     known.official_master_complete!==false||
     known.ranking_eligible!==0)
   throw Error("SGX historical listing count cannot be promoted to issuer master");
  return {...known,official_historical_listed_securities:604,
    as_of:"2026-08-31",official_historical_mainboard:406,
    official_historical_catalist:198,
    historical_count_issuer_universe_comparable:false,
    historical_count_not_current:true,
    source:statistics.source_url};
 }
 async function render(){
  const status=document.getElementById("universeCoverageAuditStatus");
  const body=document.getElementById("universeCoverageAuditRows");
  if(!status||!body)return;
  try{
   const files=await Promise.all(
    ["./data/latest.json","./data/sgx-universe-candidates.json","./data/sgx-official-batch-seed-v196.json","./data/sgx-official-monthend-aug2026-v251.json"]
    .map(async p=>{const r=await fetch(p,{cache:"no-store"});if(!r.ok)throw Error("HTTP");return r.json()}));
   const d=compareOfficialMonthEnd(...files);
   const items=[
    ["SGX公式・2026年8月末の上場証券数（過去時点）",String(d.official_historical_listed_securities)+"（Mainboard "+d.official_historical_mainboard+" / Catalist "+d.official_historical_catalist+"）"],
    ["第三者の企業候補（上記と定義・時点が異なる）",String(d.third_party_candidates)+"（不完全・公式全証券一覧ではない）"],
    ["公式11証券と第三者182候補の一致",String(d.official_in_third_party)+" / "+String(d.official_lot_batch)],
    ["公式11証券のうち第三者候補に欠けるコード",d.official_missing_from_third_party.join("、")||"なし"],
    ["公式11証券のうち財務未登録コード",d.official_missing_financials.join("、")||"なし"]
   ],fragment=document.createDocumentFragment();
   for(const [a,b] of items){const tr=document.createElement("tr");for(const v of [a,b]){
    const td=document.createElement("td");td.textContent=v;tr.append(td);
   }fragment.append(tr)}
   body.replaceChildren(fragment);
   status.textContent="SGX公式2026年8月末の上場証券604と第三者企業候補182は定義・時点が異なる。182/604を取得率や未収録銘柄数に換算しない。公式の完全な銘柄コード一覧は未取得。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=2;td.textContent="台帳の更新差分が未照合のため詳細を非表示";
   tr.append(td);body.replaceChildren(tr);
   status.textContent="台帳の照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={reconcile,compareOfficialMonthEnd};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
