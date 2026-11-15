#!/usr/bin/env node
"use strict";
/* v291 historical security-list change detector.
 * Works only with user-supplied locally staged identities; NEVER certifies
 * new listings/delistings, source rights, financial verification or rankings.
 */
const fs=require("node:fs"),path=require("node:path");
const {normalize,decodeOriginalCsv}=require("./stage-sgx-csv-v199.js");
function parseDate(s){
 if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))throw Error("Invalid date");
 const d=new Date(s+"T00:00:00Z");
 if(!Number.isFinite(d.getTime())||d.toISOString().slice(0,10)!==s)throw Error("Invalid calendar date");
 return s;
}
function validate(snapshot){
 if(!snapshot||snapshot.schema_version!=="sgx-manual-security-list-staging-v199"||
   snapshot.source_authentication!=="NOT_INDEPENDENTLY_AUTHENTICATED"||
   snapshot.original_file_is_sgx_verified!==false||
   snapshot.full_sgx_universe_verified!==false||
   snapshot.licensed_quote_access!==false||
   snapshot.ranking_enabled!==false||snapshot.ranking_eligible_count!==0||
   !Array.isArray(snapshot.items)||!snapshot.items.length||
   snapshot.item_count!==snapshot.items.length||
   !/^[a-f0-9]{64}$/.test(snapshot.original_csv_sha256||""))
   throw Error("Unsupported or promoted source snapshot");
 parseDate(snapshot.as_of_date);
 if(!/^https:\/\/(?:www\.)?sgx\.com\//.test(snapshot.source_url||"") &&
    !/^https:\/\/links\.sgx\.com\//.test(snapshot.source_url||""))
   throw Error("Source URL must refer to an SGX page");
 const codes=new Set();
 for(const x of snapshot.items){
  if(!x||!/^[A-Z0-9]{1,8}$/.test(x.trading_code||"")||
     typeof x.trading_name!=="string"||!x.trading_name.trim()||
     !/^[A-Z]{3}$/.test(x.trading_currency||"")||
     typeof x.instrument_type!=="string"||!x.instrument_type.trim())
    throw Error("Invalid identity row");
  const key=x.trading_code+"|"+x.trading_currency+"|"+x.instrument_type;
  if(codes.has(key))throw Error("Duplicate security identity "+key);
  codes.add(key);
 }
 return snapshot;
}
function diff(oldSnapshot,newSnapshot){
 const a=validate(oldSnapshot),b=validate(newSnapshot);
 if(a.as_of_date>=b.as_of_date)throw Error("Snapshots must have strictly increasing as-of dates");
 const toMap=s=>new Map(s.items.map(x=>[x.trading_code+"|"+x.trading_currency+"|"+x.instrument_type,x]));
 const before=toMap(a),after=toMap(b);
 const added=[],removed=[],changed=[];
 for(const [key,entry] of after){
  const prev=before.get(key);
  if(!prev) added.push({identity:key,name:entry.trading_name,
    interpretation:"NEW_TO_INPUT_SNAPSHOT_NOT_PROVEN_NEW_LISTING"});
  else if(prev.trading_name!==entry.trading_name||prev.listing_board!==entry.listing_board)
   changed.push({identity:key,from_name:prev.trading_name,to_name:entry.trading_name,
    from_board:prev.listing_board,to_board:entry.listing_board,
    interpretation:"METADATA_DIFFERENCE_NOT_CORPORATE_ACTION_PROOF"});
 }
 for(const [key,entry] of before)if(!after.has(key))
  removed.push({identity:key,name:entry.trading_name,
   interpretation:"ABSENT_FROM_NEW_INPUT_NOT_PROVEN_DELISTED"});
 for(const arr of [added,removed,changed])arr.sort((x,y)=>x.identity.localeCompare(y.identity));
 const previousCodes=new Set(a.items.map(x=>x.trading_code));
 const currentCodes=new Set(b.items.map(x=>x.trading_code));
 const shiftedCodes=[...previousCodes].filter(x=>currentCodes.has(x)).filter(code=>
  [...before.keys()].filter(k=>k.startsWith(code+"|")).sort().join(",")!==
  [...after.keys()].filter(k=>k.startsWith(code+"|")).sort().join(",")).sort();
 return {
  schema_version:"sgx-security-snapshot-diff-v291",
  older:{as_of_date:a.as_of_date,input_sha256:a.original_csv_sha256,source_url:a.source_url,item_count:a.item_count},
  newer:{as_of_date:b.as_of_date,input_sha256:b.original_csv_sha256,source_url:b.source_url,item_count:b.item_count},
  possible_additions:added,possible_removals:removed,
  metadata_changes:changed,code_currency_or_instrument_type_changes_for_review:shiftedCodes,
  counts:{added:added.length,removed:removed.length,changed:changed.length,code_variants:shiftedCodes.length},
  confirmed_listing_events:false,completeness_verified:false,
  issuer_count_inferred:false,market_data_rights_verified:false,
  ranking_enabled:false,ranking_eligible_count:0,
  published_feed_modified:false
 };
}
function corroborateOctober(result,october,ipo){
 const start=result.older.as_of_date,end=result.newer.as_of_date;
 if(start!=="2026-09-30"||end!=="2026-10-31")
  throw Error("October evidence requires the 30 Sep and 31 Oct 2026 snapshots");
 const {reconcileOctoberBoards}=require("../docs/universe-coverage-audit-v205.js");
 const {delisting,transfer}=reconcileOctoberBoards(october,ipo);
 const ordinary=(entry,code)=>{
  const [symbol,currency,type]=entry.identity.split("|");
  return symbol===code&&currency==="SGD"&&["STOCK","EQUITY","ORDINARY SHARE","ORDINARY SHARES"].includes(type);
 };
 const corroborated=[];
 for(const listing of ipo.issuer_listing_confirmations){
  const matches=result.possible_additions.filter(e=>ordinary(e,listing.trading_code));
  if(matches.length===1)corroborated.push({identity:matches[0].identity,
   event:"LISTING_CONFIRMATION",effective_date:listing.effective_trading_date,source_url:listing.source_url});
 }
 const removed=result.possible_removals.filter(e=>ordinary(e,delisting.symbol));
 if(removed.length===1)corroborated.push({identity:removed[0].identity,event:"DELISTING",
  effective_date:delisting.date,source_url:delisting.source.url});
 const moved=result.metadata_changes.filter(e=>ordinary(e,transfer.symbol)&&
  e.from_board===transfer.from_board&&e.to_board===transfer.to_board);
 if(moved.length===1)corroborated.push({identity:moved[0].identity,event:"TRANSFER",
  effective_date:transfer.date,source_url:transfer.source.url});
 return {...result,public_sgx_event_matches:corroborated};
}
function fromCSV(input,date,url){
 const original=decodeOriginalCsv(fs.readFileSync(input));
 const staged=normalize(original.csv,{as_of_date:date,source_url:url});
 if(original.sha256!==staged.original_csv_sha256)throw Error("Source SHA mismatch");
 return staged;
}
if(require.main===module){
 const args=process.argv.slice(2),val=k=>{const p=args.indexOf(k);return p<0?null:args[p+1]};
 try{
  const older=val("--older"),newer=val("--newer"),a=val("--older-date"),b=val("--newer-date"),
  url1=val("--older-url"),url2=val("--newer-url"),out=val("--out");
  if(![older,newer,a,b,url1,url2,out].every(Boolean))throw Error("Usage: node scripts/diff-sgx-snapshots-v291.js --older old.csv --older-date YYYY-MM-DD --older-url https://www.sgx.com/... --newer new.csv --newer-date YYYY-MM-DD --newer-url https://www.sgx.com/... --out build/research/local-diff.json [--corroborate-october-2026]");
  const dest=path.resolve(out),docs=path.resolve(__dirname,"../docs");
  if(dest===docs||dest.startsWith(docs+path.sep))throw Error("Refusing to publish private unauthenticated data into docs/");
  let result=diff(fromCSV(older,a,url1),fromCSV(newer,b,url2));
  if(args.includes("--corroborate-october-2026")){
   const research=name=>JSON.parse(fs.readFileSync(path.join(docs,"data",name)));
   result=corroborateOctober(result,research("sgx-october-release-v292.json"),research("sgx-october-ipo-listing-v294.json"));
  }
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
  console.log(result.counts.added+" possible additions, "+result.counts.removed+" possible removals"+
   (result.public_sgx_event_matches?" and "+result.public_sgx_event_matches.length+" matches to public SGX events":"")+
   ". Input source remains unauthenticated.");
 }catch(e){console.error(e.message);process.exitCode=1;}
}
module.exports={diff,validate,parseDate,fromCSV,corroborateOctober};
