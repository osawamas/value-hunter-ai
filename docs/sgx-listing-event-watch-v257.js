/* v257: primary-source corporate-event guard for historic SGX company-code lists. */
"use strict";
(function(root){
 function validate(events,feed){
  if(events?.schema_version!=="sgx-listing-event-watch-v257"||
     events.as_of_date!=="2026-11-15"||
     events.scope!=="TWO_SELECTED_ISSUERS_WITH_MATERIAL_CORPORATE_EVENTS_NOT_FULL_SGX_STATUS"||
     events.investable_by_this_watch!==false||
     events.definitive_current_trading_status_verified!==false||
     events.complete_master_covered!==false||
     events.latest_licensed_market_price_available!==false||
     events.ranking_eligible_count!==0||
     feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(events.events)||events.events.length!==2)
   throw Error("Current listing status evidence gate failed");
  const expected=[
   ["5WA","SG2F86994413","COURT_HEARING_SCHEDULED_FOR_PRIVATISATION_SCHEME","PENDING_COURT_AND_EXCHANGE_APPROVAL","SG261110OTHR59DA"],
   ["P11","BMG6845B1046","CHAPTER_11_PLAN_ADMINISTRATION_UPDATE","RESTRUCTURING_MONITOR","SG261016OTHRODOS"]
  ];
  const seen=new Set();
  return events.events.map((item,i)=>{
   const p=expected[i];
   if([item.symbol,item.isin,item.event_code,item.status,item.announcement_reference].some((v,j)=>v!==p[j])||
      seen.has(item.symbol)||
      !/^https:\/\/links\.sgx\.com\//.test(item.source_url)||
      typeof item.detail_ja!=="string"||!item.detail_ja||
      !/^2026-\d\d-\d\d$/.test(item.event_date)||
      item.delisted_confirmed!==false||
      item.active_listing_today_confirmed!==false||
      item.dates_are_firm!==false||
      item.ranking_eligible!==false)
    throw Error("Unverified delisting claim");
   if(i===0&&(item.court_hearing_date!=="2026-11-30"||item.indicative_last_trading_date!=="2026-12-01"||
               item.indicative_delisting_date!=="2026-12-17"))throw Error("OUEH expected dates changed");
   if(i===1&&(item.indicative_last_trading_date!==null||
               item.indicative_delisting_date!==null))throw Error("P11 dates invented");
   seen.add(item.symbol);
   return {symbol:item.symbol,issuer:item.issuer,detail:item.detail_ja,
    event:item.event_date,status:item.status,source:item.source_url,
    provisionalLast:item.indicative_last_trading_date,
    provisionalDelist:item.indicative_delisting_date,
    eligible:false};
  });
 }
 async function render(){
  const status=document.getElementById("sgxListingEventStatus");
  const body=document.getElementById("sgxListingEventRows");
  if(!status||!body)return;
  try{
   const [events,feed]=await Promise.all(["./data/sgx-material-listing-events-v257.json","./data/latest.json"]
    .map(async url=>{const response=await fetch(url,{cache:"no-store"});if(!response.ok)throw Error("HTTP "+response.status);return response.json()}));
   const rows=validate(events,feed),frag=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    const values=[r.symbol+" / "+r.issuer,r.event,r.detail+
      (r.provisionalDelist?"（上場廃止予定目安："+r.provisionalDelist+"。確定ではない）":"")];
    for(const v of values){const td=document.createElement("td");td.textContent=v;tr.append(td)}
    const td=document.createElement("td"),a=document.createElement("a");
    a.textContent="SGX開示";a.href=r.source;a.target="_blank";a.rel="noopener noreferrer";
    td.append(a);tr.append(td);frag.append(tr);
   }
   body.replaceChildren(frag);
   status.textContent="2026年11月15日現在の開示確認。5WAは裁判所の審理日を通知済み、P11は再建計画の管理中。いずれも現在の取引可否・確定上場廃止日を保証せず、投資ランキングには含めない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=4;td.textContent="重要な企業イベントの根拠を照合できないため非表示";tr.append(td);
   body.replaceChildren(tr);status.textContent="原本・状態の照合待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
