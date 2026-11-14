#!/usr/bin/env node
"use strict";
/* v256: 20/20 source-backed historical name/code matches across three data sources.
 * Not an official complete SGX master, nor proof of active listing, quote or valuation.
 */
const fs=require("node:fs"),path=require("node:path");const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const {derive:deriveV254}=require("./reconcile-sgx-official-code-v254.js");
const expected=Object.freeze({
 "OCTOPUS (APAC) HOLDINGS LTD.":"43A|SG1CF0000001|SG260812OTHR3OBX",
 "OIO HOLDINGS LIMITED":"KUX|SGXE73993458|SG260410OTHRZ71Y",
 "OLAM GROUP LIMITED":"VC2|SGXE65760014|SG260814DVCACQHU",
 "ONEAPEX LIMITED":"5SY|SG2C90967473|SG260722DECRDHI0",
 "OTS HOLDINGS LIMITED":"OTS|SGXE18096938|SG261015OTHR6TIG",
 "OUE REIT":"TS0U|SG2G60000004|SG260923OTHRY6XX",
 "OUHUA ENERGY HOLDINGS LIMITED":"AJ2|BMG6843Q1033|SG260813OTHR4YWA",
 "OVERSEAS EDUCATION LIMITED":"RQ1|SG2F49989922|SG260410OTHRPR4P",
 "OXLEY HOLDINGS LIMITED":"5UX|SG2F25986140|SG260829OTHR94HJ",
 "PACIFIC ANDES RESOURCES DEVLTD":"P11|BMG6845B1046|SG261016OTHRODOS",
 "PACIFIC CENTURY REGIONAL DEVTS":"P15|SG1J17886040|SG260331OTHRGORS"
});
function integrate(indexed,first,evidence,old,feed){
 if(indexed?.schema_version!=="sgx-corporate-information-indexed-page-v253"||
    indexed.records?.length!==20||indexed.trading_codes_extracted!==false||
    indexed.source_page_direct_html_verified!==false||
    first?.schema_version!=="sgx-official-announcement-issuer-codes-v255"||
    first.records?.length!==8||first.all_sgx_security_master_verified!==false||
    evidence?.schema_version!=="sgx-net-eleven-additional-counter-identity-v256"||
    evidence.records?.length!==11||
    evidence.direct_raw_html_bytes_sha256_verified!==false||
    evidence.exhaustive_current_sgx_master_verified!==false||
    evidence.all_current_listing_status_verified!==false||
    evidence.ranking_eligible_count!==0||
    old?.schema_version!=="sgx-indexed-name-to-official-code-join-v254"||
    old.matches?.length!==1||old.matches[0]?.code!=="O39"||
    old.ranking_eligible_count!==0||
    feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)throw Error("Source classification or ranking gates changed");
 const byName=new Map(),codes=new Set(),isins=new Set();
 for(const x of indexed.records){
  if(!x.issuer_name||byName.has(x.issuer_name)||x.trading_code!==null||x.trading_currency!==null)
   throw Error("Indexed issuer source altered");
  byName.set(x.issuer_name,null);
 }
 for(const r of evidence.records){
  const pinned=expected[r.issuer_name];
  if(!pinned||[r.code,r.isin,r.filing_reference].join("|")!==pinned||
    !byName.has(r.issuer_name)||byName.get(r.issuer_name)!==null||
    !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/[A-Z0-9]{16}(?:\/|$)/.test(r.source_url)||
    !/^2026-\d{2}-\d{2}$/.test(r.announcement_date)||
    r.identity_observed_in_sgxnet_filing!==true||
    r.current_listing_verified!==false||r.complete_universe_verified!==false||
    r.ranking_eligible!==false)throw Error("Untrusted additional SGXNet security identity");
  byName.set(r.issuer_name,{issuer_name:r.issuer_name,code:r.code,isin:r.isin,source:r.source_url,announced_on:r.announcement_date,source_level:"SGXNET_INDEXED_ANNOUNCEMENT_TEXT"});
 }
 for(const r of first.records){
  if(!byName.has(r.issuer_name)||byName.get(r.issuer_name)!==null||
     r.source_security_identity_verified_asof_announcement!==true||
     r.current_trading_quote_verified!==false||
     r.ranking_eligible!==false)throw Error("v255 original issuer identity mismatch");
  byName.set(r.issuer_name,{issuer_name:r.issuer_name,code:r.trading_code,isin:r.isin,source:r.source_url,announced_on:r.announced_on,source_level:"SGXNET_INDEXED_ANNOUNCEMENT_TEXT"});
 }
 const o=old.matches[0];
 if(!byName.has(o.indexed_company_name)||byName.get(o.indexed_company_name)!==null||
    o.issuer_code_on_official_static_page!==true||
    o.current_listing_independently_rechecked!==false||
    o.ranking_eligible!==false)throw Error("v254 official code mismatch");
 byName.set(o.indexed_company_name,{issuer_name:o.indexed_company_name,code:o.code,isin:null,source:o.code_source,announced_on:null,source_level:"SGX_OFFICIAL_STATIC_TRADING_TABLE"});
 const rows=[];
 for(const [name,r] of byName){
  if(!r||codes.has(r.code)||(r.isin!==null&&isins.has(r.isin)))throw Error("Missing or duplicated issuer/counter intersection");
  codes.add(r.code);if(r.isin!==null)isins.add(r.isin);
  rows.push({...r,current_listing_verified:false,trade_price_verified:false,ranking_eligible:false});
 }
 if(rows.length!==20||codes.size!==20||isins.size!==19)throw Error("Incomplete v256 source-backed intersections");
 return {schema_version:"sgx-twenty-indexed-company-code-intersection-v256",
  count_indexed_companies:20,distinct_dated_trading_codes:20,
  issuer_codes_from_announcement_index:19,issuer_codes_from_static_sgx_table:1,
  direct_original_html_bytes_retrieved_for_all:false,
  all_current_sgx_issuers_or_counters_present:false,
  official_complete_sgx_security_master:false,
  full_quote_and_redistribution_licence:false,
  independent_financial_figure_audit:false,ranking_eligible_count:0,
  warning:"The 20/20 result is coverage only of a single indexed page; not a full or current SGX universe.",
  records:rows};
}
function main(){
 const p=integrate(read("docs/data/sgx-corporate-indexed-page-v253.json"),
  read("docs/data/sgx-official-issuer-code-filings-v255.json"),
  read("docs/data/sgx-net-eleven-codes-v256.json"),
  deriveV254(read("docs/data/sgx-corporate-indexed-page-v253.json"),read("docs/data/sgx-official-batch-seed-v196.json"),read("docs/data/latest.json")),
  read("docs/data/latest.json"));
 const out=path.join(root,"build/research/sgx-twenty-codes-v256.json");
 fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(p,null,2)+"\n");
 console.log("v256 PASS: 20/20 dated code links on one indexed SGX page; no full-universe or live-valuation promotion");
}
if(require.main===module)try{main()}catch(e){console.error("v256 blocked: "+e.message);process.exitCode=1}
module.exports={integrate};
