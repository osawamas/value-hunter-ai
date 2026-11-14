#!/usr/bin/env node
"use strict";
/* Fail-closed evidence readiness derived from source sidecars.
 * Research only: no market quote feed, no web scraping, no ranking promotion.
 */
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function derive(buyback,actions,rights,feed){
 const row=buyback.rows?.at(-1);
 const source=actions.uob.observations?.find(x=>x.date===row?.trade_date);
 const matches=Boolean(source&&row&&buyback.symbol==="U11"&&
  buyback.source_kind==="SGX_ORIGINAL_ANNOUNCEMENT_HTML"&&
  source.official_verified===true&&source.origin==="OFFICIAL_SGX_ANNOUNCEMENT_HTML"&&
  source.announcement_reference===row.announcement_ref&&
  source.source_url===row.source_url&&
  source.issued_excluding_treasury_after===row.issued_excluding_treasury_after_purchase&&
  source.cancelled===row.cancelled&&
  actions.verified_as_of_date===row.trade_date&&
  buyback.official_current_asof_date===row.trade_date);
 const noLicense=rights.licensed_time_stamped_quote_available===false&&
  rights.feeds.every(x=>x.public_quote_redistribution_authorized===false&&x.can_enable_rankings===false);
 const safeFeed=feed.ranking_enabled===false&&feed.ranking_eligible_count===0;
 const uob={
  symbol:"U11",verified_historical_share_snapshot:matches,
  historical_as_of_date:matches?row.trade_date:null,
  historical_ex_treasury_shares:matches?row.issued_excluding_treasury_after_purchase:null,
  latest_nov13_official_original_obtained:false,
  source_status:matches?"HISTORICAL_SGX_ORIGINAL_MATCHED_NOT_CURRENT":"SOURCE_MISMATCH_BLOCKED",
  secondary_nov13_included:false,
  licensed_quote_available:false,
  live_valuation_allowed:false,ranking_eligible:false
 };
 const ocbcNotice=actions.ocbc.outstanding_change_notice||{};
 const ocbc={
  symbol:"O39",
  source_status:"SECONDARY_NOTICE_OFFICIAL_PDF_NOT_OBTAINED",
  original_attachment_verified:ocbcNotice.official_attachment_obtained===true,
  original_numeric_share_change_verified:ocbcNotice.share_change_verified===true,
  source_announcement_reference:ocbcNotice.announcement_reference||null,
  historical_ex_treasury_shares:null,live_valuation_allowed:false,ranking_eligible:false
 };
 const isSafe=matches&&noLicense&&safeFeed&&
  buyback.latest_2026_11_13_official_original_retrieved===false&&
  actions.uob.latest_unverified.official_verified===false&&
  actions.uob.latest_unverified.may_enter_ranking===false&&
  ocbcNotice.official_attachment_obtained===false&&
  ocbcNotice.share_change_verified===false&&
  ocbcNotice.may_enter_ranking===false;
 return {
  schema_version:"sgx-bank-share-evidence-decision-v243",
  source_scope:"ORIGINAL_SGX_HISTORICAL_BUYBACK_VS_SECONDARY_NOTICE",
  source_consistency_passed:isSafe,
  licensed_timestamped_quote_verified:false,
  redistribution_rights_verified:false,
  verified_full_sgx_universe:false,
  independent_financial_audit_verified:false,
  ranking_eligible_count:0,
  rankings_enabled:false,
  feed_modified:false,
  banks:[uob,ocbc],
  blockers:[
   "UOB_NOV13_OFFICIAL_ORIGINAL_NOT_VERIFIED",
   "OCBC_NOV12_ORIGINAL_PDF_NOT_VERIFIED",
   "LICENSED_QUOTE_AND_REDISTRIBUTION_RIGHTS_MISSING",
   "CURRENT_DATE_ISSUED_EX_TREASURY_NOT_VERIFIED",
   "INDEPENDENT_FINANCIAL_AUDIT_NOT_VERIFIED"
  ]
 };
}
function main(){
 const args=[
  read("docs/data/sgx-uob-official-buyback-v242.json"),
  read("docs/data/sgx-bank-corporate-actions-v190.json"),
  read("docs/data/sgx-source-rights-review-v222.json"),
  read("docs/data/latest.json")
 ];
 const result=derive(...args);
 if(!result.source_consistency_passed)throw Error("v243: inconsistent source evidence, refusing research output");
 const out=path.join(root,"build/research/sgx-bank-evidence-readiness-v243.json");
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
 console.log("v243 PASS: UOB dated source reconciled; OCBC original outstanding; quote/rights/ranking remain blocked");
}
if(require.main===module)main();
module.exports={derive};
