#!/usr/bin/env node
"use strict";
/* v198 evidence integrity smoke suite. Reuses the real Node tests; no web/network
   fetch and no mutation of the financial feed. Execution does not prove original
   PDFs, licensing, site publication, or investment ranking readiness. */
const {spawnSync}=require("node:child_process");
const path=require("node:path");
const fs=require("node:fs");
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
 "docs/test_primary_issuer_reconciliation_v214.js",
 "docs/test_uob_buyback_chain_v216.js",
 "docs/test_evidence_suite_report_v219.js",
 "docs/test_multicurrency_subset_v220.js",
 "docs/test_official_multicurrency_v221.js",
 "docs/test_sgx_source_rights_v222.js",
 "docs/test_dual_currency_expansion_v224.js",
 "docs/test_expanded_currency_ui_v225.js",
 "docs/test_sgx_instrument_types_v226.js",
 "docs/test_sgx_dual_currency_second_batch_v227.js",
 "docs/test_dual_currency_ui_v228.js",
 "docs/test_staged_sgx_universe_audit_v229.js",
 "docs/test_sgx_issuer_directory_v230.js",
 "docs/test_offline_sgx_cli_v232.js",
 "docs/test_sgx_pdf_sha_evidence_v233.js",
 "docs/test_sgx_pdf_sha_ui_v234.js",
 "docs/test_evidence_unique_paths_v235.js",
 "docs/test_issuer_annual_pdf_v236.js",
 "docs/test_sgx_annual_report_sha_v237.js"
];
let failed=0;
const results=[];
for(const test of tests){
 const proc=spawnSync(process.execPath,[path.join(root,test)],{
  cwd:root,encoding:"utf8",timeout:30_000,env:{...process.env}
 });
 if(proc.error||proc.status!==0){
  failed++;results.push({test,status:"FAIL",exit_code:proc.status,signal:proc.signal||null,runner_error:proc.error?String(proc.error):null});
  process.stderr.write("FAIL "+test+"\n"+(proc.stdout||"")+(proc.stderr||"")+(proc.error||"")+"\n");
 }else {results.push({test,status:"PASS",exit_code:0});process.stdout.write("PASS "+test+"\n");}
}
process.stdout.write("Evidence smoke suite: "+(tests.length-failed)+"/"+tests.length+" passed; rankings remain independently gated.\n");
const resultPath=path.join(root,"build","research","evidence-integrity-v218.json");
const report={
 schema_version:"sgx-evidence-integrity-results-v218",
 purpose:"SOURCE_AND_RANKING_GUARD_TESTS_NOT_MARKET_AUDIT",
 commit_sha:/^[0-9a-f]{40}$/.test(process.env.GITHUB_SHA||"")?process.env.GITHUB_SHA:null,
 node_version:process.version,
 total:results.length,passed:results.length-failed,failed,
 verdict:failed?"FAIL":"PASS",results,
 independent_financial_audit_proven:false,
 market_data_redistribution_license_proven:false,
 actual_github_pages_publication_proven:false
};
try{
 fs.mkdirSync(path.dirname(resultPath),{recursive:true});
 fs.writeFileSync(resultPath,JSON.stringify(report,null,2)+"\n");
 if(process.env.GITHUB_STEP_SUMMARY){
  const table=["## SGX source-integrity regression",
   "Commit: \`"+(report.commit_sha||"unverified-local")+"\`",
   "Result: **"+report.passed+"/"+report.total+"** passed",
   "",
   "| Test | Status |","|---|---|",
   ...results.map(r=>"| \`"+r.test+"\` | "+r.status+" |"),
   "",
   "These tests do not independently audit issuer PDFs, validate a quote license, or make investment rankings eligible."].join("\n");
  fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,table+"\n");
 }
}catch(e){
 failed++;
 process.stderr.write("FAIL: unable to preserve evidence run report: "+e+"\n");
}
process.exitCode=failed?1:0;
