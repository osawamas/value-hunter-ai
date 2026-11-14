#!/usr/bin/env node
"use strict";
/* v229 — offline review of manually staged, NOT source-authenticated SGX securities.
   Deliberately no HTTP, prices, ranking promotion, or writes to docs/.
   A code overlap is NOT a unique issuer link or source permission. */
const fs=require("node:fs");
const path=require("node:path");
const {inspect}=require("./classify-sgx-counters-v202.js");

const itemKeys=["instrument_type","listing_board","trading_code","trading_currency","trading_name"].sort();
function audit(staged,thirdParty,financial){
 const classified=inspect(staged);
 if(staged.source_authentication!=="NOT_INDEPENDENTLY_AUTHENTICATED"||
    staged.security_counter_not_necessarily_unique_issuer!==true||
    staged.source_url===undefined||
    !/^https:\/\/(?:www\.)?sgx\.com\//.test(staged.source_url) &&
     !/^https:\/\/links\.sgx\.com\//.test(staged.source_url)||
    !/^\d{4}-\d{2}-\d{2}$/.test(staged.as_of_date||"")||
    !/^[0-9a-f]{64}$/.test(staged.original_csv_sha256||""))
  throw Error("Unverified source or digest metadata has changed");
 for(const row of staged.items){
  if(JSON.stringify(Object.keys(row).sort())!==JSON.stringify(itemKeys))
   throw Error("Staged security fields unexpectedly include market/quote data");
 }
 if(thirdParty?.schema_version!=="sgx-third-party-company-candidates-v99"||
    thirdParty.full_sgx_listing_completeness_verified!==false||
    thirdParty.eligible_for_ranking!==false||
    !Array.isArray(thirdParty.candidates)||
    thirdParty.candidates.length!==thirdParty.provider_accepted_candidate_count||
    financial?.schema_version!=="value_hunter_web_v29"||
    financial.ranking_enabled!==false||financial.ranking_eligible_count!==0||
    !Array.isArray(financial.records)||financial.records.length!==financial.coverage?.registered_count)
   throw Error("Cannot review mismatched source populations");
 const findCodes=(items,field)=>{
  const set=new Set();
  for(const item of items){
   if(typeof item[field]!=="string"||!item[field].trim()||set.has(item[field]))
    throw Error("Invalid or duplicated reference identifier");
   set.add(item[field]);
  }
  return set;
 };
 const third=findCodes(thirdParty.candidates,"symbol");
 const registered=findCodes(financial.records,"symbol");
 const codes=classified.rows.map(x=>x.symbol);
 const uniqueCodes=new Set(codes);
 const classifiedCounterOverlaps=classified.rows.filter(x=>third.has(x.symbol));
 const registeredCounterOverlaps=classified.rows.filter(x=>registered.has(x.symbol));
 const countTypes=classified.counts;
 const unknown=classified.rows.filter(x=>x.category==="UNCLASSIFIED").map(x=>x.symbol);
 return {
  schema_version:"sgx-local-manual-staging-audit-v229",
  as_of_date:staged.as_of_date,
  original_csv_sha256:staged.original_csv_sha256,
  source_url_claim_unverified:staged.source_url,
  staged_security_counters:classified.total_counters,
  unique_trading_codes:uniqueCodes.size,
  duplicate_codes_across_currency_or_type:codes.length-uniqueCodes.size,
  classified_counter_counts:countTypes,
  unclassified_counter_codes:unknown,
  third_party_reference_count:third.size,
  financial_reference_count:registered.size,
  staged_counters_matching_third_party_code:classifiedCounterOverlaps.length,
  staged_counters_matching_registered_code:registeredCounterOverlaps.length,
  staged_distinct_codes_matching_third_party:[...new Set(classifiedCounterOverlaps.map(x=>x.symbol))].sort(),
  staged_distinct_codes_matching_financial:[...new Set(registeredCounterOverlaps.map(x=>x.symbol))].sort(),
  source_authenticated:false,full_official_master_verified:false,
  financial_issuer_identity_verified_from_code:false,
  permitted_to_redistribute_market_data:false,market_prices_extracted:false,
  registered_financial_count_increment:0,ranking_eligible_count:0,
  no_automatic_promotion:true,
  interpretation:"Identifier overlaps are research hints only. No additional companies are independently verified."
 };
}
function run(args=process.argv.slice(2)){
 const arg=name=>{const i=args.indexOf(name);return i>=0?args[i+1]:undefined};
 const input=arg("--staged"),output=arg("--out");
 if(!input||!output)throw Error("Usage: node scripts/audit-staged-sgx-universe-v229.js --staged LOCAL_STAGING.json --out LOCAL_AUDIT.json");
 const destination=path.resolve(output);
 const docs=path.resolve(__dirname,"../docs");
 if(destination===docs||destination.startsWith(docs+path.sep))
  throw Error("Refusing to publish unverified source comparison under docs/");
 const staged=JSON.parse(fs.readFileSync(input,"utf8"));
 const third=JSON.parse(fs.readFileSync(path.join(docs,"data/sgx-universe-candidates.json"),"utf8"));
 const feed=JSON.parse(fs.readFileSync(path.join(docs,"data/latest.json"),"utf8"));
 const summary=audit(staged,third,feed);
 fs.mkdirSync(path.dirname(destination),{recursive:true});
 fs.writeFileSync(destination,JSON.stringify(summary,null,2)+"\n",{flag:"wx"});
 process.stdout.write("Locally reviewed "+summary.staged_security_counters+" staged counters. Unverified; no prices or ranked securities.\n");
 return summary;
}
if(require.main===module){
 try{run()}catch(e){process.stderr.write("FAIL v229: "+String(e)+"\n");process.exitCode=1}
}
module.exports={audit,run};
