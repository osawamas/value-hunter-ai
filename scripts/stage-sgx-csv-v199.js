#!/usr/bin/env node
"use strict";
/* v199: local staging adapter for manually obtained security-list CSV.
 * NOT a scraper, SGX official-master certificate, price feed or distribution permission.
 * Only a verified/authorized source can later be promoted through a separate review.
 */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
function csvRows(raw){
 if(typeof raw!=="string"||raw.length>20_000_000)throw Error("Invalid CSV bytes");
 const text=raw.replace(/^\uFEFF/,""),rows=[],row=[];
 let field="",quoted=false;
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){
   if(c==='"'&&text[i+1]==='"'){field+='"';i++;}
   else if(c==='"')quoted=false;
   else field+=c;
  }else if(c==='"'){if(field.length)throw Error("CSV invalid quote");quoted=true;}
  else if(c===","){row.push(field);field="";}
  else if(c==="\n"||c==="\r"){
   if(c==="\r"&&text[i+1]==="\n")i++;
   row.push(field);field="";
   if(row.some(x=>x.trim().length))rows.push(row.splice(0));
   else row.splice(0);
  }else field+=c;
 }
 if(quoted)throw Error("CSV unterminated quoted field");
 if(field.length||row.length){row.push(field);if(row.some(x=>x.trim()))rows.push(row);}
 return rows;
}
function normalize(raw,{as_of_date,source_url,source_description="manually supplied CSV"}={}){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(as_of_date||"")||
    new Date(as_of_date+"T00:00:00Z").toISOString().slice(0,10)!==as_of_date)
  throw Error("Explicit valid as-of date required");
 if(!/^https:\/\/(www\.)?sgx\.com\//.test(source_url||"")&&
    !/^https:\/\/links\.sgx\.com\//.test(source_url||""))
  throw Error("Link to SGX official source page required; this alone does not authenticate the CSV");
 const rows=csvRows(raw);if(rows.length<2)throw Error("CSV must contain header and securities");
 const names=rows.shift().map(x=>x.trim().toLowerCase());
 const index=(...aliases)=>names.findIndex(x=>aliases.includes(x));
 const codeCol=index("trading code","stock code","security code","code");
 const nameCol=index("trading name","security name","stock name","name");
 const currencyCol=index("trading currency","traded currency","currency");
 const typeCol=index("security type","instrument type","product type");
 const boardCol=index("listing board","board");
 if([codeCol,nameCol,currencyCol].some(i=>i<0))throw Error("Missing required code/name/currency columns");
 if(new Set(names).size!==names.length)throw Error("Ambiguous CSV duplicate headers");
 const data=[],seen=new Set();
 for(const [i,row] of rows.entries()){
  if(row.length!==names.length)throw Error("CSV column count mismatch at "+(i+2));
  const code=row[codeCol].trim().toUpperCase(),name=row[nameCol].trim(),
   currency=row[currencyCol].trim().toUpperCase(),
   type=typeCol<0?"UNKNOWN":row[typeCol].trim().toUpperCase()||"UNKNOWN",
   board=boardCol<0?"UNKNOWN":row[boardCol].trim().toUpperCase()||"UNKNOWN";
  if(!/^[A-Z0-9]{1,8}$/.test(code)||!name||name.length>180||
     !/^[A-Z]{3}$/.test(currency)||type.length>64||board.length>64)
    throw Error("Invalid security identity field at "+(i+2));
  const key=[code,currency,type].join("|");
  if(seen.has(key))throw Error("Duplicate security counter "+key);
  seen.add(key);
  // Strictly omit Last/Bid/Ask/Volume/market-cap even if present in input.
  data.push({trading_code:code,trading_name:name,trading_currency:currency,
   instrument_type:type,listing_board:board});
 }
 const sha256=crypto.createHash("sha256").update(Buffer.from(raw,"utf8")).digest("hex");
 return {schema_version:"sgx-manual-security-list-staging-v199",as_of_date,source_url,
  source_description,original_csv_sha256:sha256,
  source_authentication:"NOT_INDEPENDENTLY_AUTHENTICATED",
  original_file_is_sgx_verified:false,full_sgx_universe_verified:false,
  security_counter_not_necessarily_unique_issuer:true,
  quote_columns_stripped:true,licensed_quote_access:false,
  distribution_rights_reviewed:false,ranking_enabled:false,ranking_eligible_count:0,
  item_count:data.length,items:data};
}
if(require.main===module){
 const args=process.argv.slice(2);
 const get=k=>{const i=args.indexOf(k);return i>=0?args[i+1]:null;};
 const inp=get("--input"),out=get("--out"),as_of_date=get("--as-of"),source_url=get("--source-url");
 if(!inp||!out||!as_of_date||!source_url){
  process.stderr.write("Usage: node scripts/stage-sgx-csv-v199.js --input FILE.csv --out LOCAL_STAGING.json --as-of YYYY-MM-DD --source-url https://www.sgx.com/...\n");
  process.exitCode=2;
 }else{
  try{
   const output=path.resolve(out),repoDocs=path.resolve(__dirname,"../docs");
   if(output===repoDocs||output.startsWith(repoDocs+path.sep))
    throw Error("Refusing to publish unauthenticated staged data under docs/");
   const doc=normalize(fs.readFileSync(inp,"utf8"),{as_of_date,source_url});
   fs.mkdirSync(path.dirname(output),{recursive:true});
   fs.writeFileSync(output,JSON.stringify(doc,null,2)+"\n",{flag:"wx"});
   process.stdout.write("Staged "+doc.item_count+" unverified security counters; NO prices or ranking eligibility.\n");
  }catch(err){process.stderr.write(String(err)+"\n");process.exitCode=1}
 }
}
module.exports={csvRows,normalize};
