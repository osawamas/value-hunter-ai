#!/usr/bin/env node
"use strict";
/* v295: compose existing narrowly sourced SGX historical code directory with
 * two separately proven 2026 IPO admission events. This is NOT an active
 * listing master, finance feed or licensed quote database.
 */
const fs=require("node:fs"),path=require("node:path");
const {buildExpanded}=require("../docs/sgx-historical-code-search-v258.js");
const {verify:verifyIPO}=require("./verify-sgx-october-ipo-v294.js");
const ROOT=path.resolve(__dirname,"..");
const SOURCES=[
 "docs/data/sgx-corporate-indexed-page-v253.json",
 "docs/data/sgx-official-issuer-code-filings-v255.json",
 "docs/data/sgx-net-eleven-codes-v256.json",
 "docs/data/sgx-official-batch-seed-v196.json",
 "docs/data/sgx-material-listing-events-v257.json",
 "docs/data/latest.json"
];
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),"utf8"));
function compose(historical,ipo,thirdParty,feed){
 if(!Array.isArray(historical)||historical.length!==30||
   new Set(historical.map(x=>x.code)).size!==30||
   historical.some(x=>x.ranking_eligible!==false||
       x.all_current_trading_verified!==false||
       x.financial_or_quote_verified!==false))
   throw Error("Historical SGX directory not the strictly unverified 30");
 const checked=verifyIPO(ipo);
 if(checked.confirmed_historical_event_count!==2)throw Error("SGX IPO admission evidence invalid");
 if(thirdParty?.schema_version!=="sgx-third-party-company-candidates-v99"||
   thirdParty.eligible_for_ranking!==false||
   thirdParty.full_sgx_listing_completeness_verified!==false||
   !Array.isArray(thirdParty.candidates)||
   thirdParty.candidates.length!==182||
   thirdParty.candidates.some(x=>x.ranking_eligible!==false||
       x.financial_verification!==false||
       x.source_verification!=="THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED"))
   throw Error("Third-party list unexpectedly authenticated or modified");
 if(feed?.ranking_eligible_count!==0||feed.ranking_enabled!==false||
   !Array.isArray(feed.records)||feed.records.length!==7||
   feed.records.some(x=>x.ranking_eligible!==false))
   throw Error("Published financial feed was promoted or changed");
 const known=new Map();
 for(const r of historical){
  if(!/^[A-Z0-9]{2,6}$/.test(r.code)||known.has(r.code))throw Error("Historical symbol duplicate");
  known.set(r.code,{symbol:r.code,issuer:r.name,isin:r.isin||null,
   primary_source_url:r.source,source_class:r.kind==="SGXNET"?
    "DATED_SGXNET_HISTORICAL_FILING":"SGX_STATIC_HISTORICAL_CODE",
   ipo_admission_event:false,ipo_effective_date:null,
   current_active_listing_verified:false,financials_verified:false,
   ranking_eligible:false});
 }
 const thirdSymbols=new Set();
 for(const row of thirdParty.candidates){
  if(!/^[A-Z0-9]{1,8}$/.test(row.symbol)||thirdSymbols.has(row.symbol))
   throw Error("Third-party duplicate/invalid symbol");
  thirdSymbols.add(row.symbol);
 }
 for(const r of checked.historical_confirmations){
  if(known.has(r.symbol))throw Error("SGX IPO event duplicates existing 30: "+r.symbol);
  known.set(r.symbol,{symbol:r.symbol,issuer:r.issuer,isin:r.isin,
   primary_source_url:r.original_listing_url,
   source_class:"ORIGINAL_SGX_ST_DATED_IPO_ADMISSION",
   ipo_admission_event:true,ipo_effective_date:r.effective_trading_date,
   current_active_listing_verified:false,financials_verified:false,
   ranking_eligible:false});
 }
 const entries=[...known.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol,"en"));
 const overlaps=entries.filter(x=>thirdSymbols.has(x.symbol)).map(x=>x.symbol);
 if(entries.length!==32||new Set(entries.map(x=>x.symbol)).size!==32)
   throw Error("32 known source identities not reconciled");
 if(entries.some(x=>x.ranking_eligible!==false||x.current_active_listing_verified!==false))
   throw Error("Invalid promotion");
 return {
  schema_version:"sgx-32-historical-source-candidate-stage-v295",
  created_from:"v259_historical_30_plus_v294_official_ipo_2",
  provenance:{historical_code_count:30,dated_sgx_st_ipo_count:2,
   third_party_candidate_count:182,overlap_with_third_party_count:overlaps.length,
   overlap_symbols:overlaps,
   confirmed_ipo_absent_from_third_party:checked.historical_confirmations
    .filter(x=>!thirdSymbols.has(x.symbol)).map(x=>x.symbol).sort()},
  total_distinct_historical_codes:entries.length,
  full_current_sgx_security_master_verified:false,
  current_listing_status_verified:false,
  financial_feed_modified:false,
  independent_financial_audit_verified:false,
  market_data_license_verified:false,
  investment_ranking_enabled:false,
  ranking_eligible_count:0,entries
 };
}
function build(){
 const inputs=SOURCES.map(read);
 const rows=buildExpanded(...inputs);
 return compose(rows,read("docs/data/sgx-october-ipo-listing-v294.json"),
  read("docs/data/sgx-universe-candidates.json"),inputs[5]);
}
if(require.main===module){
 const result=build();
 const output=path.join(ROOT,"build/research/sgx-32-historical-candidates-v295.json");
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
 console.log("v295: "+result.total_distinct_historical_codes+
  " dated sourced codes; IPO missing from third-party: "+
  result.provenance.confirmed_ipo_absent_from_third_party.join(",")+
  "; investable 0. Research staging only.");
}
module.exports={compose,build};
