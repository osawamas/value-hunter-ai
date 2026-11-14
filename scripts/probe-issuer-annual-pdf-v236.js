#!/usr/bin/env node
"use strict";
/* v236: additional annual-report PDF provenance, separate from H02/V03
   FY2025 results release PDFs. No original PDF bytes are published.
   Same issuer's two documents do NOT constitute external independent audit. */
const fs=require("node:fs"),path=require("node:path");
const {download}=require("./probe-issuer-financial-pdf-v210.js");
const TARGETS=[
 {symbol:"H02",source_kind:"FY2025_ISSUER_ANNUAL_REPORT",
  url:"https://links.sgx.com/FileOpen/Haw%20Par%20Corp%20Annual%20Report%202025.ashx?App=Announcement&FileID=881713"},
 {symbol:"V03",source_kind:"FY2025_ISSUER_ANNUAL_REPORT",
  url:"https://links.sgx.com/FileOpen/VCL_Annual_Report_2025.ashx?App=Announcement&FileID=881699"}
];
async function collect(fetchDocument=download,observed_at_utc=new Date().toISOString()){
 const rows=[];
 for(const target of TARGETS){
  try{
   const proof=await fetchDocument(target.url);
   if(!proof?.digest||! /^[0-9a-f]{64}$/.test(proof.digest.sha256||"")||
      !Number.isSafeInteger(proof.digest.bytes)||proof.digest.bytes<16||
      !/^https:\/\/links\.sgx\.com\//.test(proof.fetched_final_url||""))
    throw Error("Missing or invalid original SGX annual PDF digest");
   rows.push({symbol:target.symbol,source_kind:target.source_kind,
    original_source_url:target.url,fetched_final_url:proof.fetched_final_url,
    sha256:proof.digest.sha256,bytes:proof.digest.bytes,
    annual_report_raw_bytes_hashed:true,independent_external_auditor_comparison_completed:false,
    accounting_table_values_crosschecked_in_this_run:false,ranking_eligible:false});
  }catch(err){
   rows.push({symbol:target.symbol,source_kind:target.source_kind,
    original_source_url:target.url,sha256:null,bytes:null,
    annual_report_raw_bytes_hashed:false,reason:String(err),
    independent_external_auditor_comparison_completed:false,
    accounting_table_values_crosschecked_in_this_run:false,ranking_eligible:false});
  }
 }
 return {schema_version:"sgx-issuer-annual-original-pdf-probe-v236",
  observed_at_utc,source_type:"SGX_ISSUER_ANNUAL_REPORTS_NOT_EXTERNAL_AUDITORS",
  original_fy2025_results_comparison_separate:"docs/data/sgx-original-pdf-sha-v233.json",
  all_original_bytes_hashed:rows.every(r=>r.annual_report_raw_bytes_hashed),
  financial_feed_modified:false,ranking_eligible_count:0,
  external_independent_financial_audit_completed:false,records:rows};
}
async function run(){
 const report=await collect();
 const out=path.resolve("build/research/sgx-annual-report-probe-v236.json");
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(report,null,2)+"\n");
 console.log("v236 annual originals:",report.records.map(x=>x.symbol+":"+(x.sha256?"PDF SHA256":"UNAVAILABLE")).join(", "));
 if(!report.all_original_bytes_hashed)process.exitCode=1;
}
if(require.main===module)run().catch(e=>{console.error(e);process.exitCode=1});
module.exports={TARGETS,collect};
