/* v162: historical source share date != historical reference quote day. */
"use strict";
(function(root){
 function validate(feed,sidecar){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !sidecar||sidecar.schema_version!=="sgx-share-price-date-coherence-v161"||
     sidecar.feed_updated_at_utc!==feed.updated_at_utc||
     sidecar.issuers_reviewed!==2||sidecar.mismatched_reference_date_count!==2||
     sidecar.official_trade_tape_verified_count!==0||
     sidecar.ranking_eligible_count!==0||sidecar.financial_feed_modified!==false||
     !Array.isArray(sidecar.records)||sidecar.records.length!==2)
    throw Error("基準日診断と現在の公開データの版が一致しない");
  return ["G13","S63"].map(symbol=>{
   const matches=sidecar.records.filter(x=>x.symbol===symbol);
   const original=feed.records.filter(x=>x.symbol===symbol);
   if(matches.length!==1||original.length!==1)throw Error("銘柄の重複または欠落");
   const x=matches[0],f=original[0];
   const shareDay=String(f.shares_as_of_date),quoteDay=String(f.quote_timestamp_utc).slice(0,10);
   const gap=Math.round((Date.parse(quoteDay+"T00:00:00Z")-Date.parse(shareDay+"T00:00:00Z"))/86400000);
   if(!Number.isInteger(gap)||gap<=0||
      x.reference_share_snapshot_date!==shareDay||
      x.reference_quote_trading_date!==quoteDay||
      x.share_quote_reference_date_gap_days!==gap||
      x.same_date_reconciled!==false||
      x.newest_snapshot_is_currently_complete!==false||
      x.official_trade_tape_quote_confirmed!==false||
      x.reference_market_cap_per_pbr_temporally_verified!==false||
      x.ranking_eligible!==false||f.ranking_eligible!==false||
      x.reference_feed_shares_ex_treasury!==f.shares_outstanding||
      !Number.isSafeInteger(x.newest_observed_sgx_shares_ex_treasury)||
      x.newest_observed_sgx_share_snapshot_date<(shareDay))
    throw Error("株式数と株価の照合ができない");
   return {symbol,shareDay,quoteDay,gap,
    officialDate:x.newest_observed_sgx_share_snapshot_date,
    officialShares:x.newest_observed_sgx_shares_ex_treasury,
    storedShares:f.shares_outstanding};
  });
 }
 const fmt=n=>n.toLocaleString("ja-JP");
 async function render(){
  const body=document.getElementById("shareDateRows"),status=document.getElementById("shareDateStatus");
  if(!body||!status)return;
  try{
   const [f,s]=await Promise.all(["./data/latest.json","./data/sgx-share-quote-date-v161.json"]
    .map(async u=>{const res=await fetch(u,{cache:"no-store"});if(!res.ok)throw Error("HTTP");return res.json()}));
   const list=validate(f,s);
   body.replaceChildren();
   for(const x of list){
    const tr=document.createElement("tr");
    for(const value of [x.symbol,x.shareDay,x.quoteDay,x.gap+"日",
      x.officialDate+" / "+fmt(x.officialShares)+"株",
      "基準日不一致・ランキング対象外"]){
      const td=document.createElement("td");td.textContent=value;tr.append(td);
    }
    body.append(tr);
   }
   status.textContent="参考株価と株式数の基準日に差がある。180日以内の株式数でも株価との日時整合は証明されない。SGX公式の約定価格も未確認。";
  }catch(e){
   body.replaceChildren();const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=6;td.textContent="データの版が異なるため診断結果を非表示";tr.append(td);body.append(tr);
   status.textContent="最新の株式数・株価基準日診断の再生成待ち";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
