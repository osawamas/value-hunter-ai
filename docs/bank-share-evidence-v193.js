/* v193: dated bank share evidence, never a live quote or investable share-count feed. */
"use strict";
(function(root){
 function validate(feed,data){
  if(feed?.schema_version!=="value_hunter_web_v29"||
    feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
    data?.schema_version!=="sgx-bank-corporate-actions-v190"||
    data.verified_as_of_date!=="2026-11-12"||
    data.ranking_eligible!==false||data.no_license_verified_quote!==true||
    data.source_policy?.licensed_timestamped_quotation_available!==false||
    !Array.isArray(data.uob?.observations)||data.uob.observations.length!==2||
    data.ocbc?.outstanding_change_notice?.share_change_verified!==false||
    data.ocbc.outstanding_change_notice.official_attachment_obtained!==false||
    data.uob.latest_unverified?.official_verified!==false)
   throw Error("銀行の株式数検証情報が未整合");
  // Refuse rendering even historical share counts if issuer-level gates drift.
  if(!Array.isArray(feed.records)||!feed.coverage||
    feed.coverage.all_sgx_listed!==false||
    feed.coverage.registered_count!==feed.records.length||
    feed.records.some(x=>x.ranking_eligible!==false)||
    ["D05","O39","U11"].some(symbol=>
      feed.records.filter(x=>x.symbol===symbol).length!==1))
   throw Error("銀行ごとのランキング判定が不一致");
  const [a,b]=data.uob.observations;
  if(a.date!=="2026-11-11"||b.date!=="2026-11-12"||
    a.issued_excluding_treasury_after!==1646745591||
    b.issued_excluding_treasury_after!==1646711591||
    a.cancelled!==34000||b.cancelled!==34000||
    a.purchased!==34000||b.purchased!==34000||
    a.origin!=="OFFICIAL_SGX_ANNOUNCEMENT_HTML"||
    b.origin!=="OFFICIAL_SGX_ANNOUNCEMENT_HTML"||
    a.announcement_reference!=="SG261111OTHRGYNT"||
    b.announcement_reference!=="SG261112OTHRSYPK"||
    a.issued_excluding_treasury_after-b.issued_excluding_treasury_after!==34000||
    ![a,b].every(x=>x.official_verified===true&&
      /^https:\/\/links\.sgx\.com\//.test(x.source_url)))
   throw Error("UOB原本の履歴が期待値と不一致");
  if(data.uob.latest_unverified.date!=="2026-11-13"||
    data.uob.latest_unverified.may_enter_ranking!==false||
    data.ocbc.outstanding_change_notice.official_attachment_obtained!==false||
    data.ocbc.outstanding_change_notice.may_enter_ranking!==false)
   throw Error("未確認資料を正式情報へ昇格不可");
  return {symbol:"U11",date:b.date,count:b.issued_excluding_treasury_after,
    cancelled:b.cancelled,source:b.source_url};
 }
 async function render(){
  const status=document.getElementById("bankShareEvidenceStatus");
  const tbody=document.getElementById("bankShareEvidenceRows");
  if(!status||!tbody)return;
  try{
   const [feed,actions]=await Promise.all(
    ["./data/latest.json","./data/sgx-bank-corporate-actions-v190.json"].map(async url=>{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
    }));
   const u=validate(feed,actions);
   const rows=[
    ["UOB / U11",u.date,u.count.toLocaleString("ja-JP")+" 株","SGX発表参照（過去日付）",u.source],
    ["UOB / U11","2026-11-13","—","SGX原本未取得・第三者掲載のみ",null],
    ["OCBC / O39","2026-11-12","—","SGX添付PDF未取得",null]
   ];
   const frag=document.createDocumentFragment();
   for(const [symbol,date,count,kind,source] of rows){
    const tr=document.createElement("tr");
    for(const value of [symbol,date,count,kind]){
      const td=document.createElement("td");td.textContent=value;tr.append(td);
    }
    const td=document.createElement("td");
    if(source){const a=document.createElement("a");a.href=source;a.textContent="SGX発表";a.target="_blank";a.rel="noopener noreferrer";td.append(a);}
    else td.textContent="未取得";
    tr.append(td);frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="11月12日付UOB株式数は過去のSGX発表に基づく記録。最新株数ではない。原本URLの記録・内部照合と、独立検証・同日株価認証は別。PER・PBR・時価総額・ランキングには使わない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="株式数の根拠データが一致しないため非表示";tr.append(td);
   tbody.replaceChildren(tr);status.textContent="照合未完了：株式数を表示しない";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
