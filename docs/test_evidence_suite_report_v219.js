"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,"../scripts/verify-evidence-v198.js"),"utf8");
function simulate(failing){
 const writes=new Map(),logs=[];
 const virtualFs={
  mkdirSync:()=>{},
  writeFileSync:(p,t)=>writes.set(p,t),
  appendFileSync:(p,t)=>writes.set(p,(writes.get(p)||"")+t)
 };
 let invoked=0;
 const virtualProcess={
  env:{GITHUB_SHA:"a".repeat(40),GITHUB_STEP_SUMMARY:"/virtual/job-summary.md"},
  version:process.version,execPath:process.execPath,
  stdout:{write:v=>logs.push(v)},stderr:{write:v=>logs.push(v)},exitCode:0
 };
 const fakeRequire=mod=>{
  if(mod==="node:fs")return virtualFs;
  if(mod==="node:path")return path;
  if(mod==="node:child_process")return {
   spawnSync:(exe,args,opt)=>{
    invoked++;
    assert.equal(exe,process.execPath);
    assert.equal(opt.cwd,path.resolve(__dirname,".."));
    const fail=failing&&args[0].endsWith("test_issuer_pdf_probe_v210.js");
    return {status:fail?1:0,signal:null,stdout:"",stderr:fail?"SIMULATED FAILURE":""};
   }
  };
  throw Error("Unexpected dependency "+mod);
 };
 vm.runInNewContext(source.replace(/^#![^\n]*\n/,""),{
  require:fakeRequire,process:virtualProcess,__dirname:path.resolve(__dirname,"../scripts")
 },{timeout:10000});
 const filename=path.resolve(__dirname,"../build/research/evidence-integrity-v218.json");
 const report=JSON.parse(writes.get(filename));
 const summary=writes.get("/virtual/job-summary.md");
 assert.equal(report.schema_version,"sgx-evidence-integrity-results-v218");
 assert.equal(report.commit_sha,"a".repeat(40));
 assert.equal(report.total,invoked);
 assert.ok(report.total>=22);
 assert.equal(report.results.length,invoked);
 assert.ok(summary.includes("| Test | Status |"));
 assert.ok(summary.includes("Result: **"+report.passed+"/"+report.total+"** passed"));
 assert.equal(report.independent_financial_audit_proven,false);
 assert.equal(report.market_data_redistribution_license_proven,false);
 assert.equal(report.actual_github_pages_publication_proven,false);
 assert.ok(!writes.get(filename).includes("SIMULATED FAILURE"));
 if(failing){
  assert.equal(report.failed,1);assert.equal(report.verdict,"FAIL");
  assert.equal(virtualProcess.exitCode,1);
  assert.ok(report.results.some(r=>r.status==="FAIL"));
 }else{
  assert.equal(report.failed,0);assert.equal(report.verdict,"PASS");
  assert.equal(virtualProcess.exitCode,0);
  assert.ok(report.results.every(r=>r.status==="PASS"));
 }
}
simulate(false);
simulate(true);
console.log("v219 PASS: CI evidence report JSON and summary are generated for both success and failure, never implying market audit");
