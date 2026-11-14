#!/usr/bin/env node
"use strict";
/* v230: offline, untrusted-first transcription adapter for SGX Corporate Information
 * issuer directory. It is deliberately NOT a securities/quote list.
 * Do not publish, count as official complete coverage, or derive tickers from names. */
const fs=require("node:fs"),path=require("node:path");
const {csvRows,decodeOriginalCsv}=require("./stage-sgx-csv-v199.js");
function stage(raw,{as_of_date,source_url,original_csv_sha256}={}){
 if(typeof raw!=="string"||raw.length>10_000_000)throw Error("CSV too large or invalid");
 if(!/^\d{4}-\d{2}-\d{2}$/.test(as_of_date||"")||
    new Date(as_of_date+"T00:00:00Z").toISOString().slice(0,10)!==as_of_date)
  throw Error("Explicit valid observation date required");
 const u=new URL(source_url||"");
 if(u.protocol!=="https:"||u.hostname!=="www.sgx.com"||
   u.pathname!=="/securities/corporate-information"||
   [...u.searchParams.keys()].some(k=>k!=="page")||
   (u.searchParams.has("page")&&!/^\d+$/.test(u.searchParams.get("page"))))
  throw Error("Use exactly the SGX official Corporate Information directory source URL");
 if(!/^[0-9a-f]{64}$/.test(original_csv_sha256||""))
  throw Error("Missing original UTF-8 CSV SHA256");
 const rows=csvRows(raw);
 if(rows.length<2)throw Error("No issuer-directory rows");
 const header=rows.shift().map(s=>s.trim().toLowerCase());
 if(new Set(header).size!==header.length)throw Error("Duplicate headers");
 const idx=(...names)=>header.findIndex(x=>names.includes(x));
 const nameCol=idx("company name","issuer name","company","issuer");
 const boardCol=idx("listing board","board");
 const countryCol=idx("country","incorporation country");
 const dateCol=idx("listed date","listing date");
 if(nameCol<0||boardCol<0||countryCol<0)
  throw Error("Issuer names, listing board and country are required; securities are a different dataset");
 const seen=new Set(),out=[];
 for(const [i,row] of rows.entries()){
  if(row.length!==header.length)throw Error("Wrong issuer CSV column count at "+(i+2));
  const name=row[nameCol].trim(),board=row[boardCol].trim().toUpperCase(),
     country=row[countryCol].trim().toUpperCase(),
     listed_date=dateCol<0?null:row[dateCol].trim()||null;
  if(!name||name.length>200||!["MAINBOARD","CATALIST","GLOBAL LISTING BOARD"].includes(board)||
     !country||country.length>90||(/[\r\n\t]/.test(name))||
     (listed_date!==null&&!/^\d{4}-\d{2}-\d{2}$/.test(listed_date)))
   throw Error("Invalid issuer identity at "+(i+2));
  if(listed_date!==null&&new Date(listed_date+"T00:00:00Z").toISOString().slice(0,10)!==listed_date)
   throw Error("Invalid listing date");
  const key=name.toUpperCase().replace(/\s+/g," ");
  if(seen.has(key))throw Error("Duplicate issuer name, review multiple-board cases manually");
  seen.add(key);
  // Never accept trading code/price/market-cap from a corporate-information transcription.
  out.push({issuer_name:name,listing_board:board,country,
   directory_listed_date:listed_date,isin:null,sgx_trading_code:null,
   linked_securities_verified:false,listed_issuer_verified:false,
   ranking_eligible:false});
 }
 return {schema_version:"sgx-manual-issuer-directory-staging-v230",
  observation_date:as_of_date,source_url_claim_unverified:u.href,
  original_csv_sha256,source_authentication:"MANUAL_TRANSCRIPTION_NOT_INDEPENDENTLY_AUTHENTICATED",
  official_complete_issuer_master_verified:false,public_redistribution_rights_verified:false,
  securities_master_verified:false,quote_data_collected:false,
  company_names_not_ticker_mapping:true,ranking_enabled:false,
  ranking_eligible_count:0,issuer_count:out.length,issuers:out};
}
function run(args=process.argv.slice(2)){
 const opt=x=>{const i=args.indexOf(x);return i>=0?args[i+1]:null};
 const input=opt("--input"),out=opt("--out"),as_of_date=opt("--as-of"),source_url=opt("--source-url");
 if(!input||!out||!as_of_date||!source_url)
  throw Error("Usage: node scripts/stage-sgx-issuer-directory-v230.js --input LOCAL.csv --out LOCAL.json --as-of YYYY-MM-DD --source-url https://www.sgx.com/securities/corporate-information");
 const destination=path.resolve(out),docs=path.resolve(__dirname,"../docs");
 if(destination===docs||destination.startsWith(docs+path.sep))
  throw Error("Refusing to publish unverified manual issuer observations under docs/");
 const original=decodeOriginalCsv(fs.readFileSync(input));
 const result=stage(original.csv,{as_of_date,source_url,original_csv_sha256:original.sha256});
 fs.mkdirSync(path.dirname(destination),{recursive:true});
 fs.writeFileSync(destination,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
 process.stdout.write("Staged "+result.issuer_count+" local unverified issuer names, no trade codes/quotes.\n");
 return result;
}
if(require.main===module){try{run()}catch(e){process.stderr.write("FAIL v230: "+String(e)+"\n");process.exitCode=1}}
module.exports={stage,run};
