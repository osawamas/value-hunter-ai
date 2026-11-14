#!/usr/bin/env node
"use strict";
/** v246 original SGX announcement PDF byte-provenance only.
 * No price collection, share calculation, full-universe claim or ranking promotion.
 * Explicit URL argument, manually reviewed before use. Redirects remain on links.sgx.com.
 */
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const ROOT=path.resolve(__dirname,"..");
const MAX_BYTES=12*1024*1024;
const MAX_REDIRECTS=4;
function validateTarget(raw){
 const u=new URL(raw);
 if(u.protocol!=="https:"||u.hostname!=="links.sgx.com"||
    u.username||u.password||u.port||u.hash||
    !(/^\/FileOpen\/[A-Za-z0-9%._~()+,-]+\.ashx$/i.test(u.pathname)||
      /^\/1\.0\.0\/corporate-announcements\/[A-Za-z0-9_-]+\/[A-Za-z0-9%._~-]+\.pdf$/i.test(u.pathname)))
   throw Error("Only actual SGX announcement PDF URLs are accepted");
 const isFileOpen=u.pathname.startsWith("/FileOpen/");
 const allowed=isFileOpen?new Set(["App","FileID"]):new Set();
 for(const key of u.searchParams.keys())if(!allowed.has(key))throw Error("Unexpected SGX PDF URL query argument");
 if(isFileOpen&&(u.searchParams.get("App")!=="Announcement"||
    !/^\\d+$/.test(u.searchParams.get("FileID")||"")||
    [...u.searchParams.keys()].length!==2))
  throw Error("SGX FileOpen requires an exact announcement file id");
 return u.href;
}
function evidence(bytes,sourceUrl,finalUrl,subject){
 const buffer=Buffer.from(bytes);
 if(buffer.length<100||buffer.length>MAX_BYTES||buffer.subarray(0,5).toString()!=="%PDF-")
  throw Error("Not an acceptable SGX original PDF byte stream");
 if(!["U11","O39"].includes(subject))throw Error("Unexpected subject");
 return {
  schema_version:"sgx-original-document-byte-provenance-v246",
  symbol:subject,requested_url:validateTarget(sourceUrl),
  final_url:validateTarget(finalUrl),
  bytes:buffer.length,
  sha256:crypto.createHash("sha256").update(buffer).digest("hex"),
  source_type:"SGX_ORIGINAL_PDF_BYTES_ONLY",
  financial_figures_extracted:false,
  financial_figures_independently_verified:false,
  original_announcement_reference_confirmed:false,
  official_current_shares_verified:false,
  quote_license_verified:false,
  ranking_eligible:false
 };
}
async function download(url){
 let current=validateTarget(url);
 for(let redirect=0;redirect<=MAX_REDIRECTS;redirect++){
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),20000);
  let res;
  try{
   res=await fetch(current,{redirect:"manual",signal:controller.signal,headers:{"User-Agent":"VALUE-HUNTER-AI-source-provenance/1.0","Accept":"application/pdf"}});
  }catch(err){clearTimeout(timeout);throw err}
  try{
  if([301,302,303,307,308].includes(res.status)){
   if(redirect===MAX_REDIRECTS)throw Error("Too many redirects");
   const loc=res.headers.get("location");if(!loc)throw Error("Redirect missing location");
   current=validateTarget(new URL(loc,current).href);continue;
  }
  if(!res.ok)throw Error("SGX HTTP "+res.status);
  const n=Number(res.headers.get("content-length")||0);
  if(n>MAX_BYTES)throw Error("PDF too large");
  const contentType=(res.headers.get("content-type")||"").toLowerCase();
  if(contentType&&!/(application\/pdf|octet-stream)/.test(contentType))
   throw Error("Unexpected PDF content-type: "+contentType);
  const parts=[];let total=0;
  for await(const chunk of res.body){
   total+=chunk.length;if(total>MAX_BYTES)throw Error("PDF stream exceeds size cap");
   parts.push(chunk);
  }
  return {bytes:Buffer.concat(parts),finalUrl:current};
  }finally{clearTimeout(timeout)}
 }
 throw Error("SGX PDF not retrieved");
}
async function main(argv=process.argv.slice(2)){
 const [symbol,sourceUrl]=argv;
 if(!symbol||!sourceUrl||argv.length!==2){
  throw Error("Usage: node scripts/probe-sgx-original-v246.js U11|O39 https://links.sgx.com/...pdf");
 }
 const validated=validateTarget(sourceUrl);
 const {bytes,finalUrl}=await download(validated);
 const result=evidence(bytes,validated,finalUrl,symbol);
 const out=path.join(ROOT,"build","research","sgx-original-pdf-v246-"+symbol+".json");
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
 console.log("SGX original bytes recorded: "+symbol+" "+result.bytes+" bytes SHA256 "+result.sha256);
 console.log("No accounting or ranking promotion. Evidence: "+path.relative(ROOT,out));
}
if(require.main===module)main().catch(e=>{console.error("v246 source probe blocked: "+e.message);process.exitCode=1});
module.exports={validateTarget,evidence,download,MAX_BYTES};
