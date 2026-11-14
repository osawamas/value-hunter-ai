"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const d=JSON.parse(fs.readFileSync("docs/data/sgx-corporate-indexed-page-v253.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function validate(x,f){
 assert.equal(x.schema_version,"sgx-corporate-information-indexed-page-v253");
 assert.equal(x.origin_url,"https://www.sgx.com/securities/corporate-information?page=24");
 assert.equal(x.evidence_kind,"SEARCH_ENGINE_INDEXED_OFFICIAL_SGX_PAGE_NOT_RAW_DOCUMENT");
 assert.equal(x.page_number,24);
 assert.equal(x.source_displayed_range,"461-480");
 assert.equal(x.source_displayed_total_records,727);
 assert.equal(x.source_records_preserved,20);
 assert.equal(x.scope,"COMPANY_NAMES_AND_LISTING_BOARDS_ONLY");
 for(const flag of ["source_count_asof_date_verified","trading_codes_extracted",
   "source_page_direct_html_verified","full_official_security_master_verified",
   "license_for_public_redistribution_verified","price_feed_available",
   "financial_feed_modified","ranking_eligible"])assert.equal(x[flag],false);
 assert.equal(x.records.length,20);
 assert.equal(new Set(x.records.map(r=>r.issuer_name)).size,20);
 for(let i=0;i<20;i++){
  const r=x.records[i];
  assert.equal(r.page_ordinal,461+i);
  assert.equal(r.trading_code,null);
  assert.equal(r.trading_currency,null);
  assert.ok(["MAINBOARD","CATALIST"].includes(r.listing_board));
  assert.equal(r.issuer_specific_official_filing_matched,false);
  assert.equal(r.ranking_eligible,false);
 }
 assert.deepEqual(x.records.filter(r=>r.issuer_name==="OVERSEA-CHINESE BANKING CORP")
  .map(r=>[r.page_ordinal,r.listing_board,r.trading_code]),[[475,"MAINBOARD",null]]);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 return true;
}
validate(d,feed);
for(const edit of [
 (x,f)=>{x.records[14].trading_code="O39"},
 (x,f)=>{x.records[14].trading_currency="SGD"},
 (x,f)=>{x.source_page_direct_html_verified=true},
 (x,f)=>{x.full_official_security_master_verified=true},
 (x,f)=>{x.trading_codes_extracted=true},
 (x,f)=>{x.source_count_asof_date_verified=true},
 (x,f)=>{x.records[0].page_ordinal=463},
 (x,f)=>{x.records[1].issuer_name=x.records[0].issuer_name},
 (x,f)=>{x.records[0].listing_board="NOT_SGX"},
 (x,f)=>{x.records[0].ranking_eligible=true},
 (x,f)=>{f.ranking_eligible_count=1}
]){
 const a=structuredClone(d),b=structuredClone(feed);
 edit(a,b);assert.throws(()=>validate(a,b));
}
console.log("v253 PASS: 20 indexed official-site names and boards; no invented codes, full master, quote rights or rankings");
