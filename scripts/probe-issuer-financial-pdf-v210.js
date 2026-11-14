#!/usr/bin/env node
"use strict";
/* v210: opt-in official issuer PDF byte probe. Never scrapes market quotes.
   Does not interpret PDF tables, independently audit accounting, or enable rankings.
   Do not automatically publish downloaded PDF bytes. */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const TARGETS=[
 {symbol:"H02",kind:"FY2025_ISSUER_FINANCIAL_STATEMENTS",
  url:"https://links.sgx.com/1.0.0/corporate-announcements/R2V7WFBB9WQMBBP4/876566_FY25%20Haw%20Par%20SGX%20Announcementl.pdf"},
 {symbol:"V03",kind:"FY2025_ISSUER_FINANCIAL_STATEMENTS",
  url:"https://links.sgx.com/1.0.0/corporate-announcements/G8XZA2TO5M07X8S0/876221_Venture%20FY2025%20Financial%20Results.pdf"}
];
const allowed=new Set(["hawpar.listedcompany.com","links.sgx.com"]);
function validateTarget(url){
 const u=new URL(url);
 if(u.protocol!=="https:"||!allowed.has(u.hostname)||u.username||u.password)
  throw Error("Unapproved issuer PDF host");
 return u;
}
function pdfDigest(bytes){
 if(!Buffer.isBuffer(bytes)||bytes.length<16||!bytes.subarray(0,5).equals(Buffer.from("%PDF-")))
  throw Error("Not a PDF original");
 return {sha256:crypto.createHash("sha256").update(bytes).digest("hex"),bytes:bytes.length};
}
async function download(url,{fetcher=fetch,maxBytes=25_000_000}={}){
 validateTarget(url);
 if(!Number.isSafeInteger(maxBytes)||maxBytes<16||maxBytes>25_000_000)
  throw Error("Invalid bounded original-PDF size limit");
 const ac=new AbortController(),timer=setTimeout(()=>ac.abort(),30000);
 try{
  let current=url,response;
  const visited=new Set();
  for(let redirects=0;redirects<=3;redirects++){
   validateTarget(current);
   if(visited.has(current))throw Error("PDF redirect cycle");
   visited.add(current);
   response=await fetcher(current,{
    signal:ac.signal,redirect:"manual",headers:{"Accept":"application/pdf"}
   });
   if([301,302,303,307,308].includes(response.status)){
    if(redirects===3)throw Error("Too many PDF redirects");
    const location=response.headers?.get?.("location");
    if(!location)throw Error("PDF redirect without location");
    const next=new URL(location,current).href;
    validateTarget(next); // reject before making the next request
    current=next;
    continue;
   }
   if(!response.ok)throw Error("Original issuer PDF HTTP "+response.status);
   if(response.url){
    validateTarget(response.url);
    if(response.url!==current)
     throw Error("Fetcher followed unapproved automatic redirect");
   }
   const lengthRaw=response.headers?.get?.("content-length");
   if(lengthRaw!==null&&lengthRaw!==undefined&&lengthRaw!==""){
    const n=Number(lengthRaw);
    if(!Number.isSafeInteger(n)||n<0||n>maxBytes)
     throw Error("Invalid or oversized PDF Content-Length");
   }
   const chunks=[];let total=0;
   if(!response.body)throw Error("PDF has no response body");
   for await(const chunk of response.body){
    total+=chunk.byteLength;
    if(total>maxBytes)throw Error("PDF stream exceeds size limit");
    chunks.push(Buffer.from(chunk));
   }
   const buf=Buffer.concat(chunks);
   return {digest:pdfDigest(buf),
    mime:response.headers?.get?.("content-type")||null,
    fetched_final_url:current,redirect_count:redirects};
  }
  throw Error("PDF redirect limit reached");
 }finally{clearTimeout(timer)}
}
async function run(){
 const records=[];
 for(const item of TARGETS){
  try{
   const x=await download(item.url);
   records.push({symbol:item.symbol,source_kind:item.kind,source_url:item.url,
    ...x.digest,fetched_final_url:x.fetched_final_url,source_pdf_byte_digest_calculated:true,
    accounting_table_values_independently_verified:false,share_quote_license_verified:false,
    ranking_eligible:false});
  }catch(e){
   records.push({symbol:item.symbol,source_kind:item.kind,source_url:item.url,
    sha256:null,bytes:null,source_pdf_byte_digest_calculated:false,
    failure:String(e),accounting_table_values_independently_verified:false,
    share_quote_license_verified:false,ranking_eligible:false});
  }
 }
 const output={schema_version:"sgx-discovered-issuer-pdf-source-probe-v210",
  observed_at_utc:new Date().toISOString(),records,
  ranking_eligible_count:0,financial_feed_modified:false,
  no_independent_numeric_validation:true};
 const dest=path.resolve("build/research/sgx-discovered-issuer-pdf-v210.json");
 fs.mkdirSync(path.dirname(dest),{recursive:true});
 fs.writeFileSync(dest,JSON.stringify(output,null,2)+"\n");
 console.log("v210 source check:",records.map(r=>r.symbol+":"+(r.sha256?"PDF digest":"unavailable")).join(", "));
 if(records.some(r=>!r.sha256))process.exitCode=1;
}
if(require.main===module)run().catch(e=>{console.error(e);process.exitCode=1});
module.exports={validateTarget,pdfDigest,download,TARGETS};
