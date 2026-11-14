#!/usr/bin/env node
"use strict";
/* v198 evidence integrity smoke suite. Reuses the real Node tests; no web/network
   fetch and no mutation of the financial feed. Execution does not prove original
   PDFs, licensing, site publication, or investment ranking readiness. */
const {spawnSync}=require("node:child_process");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const tests=[
 "docs/test_bank_corporate_actions_v190.js",
 "docs/test_bank_cross_evidence_v192.js",
 "docs/test_bank_share_evidence_v193.js",
 "docs/test_bank_fy_interim_bridge_v195.js",
 "docs/test_official_batch_v196.js",
 "docs/test_fy_third_party_figure_v197.js",
 "docs/test_stage_sgx_csv_v199.js",
 "docs/test_uob_share_display_scope_v201.js",
 "docs/test_classify_sgx_counters_v202.js",
 "docs/test_stage_classification_pipeline_v203.js",
 "docs/test_sgx_isin_linkage_v204.js",
 "docs/test_universe_coverage_audit_v205.js",
 "docs/test_additional_issuer_fy2025_v206.js",
 "docs/test_remaining_issuer_research_v207.js",
 "docs/test_h02_group_statement_v208.js",
 "docs/test_v03_balance_v209.js",
 "docs/test_issuer_pdf_probe_v210.js",
 "docs/test_parent_equity_research_v211.js",
 "docs/test_h02_primary_filing_v212.js",
 "docs/test_v03_primary_statements_v213.js",
 "docs/test_primary_issuer_reconciliation_v214.js"
];
let failed=0;
for(const test of tests){
 const proc=spawnSync(process.execPath,[path.join(root,test)],{
  cwd:root,encoding:"utf8",timeout:30_000,env:{...process.env}
 });
 if(proc.error||proc.status!==0){
  failed++;process.stderr.write("FAIL "+test+"\n"+(proc.stdout||"")+(proc.stderr||"")+(proc.error||"")+"\n");
 }else process.stdout.write("PASS "+test+"\n");
}
process.stdout.write("Evidence smoke suite: "+(tests.length-failed)+"/"+tests.length+" passed; rankings remain independently gated.\n");
process.exitCode=failed?1:0;
