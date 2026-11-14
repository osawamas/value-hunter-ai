#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const EXPECTED=Object.freeze({
 "OCEANUS GROUP LIMITED":"579|SG1M80907371|SG260814OTHROJYF",
 "OILTEK INTERNATIONAL LIMITED":"HQU|SGXE21569376|SG260410OTHRH0PY",
 "OKP HOLDINGS LIMITED":"5CF|SG1M55904841|SG260401OTHRXIAW",
 "OLD CHANG KEE LTD.":"5ML|SG1W49939232|SG261113OTHR9OGS",
 "OSSIA INTERNATIONAL LTD":"O08|SG1D61018413|SG260629OTHR4XNV",
 "OUE HEALTHCARE LIMITED":"5WA|SG2F86994413|SG260824OTHRTOJR",
 "OUE LIMITED":"LJ3|SG2B80958517|SG261102OTHRXFXJ",
 "OXPAY FINANCIAL LIMITED":"TVV|SGXE15822534|SG260813OTHRH7WL"
});
function derive(indexed,filings,feed){
 if(indexed?.schema_version!=="sgx-corporate-information-indexed-page-v253"||
   indexed.records?.length!==20||indexed.trading_codes_extracted!==false||
   indexed.source_page_direct_html_verified!==false||
   indexed.full_official_security_master_verified!==false||
   filings?.schema_version!=="sgx-official-announcement-issuer-codes-v255"||
   filings.source_kind!=="SGXNET_ORIGINAL_ISSUER_SECURITY_ANNOUNCEMENT_HTML"||
   filings.records?.length!==8||
   filings.all_sgx_security_master_verified!==false||
   filings.all_codes_currently_listed_verified!==false||
   filings.ranking_eligible_count!==0||
   feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)
  throw Error("Inconsistent SGX record classes");
 const seen=new Set(),codeSeen=new Set(),matched=[];
 const indexedNames=new Set(indexed.records.map(x=>x.issuer_name));
 if(indexedNames.size!==20)throw Error("Duplicate indexed company name");
 for(const row of filings.records){
  const exact=EXPECTED[row.issuer_name];
  if(!exact||[row.trading_code,row.isin,row.announcement_ref].join("|")!==exact||
     !indexedNames.has(row.issuer_name)||
     !/^[A-Z0-9]{2,6}$/.test(row.trading_code)||
     !/^SG[A-Z0-9]{10}$/.test(row.isin)||
     !/^2026-\d{2}-\d{2}$/.test(row.announced_on)||
     !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/[A-Z0-9]{16}(\/|$)/.test(row.source_url)||
     !row.source_security_identity_verified_asof_announcement||
     row.current_trading_quote_verified!==false||
     row.share_count_verified!==false||
     row.ranking_eligible!==false||
     seen.has(row.issuer_name)||codeSeen.has(row.trading_code))
   throw Error("Unverified SGX issuer identity or duplicated trading code");
  seen.add(row.issuer_name);codeSeen.add(row.trading_code);
  matched.push({issuer_name:row.issuer_name,code:row.trading_code,isin:row.isin,
   announcement_ref:row.announcement_ref,announcement_date:row.announced_on,
   official_source_url:row.source_url,
   asof_dated_filing_identity_only:true,active_current_listing_verified:false,
   quote_redistribution_rights_verified:false,ranking_eligible:false});
 }
 if(matched.length!==8)throw Error("Incomplete original announcement source batch");
 for(const record of indexed.records){
  if(record.trading_code!==null||record.trading_currency!==null)throw Error("Indexed codes must remain null");
 }
 return {schema_version:"sgx-indexed-issuer-direct-filings-join-v255",
  partial_index_records:indexed.records.length,
  issuer_codes_from_sgxnet_filings:matched.length,
  issuer_codes_missing_from_original_filings:12,
  source_covers_complete_sgx:false,
  code_provenance:"DATED_OFFICIAL_SGXNET_ISSUER_SECURITY_FILINGS",
  current_active_listing_all_verified:false,official_full_master_verified:false,
  financial_feed_modified:false,licensed_timestamped_quote_verified:false,
  ranking_eligible_count:0,rows:matched.sort((a,b)=>a.issuer_name.localeCompare(b.issuer_name))};
}
function main(){
 const out=derive(read("docs/data/sgx-corporate-indexed-page-v253.json"),
  read("docs/data/sgx-official-issuer-code-filings-v255.json"),read("docs/data/latest.json"));
 const p=path.join(root,"build/research/sgx-direct-filing-issuer-code-v255.json");
 fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,JSON.stringify(out,null,2)+"\n");
 console.log("v255 PASS: 8 official SGXNet announcement issuer/security code identities, not current full listing");
}
if(require.main===module)try{main()}catch(e){console.error("v255 failed: "+e.message);process.exitCode=1}
module.exports={derive};
