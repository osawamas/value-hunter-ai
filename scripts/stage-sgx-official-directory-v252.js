#!/usr/bin/env node
"use strict";
/* v252 local, manual SGX issuer-directory CSV staging.
 * Import is deliberately NEVER proof that a directory is complete or licensed.
 * No network collection, no price scraping, no financial/ranking promotion.
 */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const root=path.resolve(__dirname,"..");
const permittedBoards=new Set(["MAINBOARD","CATALIST","GLOBAL LISTING BOARD"]);
const permittedCurrencies=new Set(["SGD","USD","HKD","EUR","GBP","AUD","JPY","CNY","MYR","IDR","THB","PHP","CHF","CAD","NZD"]);
const expected=["Trading Code","Trading Name","Listing Board","Traded Currency"];
function parseCsv(text){
 if(text.charCodeAt(0)===0xfeff)text=text.slice(1);
 if(text.length>4*1024*1024)throw Error("CSV source too large");
 const records=[];let row=[],cell="",quoted=false,endedQuote=false;
 for(let i=0;i<text.length;i++){
  const ch=text[i];
  if(quoted){
   if(ch==='"'&&text[i+1]==='"'){cell+='"';i++}
   else if(ch==='"'){quoted=false;endedQuote=true}
   else cell+=ch;
  }else if(endedQuote){
   if(ch===","){row.push(cell);cell="";endedQuote=false}
   else if(ch==="\n"||ch==="\r"){
    row.push(cell);records.push(row);row=[];cell="";endedQuote=false;
    if(ch==="\r"&&text[i+1]==="\n")i++;
   }else throw Error("Unexpected character after CSV quoted value");
  }else if(ch==='"'){
   if(cell)throw Error("Unescaped quote in field");
   quoted=true;
  }else if(ch===","){row.push(cell);cell=""}
  else if(ch==="\n"||ch==="\r"){
   row.push(cell);records.push(row);row=[];cell="";
   if(ch==="\r"&&text[i+1]==="\n")i++;
  }else cell+=ch;
  if(cell.length>2000)throw Error("CSV cell too long");
 }
 if(quoted)throw Error("Unterminated CSV quote");
 if(endedQuote||cell!==""||row.length){row.push(cell);records.push(row)}
 return records.filter(x=>x.some(v=>v.trim()!==""));
}
function stage(text,sourceUrl,asOf,candidates,feed){
 const url=new URL(sourceUrl);
 if(url.protocol!=="https:"||!["sgx.com","www.sgx.com","links.sgx.com"].includes(url.hostname)||
    url.username||url.password||url.hash)
  throw Error("SGX corporate-information source URL required");
 if(!/^\d{4}-\d{2}-\d{2}$/.test(asOf)||new Date(asOf+"T00:00:00Z").toISOString().slice(0,10)!==asOf)
  throw Error("Explicit valid dated snapshot required");
 const rows=parseCsv(text);
 if(!rows.length||rows[0].length!==4||rows[0].some((x,i)=>x!==expected[i]))
  throw Error("CSV requires exact reviewed headers: "+expected.join(", "));
 const items=[],seen=new Set();
 for(const fields of rows.slice(1)){
  if(fields.length!==4)throw Error("Wrong CSV column count");
  const [code,name,board,currency]=fields.map(x=>x.trim());
  if(!/^[A-Z0-9]{1,6}$/.test(code)||!name||name.length>180||
     !permittedBoards.has(board)||!permittedCurrencies.has(currency)||
     seen.has(code))throw Error("Invalid/duplicate SGX code, name, board or currency");
  seen.add(code);
  items.push({symbol:code,name,listing_board:board,traded_currency:currency,
   issuer_directory_source_reviewed:false,
   source_document_and_symbol_verified_individually:false,
   financial_verification:false,ranking_eligible:false});
 }
 if(!items.length||items.length>1200)throw Error("Source row count out of research bounds");
 if(candidates.schema_version!=="sgx-third-party-company-candidates-v99"||
    candidates.full_sgx_listing_completeness_verified!==false||
    candidates.eligible_for_ranking!==false||
    !Array.isArray(candidates.candidates)||
    candidates.provider_accepted_candidate_count!==candidates.candidates.length||
    feed.ranking_enabled!==false||feed.ranking_eligible_count!==0)
  throw Error("Upstream source gates invalid");
 const third=new Set(candidates.candidates.map(x=>x.symbol));
 const finance=new Set(feed.records.map(x=>x.symbol));
 return {schema_version:"sgx-manual-official-directory-staging-v252",
  as_of_date:asOf,source_url:url.href,source_kind:"MANUALLY_SUPPLIED_UNREVIEWED_CSV",
  csv_sha256:crypto.createHash("sha256").update(text).digest("hex"),
  staged_security_rows:items.length,
  intersect_third_party_candidate_count:items.filter(x=>third.has(x.symbol)).length,
  staged_not_in_third_party:items.filter(x=>!third.has(x.symbol)).map(x=>x.symbol).sort(),
  staged_not_in_financial_feed:items.filter(x=>!finance.has(x.symbol)).map(x=>x.symbol).sort(),
  official_full_master_verified:false,issuer_level_source_review_complete:false,
  source_license_and_redistribution_authorized:false,
  securities_code_coverage_complete:false,
  independent_financial_audit_complete:false,licensed_quote_feed_verified:false,
  financial_feed_modified:false,ranking_enabled:false,ranking_eligible_count:0,
  records:items};
}
function main(args=process.argv.slice(2)){
 if(args.length!==3)throw Error("Usage: node scripts/stage-sgx-official-directory-v252.js FILE.csv SGX_SOURCE_URL YYYY-MM-DD");
 const [source,url,asOf]=args;
 const text=fs.readFileSync(source,"utf8");
 const candidates=JSON.parse(fs.readFileSync(path.join(root,"docs/data/sgx-universe-candidates.json"),"utf8"));
 const feed=JSON.parse(fs.readFileSync(path.join(root,"docs/data/latest.json"),"utf8"));
 const result=stage(text,url,asOf,candidates,feed);
 const output=path.join(root,"build/research/sgx-official-directory-staging-v252.json");
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
 console.log("v252 STAGED: "+result.staged_security_rows+" local rows, "+
 result.staged_not_in_third_party.length+" absent from third-party candidates; NOT certified full SGX universe");
}
if(require.main===module)try{main()}catch(e){console.error("v252 blocked: "+e.message);process.exitCode=1}
module.exports={parseCsv,stage};
