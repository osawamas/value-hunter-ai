#!/usr/bin/env node
"use strict";
/* v254: strict source intersection. The indexed name is NOT original SGX bytes;
 * the code is an independent official SGX static trading-board-lot excerpt.
 * This does NOT certify full listing completeness, licensing, prices or valuations.
 */
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const ONLY_MATCH=Object.freeze({
 "OVERSEA-CHINESE BANKING CORP":Object.freeze({official_issuer:"Oversea-Chinese Banking Corporation Ltd",symbol:"O39"})
});
function derive(indexed,official,feed){
 if(indexed?.schema_version!=="sgx-corporate-information-indexed-page-v253"||
    indexed.evidence_kind!=="SEARCH_ENGINE_INDEXED_OFFICIAL_SGX_PAGE_NOT_RAW_DOCUMENT"||
    indexed.source_page_direct_html_verified!==false||
    indexed.trading_codes_extracted!==false||
    indexed.full_official_security_master_verified!==false||
    indexed.records?.length!==20||
    official?.schema_version!=="sgx-official-first-batch-board-lot-v196"||
    official.source_url!=="https://www.sgx.com/securities/trading"||
    official.source_is_full_security_master!==false||
    official.official_full_security_master_obtained!==false||
    official.rows?.length!==11||
    feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)
  throw Error("Incorrect SGX provenance or investability gate");
 const matched=[],seenNames=new Set(),seenCodes=new Set();
 for(const row of indexed.records){
  if(typeof row.issuer_name!=="string"||seenNames.has(row.issuer_name)||
    row.trading_code!==null||row.trading_currency!==null||
    row.ranking_eligible!==false)
   throw Error("Name-only source became untrusted");
  seenNames.add(row.issuer_name);
  const exact=ONLY_MATCH[row.issuer_name];
  if(!exact)continue;
  const officialRows=official.rows.filter(x=>x.name===exact.official_issuer&&x.symbol===exact.symbol);
  if(officialRows.length!==1)throw Error("Official issuer-code identity mismatch");
  const verified=officialRows[0];
  if(row.listing_board!=="MAINBOARD"||verified.trading_currency!=="SGD"||
     verified.provenance!=="OFFICIAL_SGX_TRADING_PAGE_STATIC_BATCH"||
     verified.eligible_for_valuation!==false||seenCodes.has(verified.symbol))
   throw Error("SGX board/currency or official static-code source mismatch");
  seenCodes.add(verified.symbol);
  matched.push({
    indexed_company_name:row.issuer_name,listed_board_from_index:row.listing_board,
    code:verified.symbol,issuer_name_from_official_code_source:verified.name,
    currency_from_official_code_source:verified.trading_currency,
    indexed_name_source:indexed.origin_url,code_source:official.source_url,
    match_rule:"EXPLICITLY_REVIEWED_SINGLE_ISSUER_ALIAS",
    indexed_page_direct_html_authenticated:false,
    issuer_code_on_official_static_page:true,
    current_listing_independently_rechecked:false,
    licensed_market_quote_available:false,
    full_master_verified:false,ranking_eligible:false
  });
 }
 if(matched.length!==1||matched[0].code!=="O39")throw Error("Expected exact OCBC pair absent");
 return {
  schema_version:"sgx-indexed-name-to-official-code-join-v254",
  scope:"STRICT_INTERSECTION_OF_PARTIAL_INDEX_AND_STATIC_SGX_CODE_TABLE",
  name_only_index_records:indexed.records.length,
  linked_issuer_count:matched.length,
  unlinked_issuer_count:indexed.records.length-matched.length,
  inferred_missing_codes:0,
  current_all_sgx_listings_verified:false,
  full_security_master_verified:false,licensed_price_feed_verified:false,
  issuer_independent_financial_audit_verified:false,
  financial_feed_modified:false,ranking_eligible_count:0,
  matches:matched
 };
}
function main(){
 const result=derive(read("docs/data/sgx-corporate-indexed-page-v253.json"),
  read("docs/data/sgx-official-batch-seed-v196.json"),read("docs/data/latest.json"));
 const output=path.join(root,"build/research/sgx-indexed-to-official-code-v254.json");
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
 console.log("v254 PASS: 1 explicit source-backed code intersection O39; 19 left unlinked, ranking blocked");
}
if(require.main===module)try{main()}catch(e){console.error("v254 source mismatch: "+e.message);process.exitCode=1}
module.exports={derive};
