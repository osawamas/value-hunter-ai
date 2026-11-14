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
 "docs/test_fy_third_party_figure_v197.js"
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
