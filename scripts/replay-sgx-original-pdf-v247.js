#!/usr/bin/env node
"use strict";
/* v247: an actual SGX PDF replay, comparing newly fetched original bytes
   against pre-existing GitHub Actions provenance. No financial extraction. */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto");
const {download,validateTarget}=require("./probe-sgx-original-v246.js");
const root=path.resolve(__dirname,"..");
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
const sources=Object.freeze([
 Object.freeze({symbol:"H02",type:"FY2025_RESULTS",dataset:"docs/data/sgx-original-pdf-sha-v233.json",urlKey:"pdf_url",byteKey:"byte_length"}),
 Object.freeze({symbol:"V03",type:"FY2025_RESULTS",dataset:"docs/data/sgx-original-pdf-sha-v233.json",urlKey:"pdf_url",byteKey:"byte_length"}),
 Object.freeze({symbol:"H02",type:"FY2025_ANNUAL",dataset:"docs/data/sgx-annual-report-sha-v237.json",urlKey:"source_url",byteKey:"bytes"}),
 Object.freeze({symbol:"V03",type:"FY2025_ANNUAL",dataset:"docs/data/sgx-annual-report-sha-v237.json",urlKey:"source_url",byteKey:"bytes"})
]);
function expectedRows(results,annual){
 if(results.schema_version!=="sgx-original-issuer-pdf-sha-evidence-v233"||
    annual.schema_version!=="sgx-h02-v03-annual-original-pdf-sha-v237"||
    results.records?.length!==2||annual.records?.length!==2)
  throw Error("Incorrect source-provenance datasets");
 const sourceMap=new Map([["docs/data/sgx-original-pdf-sha-v233.json",results],["docs/data/sgx-annual-report-sha-v237.json",annual]]);
 return sources.map(s=>{
  const found=sourceMap.get(s.dataset).records.filter(x=>x.symbol===s.symbol);
  if(found.length!==1)throw Error("Missing or duplicate source: "+s.symbol+" "+s.type);
  const rec=found[0],url=validateTarget(rec[s.urlKey]),sha=rec.sha256,bytes=rec[s.byteKey];
  if(!/^[0-9a-f]{64}$/.test(sha)||!Number.isSafeInteger(bytes)||bytes<100||bytes>12*1024*1024)
   throw Error("Malformed pinned source evidence: "+s.symbol+" "+s.type);
  if(rec.ranking_eligible!==false)throw Error("Unexpected ranking eligibility");
  return {symbol:s.symbol,kind:s.type,url,expected_sha256:sha,expected_bytes:bytes};
 });
}
function reconcile(pinned,retrieved){
 const bytes=Buffer.from(retrieved.bytes);
 const final=validateTarget(retrieved.finalUrl);
 if(bytes.length<100||bytes.subarray(0,5).toString()!=="%PDF-")
  throw Error("Original source did not return PDF bytes");
 const sha256=crypto.createHash("sha256").update(bytes).digest("hex");
 if(bytes.length!==pinned.expected_bytes||sha256!==pinned.expected_sha256)
  throw Error("SGX original PDF byte identity mismatch for "+pinned.symbol+" "+pinned.kind);
 return {symbol:pinned.symbol,kind:pinned.kind,url:pinned.url,final_url:final,
         sha256,bytes:bytes.length,matched_previously_observed_sha256:true,
         independent_financial_numeric_audit:false,licensed_quote_verified:false,
         current_share_count_verified:false,ranking_eligible:false};
}
async function replay(rows,fetcher=download){
 const out=[];
 for(const row of rows)out.push(reconcile(row,await fetcher(row.url)));
 return {
  schema_version:"sgx-original-pdf-replay-v247",scope:"REPEATED_SGX_ORIGINAL_BYTES_NOT_INDEPENDENT_FINANCIAL_AUDIT",
  sources_checked:out.length,all_original_bytes_match_existing_evidence:out.length===4,
  independent_accounting_audit_complete:false,quote_rights_verified:false,ranking_eligible_count:0,
  records:out
 };
}
async function main(){
 const rows=expectedRows(read("docs/data/sgx-original-pdf-sha-v233.json"),read("docs/data/sgx-annual-report-sha-v237.json"));
 const report=await replay(rows);
 if(!report.all_original_bytes_match_existing_evidence)throw Error("Incomplete PDF replay");
 const file=path.join(root,"build/research/sgx-original-pdf-replay-v247.json");
 fs.mkdirSync(path.dirname(file),{recursive:true});
 fs.writeFileSync(file,JSON.stringify(report,null,2)+"\n");
 console.log("v247 VERIFIED: "+report.records.length+" SGX original PDFs have expected SHA256 and length. No ranking promotion.");
}
if(require.main===module)main().catch(e=>{console.error("v247 original PDF replay failed: "+e.message);process.exitCode=1});
module.exports={expectedRows,reconcile,replay};
