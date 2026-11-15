"use strict";
/* v294 SGX-ST primary listing events: historical dated admission only.
 * A listing-confirmation HTML establishes the event, NOT today's active
 * security master, licensing, financial audit or ranking eligibility.
 */
const fs=require("node:fs");
const path=require("node:path");
const EXPECTED={
 "9DC":{isin:"SGXE96931105",date:"2026-10-16",time:"09:00",
   reference:"SG261016OTHRW0SM",issuer:"DELUGE CORPORATION LIMITED"},
 "MIM":{isin:"SGXE49931863",date:"2026-10-28",time:"14:00",
   reference:"SG261027OTHR92A1",issuer:"MI MATERIAL HOLDING LIMITED"}
};
function validDate(s){
 if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;
 const dt=new Date(s+"T00:00:00Z");
 return Number.isFinite(+dt)&&dt.toISOString().slice(0,10)===s;
}
function verify(doc){
 if(!doc||doc.schema_version!=="sgx-october-ipo-official-listing-v294"||
   doc.original_source_type!=="SGXNET_EXCHANGE_LISTING_CONFIRMATION_HTML"||
   doc.full_active_sgx_master_verified!==false||
   doc.market_data_display_rights_verified!==false||
   doc.market_data_non_display_rights_verified!==false||
   doc.independent_financial_verification_complete!==false||
   doc.ranking_enabled!==false||doc.ranking_eligible_count!==0||
   doc.october_monthly_statistics_pdf_sha256!==null||
   doc.october_monthly_issuer_counts_verified!==false)
   throw Error("Listing evidence scope or master/rights claim invalid");
 const rows=doc.issuer_listing_confirmations;
 if(!Array.isArray(rows)||rows.length!==2)throw Error("Two independent original listing event rows required");
 const seen=new Set();
 for(const r of rows){
  const e=EXPECTED[r?.trading_code];
  if(!e||seen.has(r.trading_code))throw Error("Unexpected or repeated IPO counter");
  seen.add(r.trading_code);
  if(r.issuer_name!==e.issuer||r.isin!==e.isin||
     r.effective_trading_date!==e.date||!validDate(r.effective_trading_date)||
     r.effective_time_sgt!==e.time||
     r.announcement_reference!==e.reference||
     r.board!=="MAINBOARD"||
     r.event_type!=="EQUITY_LISTING_CONFIRMATION"||
     r.listed_trading_confirmed_asof_event!==true||
     r.currently_active_listing_verified!==false||
     r.quote_verified!==false||
     r.shares_ex_treasury_verified!==false||
     r.financials_verified!==false||
     r.ranking_eligible!==false||
     !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/[A-Z0-9]+\/[a-f0-9]+$/.test(r.source_url||""))
     throw Error("SGX primary listing row invalid: "+r.trading_code);
 }
 return {schema_version:"sgx-confirmed-october-ipo-identities-v294",
  historical_confirmations:rows.map(r=>({
    symbol:r.trading_code,issuer:r.issuer_name,isin:r.isin,
    effective_trading_date:r.effective_trading_date,
    original_listing_url:r.source_url,
    historical_original_sgxnet_listing_confirmed:true,
    current_active_status_verified:false,ranking_eligible:false
  })),
  confirmed_historical_event_count:2,full_security_master_verified:false,
  current_active_status_verified:false,latest_market_quote_available:false,
  independent_financial_audit_available:false,ranking_eligible_count:0};
}
if(require.main===module){
 const data=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../docs/data/sgx-october-ipo-listing-v294.json"),"utf8"));
 const result=verify(data);
 console.log("v294 PASS: "+result.historical_confirmations.map(x=>x.symbol+" "+x.isin).join(", ")+" SGX-ST original historical listings only");
}
module.exports={verify,validDate};
