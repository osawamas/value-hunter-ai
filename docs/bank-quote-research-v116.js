/* v116: read-only, non-official, timestamped SGX bank market research panel. */
"use strict";
(function(root) {
 const BANKS=["D05","O39","U11"];
 function validate(daily,intraday,consistency) {
  if (daily?.schema_version!=="sgx-secondary-quote-probe-v112" ||
      daily.source_kind!=="YAHOO_UNOFFICIAL_DAILY_CHART" ||
      daily.promote_to_financial_feed!==false ||
      intraday?.schema_version!=="sgx-secondary-intraday-v114" ||
      intraday.research_provider!=="YAHOO_FINANCE_UNOFFICIAL" ||
      intraday.promoted_to_financial_feed!==false ||
      consistency?.schema_version!=="sgx-yahoo-daily-intraday-consistency-v115" ||
      consistency.same_provider_internal_consistency_only!==true ||
      consistency.official_exchange_confirmed_quotes!==0 ||
      consistency.ranking_eligible!==false)
   throw new Error("第三者市場データの区分・取得状態が不正");
  const rows=consistency.records;
  if (!Array.isArray(rows)||rows.length!==3||
      !Array.isArray(daily.records)||daily.records.length!==3||
      !Array.isArray(intraday.records)||intraday.records.length!==3)
    throw new Error("銀行3社の研究記録に不足");
  const lookup=new Map();
  for(const rec of rows) {
   if (!rec||!BANKS.includes(rec.symbol)||lookup.has(rec.symbol)||
       rec.provider_internal_only!==true||
       rec.sgx_trade_execution_timestamp_verified!==false||
       rec.valuation_eligible!==false||rec.ranking_eligible!==false||
       typeof rec.session_date_sgt!=="string"||
       !/^\d{4}-\d{2}-\d{2}$/.test(rec.session_date_sgt)||
       !/^\d{1,4}\.\d{2}$/.test(rec.daily_close_sgd)||
       !/^\d{1,4}\.\d{2}$/.test(rec.last_5m_bar_price_sgd))
    throw new Error("未検証の銀行株価状態");
   lookup.set(rec.symbol,rec);
  }
  for (const symbol of BANKS) {
    const a=daily.records.find(r=>r.symbol===symbol);
    const b=intraday.records.find(r=>r.symbol===symbol);
    const c=lookup.get(symbol);
    if (!a?.record||!b?.record||!c||
        a.record.symbol!==symbol||b.record.symbol!==symbol||
        a.record.daily_bar_date_sgt!==c.session_date_sgt||
        b.record.last_bar_date_sgt!==c.session_date_sgt||
        a.record.original_sgx_exchange_source_verified!==false||
        b.record.price_independently_exchange_confirmed!==false||
        a.record.usable_for_market_cap!==false||
        b.record.eligible_for_market_cap_per_pbr!==false||
        a.record.ranking_eligible!==false||b.record.ranking_eligible!==false||
        Math.abs(Number(a.record.close_sgd_research)-Number(c.daily_close_sgd))>0.005||
        Math.abs(Number(b.record.last_bar_price_sgd)-Number(c.last_5m_bar_price_sgd))>0.005)
      throw new Error("研究資料間の銘柄・価格・日付が一致しない");
  }
  return BANKS.map(symbol=>{
   const c=lookup.get(symbol);
   const stamp=intraday.records.find(r=>r.symbol===symbol).record.last_bar_timestamp_utc;
   const epoch=Date.parse(stamp);
   if (!Number.isFinite(epoch)||new Date(epoch).toLocaleDateString("en-CA",{timeZone:"Asia/Singapore"})!==c.session_date_sgt)
     throw new Error("最終5分足バーの時刻が不正");
   return {symbol,date:c.session_date_sgt,
    dailyClose:c.daily_close_sgd,last5m:c.last_5m_bar_price_sgd,
    lastBarAtSgt:new Date(epoch).toLocaleString("ja-JP",{
      timeZone:"Asia/Singapore",year:"numeric",month:"2-digit",day:"2-digit",
      hour:"2-digit",minute:"2-digit"}),
    equal:c.rounded_price_matches===true};
  });
 }
 function cell(tag,value) {const x=document.createElement(tag);x.textContent=value;return x;}
 async function load() {
  const body=document.getElementById("secondaryBankResearchRows");
  const status=document.getElementById("secondaryBankResearchStatus");
  if (!body||!status)return;
  try {
   const files=await Promise.all([
    "./data/sgx-bank-secondary-quotes-v112.json",
    "./data/sgx-bank-intraday-v114.json",
    "./data/sgx-bank-daily-intraday-v115.json"
   ].map(async path=>{
    const r=await fetch(path,{cache:"no-store"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    return r.json();
   }));
   const values=validate(...files);
   body.replaceChildren();
   for(const v of values) {
    const tr=document.createElement("tr");
    tr.append(cell("td",v.symbol),cell("td",v.date),cell("td",v.dailyClose+" SGD"),
      cell("td",v.last5m+" SGD"),cell("td",v.lastBarAtSgt+" SGT"),
      cell("td",v.equal?"同一提供元内で一致":"不一致"));
    body.append(tr);
   }
   status.textContent="Yahoo Financeの第三者参考データ。最終バー時刻は約定時刻ではない。SGX公式照合・独立株価検証は未完了。投資評価には使用しない。";
  } catch(error) {
   body.replaceChildren();
   const tr=document.createElement("tr");const td=cell("td","データ照合に失敗したため非表示");
   td.colSpan=6;tr.append(td);body.append(tr);
   status.textContent="研究データが不完全。SGX公式の株価として扱わない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root&&root.document)root.document.addEventListener("DOMContentLoaded",load);
})(typeof window!=="undefined"?window:null);
