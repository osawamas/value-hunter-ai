"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {stage}=require("../scripts/stage-sgx-issuer-directory-v230.js");
const csv=[
 "Company Name,Country,Listing Board,Listed Date,Stock Code,Last,Volume",
 '"Oceanus Group Limited",Singapore,Mainboard,2009-05-25,579,0.01,1000',
 '"Octopus (APAC) Holdings Ltd.",Singapore,Catalist,2016-01-18,1F1,0.02,999',
 '"Olam Group Limited",Singapore,Mainboard,2022-03-16,VC2,0.03,1000'
].join("\r\n")+"\r\n";
const opts={as_of_date:"2026-11-14",
 source_url:"https://www.sgx.com/securities/corporate-information?page=24",
 original_csv_sha256:"a".repeat(64)};
const out=stage(csv,opts);
assert.equal(out.issuer_count,3);
assert.deepEqual(out.issuers.map(x=>x.issuer_name),[
 "Oceanus Group Limited","Octopus (APAC) Holdings Ltd.","Olam Group Limited"]);
assert.deepEqual(out.issuers.map(x=>x.listing_board),["MAINBOARD","CATALIST","MAINBOARD"]);
assert.deepEqual(out.issuers.map(x=>x.directory_listed_date),["2009-05-25","2016-01-18","2022-03-16"]);
assert.equal(out.company_names_not_ticker_mapping,true);
assert.equal(out.source_authentication,"MANUAL_TRANSCRIPTION_NOT_INDEPENDENTLY_AUTHENTICATED");
assert.equal(out.official_complete_issuer_master_verified,false);
assert.equal(out.public_redistribution_rights_verified,false);
assert.equal(out.securities_master_verified,false);
assert.equal(out.quote_data_collected,false);
assert.equal(out.ranking_enabled,false);
assert.equal(out.ranking_eligible_count,0);
for(const r of out.issuers){
 assert.deepEqual(Object.keys(r),["issuer_name","listing_board","country",
  "directory_listed_date","isin","sgx_trading_code",
  "linked_securities_verified","listed_issuer_verified","ranking_eligible"]);
 assert.equal(r.sgx_trading_code,null);
 assert.equal(r.isin,null);
 assert.equal(r.listed_issuer_verified,false);
 assert.equal(r.ranking_eligible,false);
}
assert.ok(!JSON.stringify(out).includes("1F1"));
assert.ok(!JSON.stringify(out).includes('"Last"'));
for(const change of [
 ()=>stage(csv,{...opts,source_url:"https://sgx.com/securities/corporate-information"}),
 ()=>stage(csv,{...opts,source_url:"https://www.sgx.com/securities/securities-prices"}),
 ()=>stage(csv,{...opts,source_url:"https://www.sgx.com/securities/corporate-information?code=stocks"}),
 ()=>stage(csv,{...opts,original_csv_sha256:"unverified"}),
 ()=>stage(csv,{...opts,as_of_date:"2026-02-30"}),
 ()=>stage(csv+"Oceanus Group Limited,Singapore,Mainboard,2009-05-25,579,1,1\n",opts),
 ()=>stage(csv.replace("Mainboard","UNKNOWN BOARD"),opts),
 ()=>stage(csv.replace("2016-01-18","2016-02-30"),opts),
 ()=>stage(csv.replace("Country","Stock Price"),opts),
 ()=>stage('Company Name,Country,Listing Board\n"Broken CSV,Singapore,Mainboard',opts)
])assert.throws(change);
console.log("v230 PASS: issuer-only manual directory stage preserves origin, strips tickers/quotes and blocks false official coverage");
