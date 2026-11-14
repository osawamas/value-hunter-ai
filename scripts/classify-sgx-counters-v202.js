"use strict";
/* v202: deterministic classification for a *staged* SGX securities catalogue.
   It is not proof of official coverage, equity eligibility, or market data rights.
   Counters and issuers are different objects. Unknown types never become companies. */
(function(root){
 const strictEquityTypes=new Set(["ORDINARY SHARE","ORDINARY SHARES","COMMON SHARE","COMMON STOCK","EQUITY","STOCK"]);
 const otherCategories=new Map([
  ["REIT","REIT"],["REAL ESTATE INVESTMENT TRUST","REIT"],
  ["ETF","ETF"],["EXCHANGE TRADED FUND","ETF"],
  ["BUSINESS TRUST","BUSINESS_TRUST"],
  ["STAPLED SECURITY","STAPLED_SECURITY"],["STAPLED SECURITIES","STAPLED_SECURITY"],
  ["L&I PRODUCT","LEVERAGED_PRODUCT"],
  ["WARRANT","WARRANT"],["STRUCTURED WARRANT","WARRANT"],
  ["DLC","LEVERAGED_PRODUCT"],["DAILY LEVERAGE CERTIFICATE","LEVERAGED_PRODUCT"],
  ["BOND","DEBT"],["NOTE","DEBT"],["DEBT","DEBT"]
 ]);
 function typeCategory(raw){
  const t=String(raw||"").trim().toUpperCase().replace(/\s+/g," ");
  if(strictEquityTypes.has(t))return "POTENTIAL_EQUITY";
  return otherCategories.get(t)||"UNCLASSIFIED";
 }
 function inspect(staged){
  if(staged?.schema_version!=="sgx-manual-security-list-staging-v199"||
   staged.original_file_is_sgx_verified!==false||
   staged.full_sgx_universe_verified!==false||
   staged.quote_columns_stripped!==true||
   staged.licensed_quote_access!==false||
   staged.distribution_rights_reviewed!==false||
   staged.ranking_enabled!==false||staged.ranking_eligible_count!==0||
   !Array.isArray(staged.items)||staged.items.length!==staged.item_count)
   throw Error("Staging status not verified for classification");
  const summary={POTENTIAL_EQUITY:0,REIT:0,ETF:0,BUSINESS_TRUST:0,STAPLED_SECURITY:0,WARRANT:0,LEVERAGED_PRODUCT:0,DEBT:0,UNCLASSIFIED:0};
  const keys=new Set(),rows=[];
  for(const x of staged.items){
   const code=x?.trading_code,cur=x?.trading_currency,typ=x?.instrument_type;
   if(typeof code!=="string"||! /^[A-Z0-9]{1,8}$/.test(code)||
    typeof cur!=="string"||! /^[A-Z]{3}$/.test(cur)||
    typeof x.trading_name!=="string"||!x.trading_name.trim()||
    typeof typ!=="string")throw Error("Invalid staged identity");
   const key=[code,cur,typ].join("|");
   if(keys.has(key))throw Error("Duplicate security counter");
   keys.add(key);
   const category=typeCategory(typ);
   summary[category]++;
   rows.push({symbol:code,currency:cur,security_type:typ,category,
    is_validated_company_issuer:false,valuation_ready:false,ranking_eligible:false});
  }
  if(Object.values(summary).reduce((a,b)=>a+b,0)!==staged.item_count)
   throw Error("Security type counts mismatch");
  return {status:"STAGING_ONLY_NOT_OFFICIAL_MASTER",counts:summary,total_counters:rows.length,
   candidate_equity_counters_not_verified_issuers:summary.POTENTIAL_EQUITY,rows};
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={inspect,typeCategory};
})(typeof window!=="undefined"?window:null);
