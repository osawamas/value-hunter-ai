/* v168: reference valuations do NOT become current by a fresh JSON publish.
   Exact same-day checks are necessary, never sufficient for independent SGX quote approval.
   No API requests, no data mutation, no automatic ranking promotion. */
"use strict";
(function(root){
 function status(row){
   const shares=row?.shares_as_of_date,trade=row?.quote_timestamp_utc;
   if(typeof shares!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(shares)||
      typeof trade!=="string"||!/^\d{4}-\d{2}-\d{2}T/.test(trade)||
      !Number.isFinite(Date.parse(trade))||!Number.isFinite(Date.parse(shares+"T00:00:00Z")))
     return "UNKNOWN_DATE";
   if(shares!==trade.slice(0,10))return "DATE_MISMATCH";
   return "DATES_MATCH_BUT_ORIGINAL_SGX_PRICE_NOT_VERIFIED";
 }
 function canDisplayReferenceValuation(row){
   return false; // No verified authentic SGX trade-tape quote in the current financial feed.
 }
 function label(row){
   const s=status(row);
   if(s==="DATE_MISMATCH")return "—（株価と株式数の基準日不一致）";
   if(s==="UNKNOWN_DATE")return "—（基準日未確認）";
   return "—（正規SGX約定価格未検証）";
 }
 const api={status,canDisplayReferenceValuation,label};
 if(typeof module!=="undefined"&&module.exports)module.exports=api;
 if(root)root.VALUE_HUNTER_REF_VALUATION=api;
})(typeof window!=="undefined"?window:null);
