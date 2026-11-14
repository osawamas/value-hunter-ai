"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./bank-quote-research-v116.js");
function fixtures(){
 const symbols=["D05","O39","U11"],prices=[69.9,28.53,37.75];
 const daily={schema_version:"sgx-secondary-quote-probe-v112",
              source_kind:"YAHOO_UNOFFICIAL_DAILY_CHART",
              promote_to_financial_feed:false,records:[]};
 const intra={schema_version:"sgx-secondary-intraday-v114",
              research_provider:"YAHOO_FINANCE_UNOFFICIAL",
              promoted_to_financial_feed:false,records:[]};
 const match={schema_version:"sgx-yahoo-daily-intraday-consistency-v115",
              same_provider_internal_consistency_only:true,
              official_exchange_confirmed_quotes:0,ranking_eligible:false,records:[]};
 symbols.forEach((s,i)=>{
  daily.records.push({symbol:s,record:{
   symbol:s,daily_bar_date_sgt:"2026-11-13",close_sgd_research:prices[i],
   original_sgx_exchange_source_verified:false,usable_for_market_cap:false,ranking_eligible:false}});
  intra.records.push({symbol:s,record:{
   symbol:s,last_bar_date_sgt:"2026-11-13",last_bar_price_sgd:prices[i],
   last_bar_timestamp_utc:"2026-11-13T09:00:00+00:00",
   price_independently_exchange_confirmed:false,eligible_for_market_cap_per_pbr:false,
   ranking_eligible:false}});
  match.records.push({symbol:s,session_date_sgt:"2026-11-13",
   daily_close_sgd:prices[i].toFixed(2),last_5m_bar_price_sgd:prices[i].toFixed(2),
   provider_internal_only:true,sgx_trade_execution_timestamp_verified:false,
   valuation_eligible:false,ranking_eligible:false,rounded_price_matches:true});
 });
 return [daily,intra,match];
}
assert.equal(validate(...fixtures()).length,3);
const changes=[
 ([d,i,m])=>m.official_exchange_confirmed_quotes=3,
 ([d,i,m])=>m.records[0].ranking_eligible=true,
 ([d,i,m])=>i.records[0].record.price_independently_exchange_confirmed=true,
 ([d,i,m])=>d.records[0].record.close_sgd_research=70.14,
 ([d,i,m])=>i.records[0].record.last_bar_timestamp_utc="2026-11-12T09:00:00Z",
 ([d,i,m])=>m.records.pop()
];
for(const mutate of changes){const data=fixtures();mutate(data);assert.throws(()=>validate(...data));}
console.log("v116 non-official SGX bank chart UI guard passed");
