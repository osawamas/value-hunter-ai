"use strict";
const assert=require("node:assert/strict");
const {validateUniverse}=require("./universe.js");
function fixture(){
 const candidates=Array.from({length:24},(_,i)=>({
  symbol:"X"+String(i).padStart(3,"0"),display_name:"Example Holdings Limited "+i,
  source_verification:"THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED",
  financial_verification:false,ranking_eligible:false
 }));
 return {schema_version:"sgx-third-party-company-candidates-v99",
         coverage:"PARTIAL_UNVERIFIED",
         full_sgx_listing_completeness_verified:false,
         eligible_for_ranking:false,
         records_not_added_to_verified_financial_feed:true,
         provider_accepted_candidate_count:candidates.length,candidates};
}
assert.equal(validateUniverse(fixture()).candidates.length,24);
const cases=[
 d=>{d.coverage="COMPLETE";},
 d=>{d.full_sgx_listing_completeness_verified=true;},
 d=>{d.candidates[1].financial_verification=true;},
 d=>{d.candidates[1].ranking_eligible=true;},
 d=>{d.candidates[1].symbol="../evil";},
 d=>{d.candidates[1].symbol=d.candidates[0].symbol;},
 d=>{d.provider_accepted_candidate_count++;},
 d=>{d.candidates=[];},
 d=>{d.candidates[0].source_verification="EXCHANGE_OFFICIAL";},
];
for(const change of cases){
 const data=fixture();change(data);
 assert.throws(()=>validateUniverse(data));
}
console.log("v100: partial candidate directory UI schema and fail-closed validations OK");
