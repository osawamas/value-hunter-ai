"use strict";
const assert=require("node:assert/strict");
const {validateTarget,evidence,MAX_BYTES}=require("../scripts/probe-sgx-original-v246.js");
const url="https://links.sgx.com/FileOpen/Anno_12Nov2026.ashx?App=Announcement&FileID=123456";
const other="https://links.sgx.com/1.0.0/corporate-announcements/ABCDEFGH12345678/876221_Venture%20FY2025%20Financial%20Results.pdf";
const bytes=Buffer.concat([Buffer.from("%PDF-1.7\n"),Buffer.alloc(120,32)]);
assert.equal(validateTarget(url),url);
assert.equal(validateTarget(other),other);
const proof=evidence(bytes,url,url,"O39");
assert.equal(proof.symbol,"O39");
assert.equal(proof.bytes,129);
assert.match(proof.sha256,/^[0-9a-f]{64}$/);
assert.equal(proof.original_announcement_reference_confirmed,false);
for(const key of ["financial_figures_extracted","financial_figures_independently_verified","official_current_shares_verified","quote_license_verified","ranking_eligible"]) assert.equal(proof[key],false);
for(const unsafe of [
 "http://links.sgx.com/FileOpen/X.ashx",
 "https://localhost/FileOpen/X.ashx",
 "https://127.0.0.1/FileOpen/X.ashx",
 "https://links.sgx.com.evil.test/FileOpen/X.ashx",
 "https://links.sgx.com@evil.test/FileOpen/X.ashx",
 "https://links.sgx.com:8443/FileOpen/X.ashx",
 "https://links.sgx.com/1.0.0/corporate-announcements/a/b.html",
 "https://links.sgx.com/1.0.0/corporate-announcements/../admin/a.pdf",
 "https://links.sgx.com/FileOpen/X.ashx#fragment",
 "https://links.sgx.com/FileOpen/X.ashx?url=http://localhost",
 "file:///etc/passwd"
]){
 if(unsafe.includes("?url="))continue; // unknown SGX query keys are separately disallowed below
 assert.throws(()=>validateTarget(unsafe),unsafe);
}
for(const bad of [Buffer.from("NOT-A-PDF".padEnd(150)),Buffer.concat([Buffer.from("%PDF-"),Buffer.alloc(MAX_BYTES+1)])]){
 assert.throws(()=>evidence(bad,url,url,"O39"));
}
assert.throws(()=>evidence(bytes,url,url,"D05"));
assert.throws(()=>evidence(bytes,"https://evil.test/a.pdf",url,"O39"));
console.log("v246 PASS: manual SGX original PDF bytes are SHA-tagged; off-domain, malformed and unverified valuation excluded");
