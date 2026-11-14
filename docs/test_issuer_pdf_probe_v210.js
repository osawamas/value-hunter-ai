"use strict";
const assert=require("node:assert/strict");
const {validateTarget,pdfDigest,download,TARGETS}=require("../scripts/probe-issuer-financial-pdf-v210.js");
assert.equal(TARGETS.length,2);
for(const target of TARGETS)assert.ok(validateTarget(target.url).hostname.endsWith("sgx.com")||
  validateTarget(target.url).hostname.endsWith("listedcompany.com"));
for(const bad of [
 "http://links.sgx.com/file.pdf",
 "https://evil.example/file.pdf",
 "https://links.sgx.com.evil.example/file.pdf",
 "https://user:pass@links.sgx.com/file.pdf"
])assert.throws(()=>validateTarget(bad));
const sample=Buffer.from("%PDF-1.7\nmanual test bytes\n%%EOF");
assert.equal(pdfDigest(sample).bytes,sample.length);
assert.match(pdfDigest(sample).sha256,/^[a-f0-9]{64}$/);
assert.throws(()=>pdfDigest(Buffer.from("NOT_A_PDF_ORIGINAL")));
(async()=>{
 const makeResponse=(url,bytes,contentLength=bytes.length)=>({
  url,ok:true,status:200,
  headers:{get:k=>k==="content-length"?String(contentLength):"application/pdf"},
  body:(async function*(){yield bytes})()
 });
 const result=await download(TARGETS[0].url,{fetcher:async url=>makeResponse(url,sample)});
 assert.equal(result.digest.bytes,sample.length);
 assert.equal(result.digest.sha256,pdfDigest(sample).sha256);
 await assert.rejects(()=>download(TARGETS[0].url,{fetcher:async url=>
  makeResponse("https://example.com/redirected.pdf",sample)}));
 await assert.rejects(()=>download(TARGETS[0].url,{fetcher:async url=>
  makeResponse(url,sample,1000000),maxBytes:100}));
 await assert.rejects(()=>download(TARGETS[0].url,{fetcher:async url=>
  makeResponse(url,Buffer.from("BAD DOCUMENT BODY"))}));
 console.log("v210 PASS: official-only PDF download guard, source byte SHA, bounded stream and redirect denial");
})().catch(e=>{console.error(e);process.exitCode=1});
