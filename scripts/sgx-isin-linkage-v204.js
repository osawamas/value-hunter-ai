"use strict";
/* v204: validate internationally standardized ISIN *format/check digit*.
   A correct checksum does not prove a code is issued by a specific company.
   Matching ISIN across currencies means same security identifier, NOT independent
   verification of issuer ownership, current SGX listing or lawful market data. */
(function(root){
 function validIsin(input){
  if(typeof input!=="string"||!/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(input))return false;
  let digits="";
  for(const c of input){
   const n=c.charCodeAt(0);
   if(n>=48&&n<=57)digits+=c;
   else digits+=String(n-55);
  }
  let sum=0,alternate=false;
  for(let i=digits.length-1;i>=0;i--){
   let x=digits.charCodeAt(i)-48;
   if(alternate)x*=2;
   sum+=Math.floor(x/10)+x%10;
   alternate=!alternate;
  }
  return sum%10===0;
 }
 function reconcile(staged,identifiers){
  if(staged?.schema_version!=="sgx-manual-security-list-staging-v199"||
    staged.original_file_is_sgx_verified!==false||
    staged.full_sgx_universe_verified!==false||
    staged.quote_columns_stripped!==true||
    staged.licensed_quote_access!==false||
    staged.ranking_eligible_count!==0||
    !Array.isArray(staged.items)||
    !Array.isArray(identifiers))throw Error("Source staging not trusted");
  const keys=new Map();
  for(const x of staged.items){
   const key=[x.trading_code,x.trading_currency,x.instrument_type].join("|");
   if(keys.has(key))throw Error("Duplicate securities counter");
   keys.set(key,x);
  }
  const seen=new Set(),records=[];
  for(const entry of identifiers){
   const {trading_code,trading_currency,instrument_type,isin,source_url,
    assertion_level}=entry||{};
   const key=[trading_code,trading_currency,instrument_type].join("|");
   if(seen.has(key)||!keys.has(key))throw Error("Identifier mapping mismatch");
   seen.add(key);
   if(!validIsin(isin)||!/^https:\/\//.test(source_url||"")||
      assertion_level!=="MANUAL_UNVERIFIED_EVIDENCE")
    throw Error("ISIN checksum or evidence classification invalid");
   records.push({trading_code,trading_currency,instrument_type,isin,
    same_security_identifier_only:true,
    issuer_entity_verified:false,sgx_listing_verified:false,
    third_party_financial_audit_verified:false,
    current_share_count_verified:false,quote_license_verified:false,
    ranking_eligible:false});
  }
  const groups={};
  for(const r of records)(groups[r.isin]??=[]).push(r);
  return {mapping_rows:records,by_isin:groups,
   validated_isin_checksums:records.length,
   verified_issuer_links:0,investment_ranking_eligible:0,
   same_isin_is_not_independent_issuer_verification:true};
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validIsin,reconcile};
})(typeof window!=="undefined"?window:null);
