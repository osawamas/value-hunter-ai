#!/usr/bin/env node
"use strict";
// Historical source identity triage only. Never infers active listing or valuations.
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const {integrate}=require("./integrate-sgx-twenty-v256.js");
const {derive}=require("./reconcile-sgx-official-code-v254.js");
const priorities={"P11":"RESTRUCTURING_LIQUIDATION_RISK","5WA":"SCHEME_OF_ARRANGEMENT","5SY":"CAPITAL_REDUCTION","VC2":"MULTIPLE_SECURITY_TYPES","43A":"RENAME_OR_CHANGE_HISTORY","TS0U":"REIT_NOT_OPERATING_COMPANY"};
function build(){
 const index=read("docs/data/sgx-corporate-indexed-page-v253.json"),first=read("docs/data/sgx-official-issuer-code-filings-v255.json"),extra=read("docs/data/sgx-net-eleven-codes-v256.json"),feed=read("docs/data/latest.json");
 const v256=integrate(index,first,extra,derive(index,read("docs/data/sgx-official-batch-seed-v196.json"),feed),feed);
 if(v256.records.length!==20||feed.ranking_eligible_count!==0||feed.ranking_enabled!==false)throw Error("Scope or ranking guard changed");
 const rows=v256.records.map(x=>({issuer_name:x.issuer_name,code:x.code,isin:x.isin,source_url:x.source,source_date:x.announced_on,review_priority:priorities[x.code]?"HIGH":"NORMAL",review_reason:priorities[x.code]||"CURRENT_LISTING_UNVERIFIED",current_listing_verified:false,delisted_verified:false,suspended_verified:false,quote_verified:false,ranking_eligible:false}));
 rows.sort((a,b)=>(b.review_priority==="HIGH")-(a.review_priority==="HIGH")||a.issuer_name.localeCompare(b.issuer_name));
 return {schema_version:"sgx-listing-risk-triage-v257",scope:"ONE indexed SGX company page, 20 historical code identities only",total:20,high_priority:rows.filter(x=>x.review_priority==="HIGH").length,verified_current_listings:0,confirmed_delistings:0,licensed_quotes:0,ranking_eligible_count:0,warning:"Review flags are NOT findings of delisting, suspension or current listing.",records:rows};
}
if(require.main===module){try{const result=build(),out=path.join(root,"build/research/sgx-listing-risk-triage-v257.json");fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");console.log("v257 PASS: 20 historical codes; 6 prioritized listing-risk reviews; 0 live status claims");}catch(e){console.error(e);process.exitCode=1}}
module.exports={build};
