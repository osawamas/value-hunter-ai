"use strict";
const assert=require("node:assert/strict");
const {validate}=require("./share-date-v162.js");
function sample(){
 const feed={schema_version:"value_hunter_web_v29",ranking_enabled:false,
  ranking_eligible_count:0,updated_at_utc:"2026-11-14T07:08:54+00:00",
  records:["G13","S63"].map((symbol,i)=>({symbol,ranking_eligible:false,
  shares_as_of_date:"2026-06-30",quote_timestamp_utc:"2026-11-13T09:11:00+00:00",
  shares_outstanding:i?3119304988:12063642274}))};
 const side={schema_version:"sgx-share-price-date-coherence-v161",
  feed_updated_at_utc:feed.updated_at_utc,issuers_reviewed:2,
  mismatched_reference_date_count:2,official_trade_tape_verified_count:0,
  ranking_eligible_count:0,financial_feed_modified:false,
  records:feed.records.map(x=>({
   symbol:x.symbol,reference_share_snapshot_date:"2026-06-30",
   reference_quote_trading_date:"2026-11-13",share_quote_reference_date_gap_days:136,
   same_date_reconciled:false,newest_snapshot_is_currently_complete:false,
   official_trade_tape_quote_confirmed:false,
   reference_market_cap_per_pbr_temporally_verified:false,
   ranking_eligible:false,reference_feed_shares_ex_treasury:x.shares_outstanding,
   newest_observed_sgx_share_snapshot_date:x.symbol==="G13"?"2026-06-30":"2026-11-13",
   newest_observed_sgx_shares_ex_treasury:x.symbol==="G13"?12063642274:3115847115
  }))};
 return [feed,side];
}
assert.equal(validate(...sample())[0].gap,136);
for(const modify of [
 ([f,s])=>s.feed_updated_at_utc="old",
 ([f,s])=>s.records[0].share_quote_reference_date_gap_days=0,
 ([f,s])=>s.records[1].same_date_reconciled=true,
 ([f,s])=>s.records[1].reference_market_cap_per_pbr_temporally_verified=true,
 ([f,s])=>f.records[1].shares_outstanding=0,
 ([f,s])=>f.ranking_eligible_count=1
]){
 const input=sample();modify(input);assert.throws(()=>validate(...input));
}
console.log("v162 shares-date and trade-date mismatch UI fail closed");
