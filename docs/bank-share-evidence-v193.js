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
 // v245: the browser must verify newer official source records, not trust only v190.
 function validateSupplemental(feed,actions,uob,ocbc,rights){
  const historic=validate(feed,actions);
  if(uob?.schema_version!=="sgx-uob-official-daily-buyback-chain-v242"||
     uob.symbol!=="U11"||uob.isin!=="SG1M31001969"||
     uob.source_kind!=="SGX_ORIGINAL_ANNOUNCEMENT_HTML"||
     uob.official_current_asof_date!==historic.date||
     !Array.isArray(uob.rows)||uob.rows.length!==3||
     uob.latest_2026_11_13_official_original_retrieved!==false||
     uob.latest_2026_11_13_secondary_not_promoted!==true||
     uob.ranking_eligible!==false||
     ocbc?.schema_version!=="sgx-ocbc-official-issuer-identity-v244"||
     ocbc.symbol!=="O39"||ocbc.isin!=="SG1S04926220"||
     ocbc.source_url!=="https://links.sgx.com/1.0.0/corporate-information/1943"||
     ocbc.company_information_source!=="SGX_OFFICIAL_CORPORATE_INFORMATION"||
     ocbc.official_treasury_attachment_2026_11_12_obtained!==false||
     ocbc.latest_issued_excluding_treasury_shares_verified!==false||
     ocbc.ranking_eligible!==false||
     rights?.schema_version!=="sgx-source-reuse-policy-v222"||
     rights.licensed_time_stamped_quote_available!==false||
     !Array.isArray(rights.feeds)||rights.feeds.length!==3||
     rights.feeds.some(x=>x.public_quote_redistribution_authorized!==false||
                           x.can_enable_rankings!==false))
    throw Error("追加SGX原本または利用権限の照合に失敗");
  const dates=["2026-11-10","2026-11-11","2026-11-12"];
  const refs=["SG261110OTHRQ7Q7","SG261111OTHRGYNT","SG261112OTHRSYPK"];
  const counts=[1646779591,1646745591,1646711591];
  for(let i=0;i<3;i++){
   const row=uob.rows[i];
   if(!row||row.trade_date!==dates[i]||row.announcement_ref!==refs[i]||
      row.issued_excluding_treasury_after_purchase!==counts[i]||
      row.purchased!==34000||row.cancelled!==34000||
      !/^https:\/\/links\.sgx\.com\//.test(row.source_url))
    throw Error("UOB買戻し原本の連続性が不一致");
   if(i&&uob.rows[i-1].issued_excluding_treasury_after_purchase-row.issued_excluding_treasury_after_purchase!==row.cancelled)
    throw Error("UOB消却株式数と発行済株数が一致しない");
  }
  const final=uob.rows[2];
  if(final.issued_excluding_treasury_after_purchase!==historic.count||
     final.cancelled!==historic.cancelled||
     final.source_url!==historic.source||
     final.announcement_ref!==actions.uob.observations[1].announcement_reference)
    throw Error("v190とv242のUOB原本が不一致");
  return {uob:historic,ocbc:{symbol:ocbc.symbol,isin:ocbc.isin,source_url:ocbc.source_url}};
 }
 // v284 direct GitHub Actions original-body replay proof, distinct from indexed
 // historic source records and from the still-missing 13-Nov SGXNet original.
 function validateReplayedOriginal(uob,actions,chain,feed){
  const old=validate(feed,actions);
  if(uob?.schema_version!=="uob-sgxnet-official-original-share-count-2026-11-12-v284"||
     uob.original_workflow_run!=="https://github.com/osawamas/value-hunter-ai/actions/runs/43664272047"||
     uob.issuer!=="UNITED OVERSEAS BANK LIMITED"||uob.symbol!=="U11"||
     uob.isin!=="SG1M31001969"||uob.announcement_ref!=="SG261112OTHRSYPK"||
     uob.event_date!==old.date||
     uob.issued_excluding_treasury_after_event!==old.count||
     uob.shares_purchased_on_event!==old.cancelled||
     uob.shares_cancelled_on_event!==old.cancelled||
     uob.treasury_shares_after_event!==14548000||
     uob.original_html_sha256!=="02722c970c4200e6507d60fbaa5458a2bcf43d96686f5111853bffb800e6e8e2"||
     uob.original_html_bytes!==7612||
     uob.original_issuer_isin_announcement_and_share_labels_matched!==true||
     uob.official_source_url!==old.source||
     chain?.rows?.[2]?.source_url!==uob.official_source_url||
     uob.current_issued_shares_verified!==false||
     uob.current_quote_verified!==false||uob.stock_ranking_eligible!==false||
     uob.next_day_notice_known_but_original_not_confirmed?.original_sgxnet_url_verified!==false||
     uob.next_day_notice_known_but_original_not_confirmed?.announcement_ref!=="SG261113OTHRHOAF"||
     uob.next_day_notice_known_but_original_not_confirmed?.secondary_reports_issued_excluding_treasury_after_event!==1646677591||
     uob.next_day_notice_known_but_original_not_confirmed?.not_suitable_for_current_verified_share_count!==true||
     uob.issued_excluding_treasury_after_event-
       uob.next_day_notice_known_but_original_not_confirmed.secondary_reports_issued_excluding_treasury_after_event!==34000||
     uob.next_day_notice_known_but_original_not_confirmed?.secondary_reports_shares_purchased_and_cancelled!==34000)
     throw Error("UOB 12-Nov原本SHAまたは13-Nov未確認区分が不一致");
  return {date:uob.event_date,count:uob.issued_excluding_treasury_after_event,
    sha:uob.original_html_sha256,source:uob.official_source_url,
    nextDayUnverified:true};
 }
 async function render(){
  const status=document.getElementById("bankShareEvidenceStatus");
  const tbody=document.getElementById("bankShareEvidenceRows");
  if(!status||!tbody)return;
  try{
   const [feed,actions,uobOriginal,ocbcIssuer,rights,replayed]=await Promise.all(
    ["./data/latest.json","./data/sgx-bank-corporate-actions-v190.json",
     "./data/sgx-uob-official-buyback-v242.json","./data/sgx-ocbc-issuer-identity-v244.json",
     "./data/sgx-source-rights-review-v222.json",
     "./data/uob-original-12nov-share-count-v284.json"].map(async url=>{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
    }));
   const verified=validateSupplemental(feed,actions,uobOriginal,ocbcIssuer,rights);
   const u=verified.uob;
   const original=validateReplayedOriginal(replayed,actions,uobOriginal,feed);
   const rows=[
    ["UOB / U11",original.date,original.count.toLocaleString("ja-JP")+" 株","SGX原本本文・SHA256照合済み（過去日付）",original.source],
    ["UOB / U11","2026-11-13","—","SGX原本未取得・第三者掲載のみ",null],
    ["OCBC / O39","2026-11-12","—","公式銘柄識別確認・SGX添付PDF未取得",verified.ocbc.source_url]
   ];
   const frag=document.createDocumentFragment();
   for(const [symbol,date,count,kind,source] of rows){
    const tr=document.createElement("tr");
    for(const value of [symbol,date,count,kind]){
      const td=document.createElement("td");td.textContent=value;tr.append(td);
    }
    const td=document.createElement("td");
    if(source){const a=document.createElement("a");a.href=source;a.textContent=symbol==="OCBC / O39"?"SGX会社情報":"SGX原本";
      if(symbol==="UOB / U11"&&date==="2026-11-12")a.title="原本SHA-256："+original.sha;a.target="_blank";a.rel="noopener noreferrer";td.append(a);}
    else td.textContent="未取得";
    tr.append(td);frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="v284で11月12日のUOB SGXNet原本本文とSHA256を再取得検証。11月13日原本は未取得、12日の株数は過去の記録。OCBCはSGX公式銘柄識別のみ確認済み・株数原本未取得。正規株価利用許諾なし。PER・PBR・ランキングには使わない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="株式数の根拠データが一致しないため非表示";tr.append(td);
   tbody.replaceChildren(tr);status.textContent="照合未完了：株式数を表示しない";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate,validateSupplemental,validateReplayedOriginal};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
