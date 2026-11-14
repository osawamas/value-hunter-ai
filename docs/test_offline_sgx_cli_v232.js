"use strict";
/* v232 — real Node CLI smoke regression. Input fixture is synthetic.
 * Runs all three offline programs using temporary files and ensures no
 * unauthenticated staging output is written under public docs/. */
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),
 os=require("node:os"),crypto=require("node:crypto");
const {spawnSync}=require("node:child_process");
const root=path.resolve(__dirname,"..");
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"value-hunter-sgx-v232-"));
function run(script,args){
 return spawnSync(process.execPath,[path.join(root,script),...args],{
  cwd:root,encoding:"utf8",timeout:30000,env:{...process.env}
 });
}
try{
 const securities=[
  "Trading Code,Trading Name,Traded Currency,Security Type,Listing Board,Last,Bid,Ask,Volume",
  "AWX,AEM SGD,SGD,STOCK,MAINBOARD,9.00,8.99,9.01,100",
  "XWA,AEM USD,USD,STOCK,MAINBOARD,7.00,6.99,7.01,120",
  "G13,Genting,SGD,STOCK,MAINBOARD,0.60,0.59,0.61,500",
  "AAA,Synthetic ETF,USD,ETF,MAINBOARD,1.00,0.99,1.01,100"
 ].join("\n")+"\n";
 const issuers=[
  "Company Name,Country,Listing Board,Listed Date,Stock Code,Last",
  "Example Alpha Holdings,Singapore,Mainboard,2020-01-02,AWX,9.00",
  "Example Beta Holdings,Singapore,Catalist,2019-04-03,G13,0.60"
 ].join("\n")+"\n";
 const securitiesPath=path.join(tmp,"securities.csv"),
       issuerPath=path.join(tmp,"issuers.csv");
 fs.writeFileSync(securitiesPath,securities);
 fs.writeFileSync(issuerPath,issuers);
 const localStaged=path.join(tmp,"securities-staged.json"),
       localAudit=path.join(tmp,"securities-audit.json"),
       issuerStaged=path.join(tmp,"issuers-staged.json");
 const quoteSource="https://www.sgx.com/securities/securities-prices?code=stocks";
 const issuerSource="https://www.sgx.com/securities/corporate-information";
 const a=run("scripts/stage-sgx-csv-v199.js",[
  "--input",securitiesPath,"--out",localStaged,"--as-of","2026-11-14",
  "--source-url",quoteSource
 ]);
 assert.equal(a.status,0,a.stderr||a.stdout);
 const b=run("scripts/audit-staged-sgx-universe-v229.js",[
  "--staged",localStaged,"--out",localAudit
 ]);
 assert.equal(b.status,0,b.stderr||b.stdout);
 const c=run("scripts/stage-sgx-issuer-directory-v230.js",[
  "--input",issuerPath,"--out",issuerStaged,"--as-of","2026-11-14",
  "--source-url",issuerSource
 ]);
 assert.equal(c.status,0,c.stderr||c.stdout);
 const staged=JSON.parse(fs.readFileSync(localStaged,"utf8")),
       audit=JSON.parse(fs.readFileSync(localAudit,"utf8")),
       issuer=JSON.parse(fs.readFileSync(issuerStaged,"utf8"));
 assert.equal(staged.original_csv_sha256,
  crypto.createHash("sha256").update(fs.readFileSync(securitiesPath)).digest("hex"));
 assert.equal(issuer.original_csv_sha256,
  crypto.createHash("sha256").update(fs.readFileSync(issuerPath)).digest("hex"));
 assert.equal(staged.item_count,4);
 assert.equal(audit.staged_security_counters,4);
 assert.equal(audit.classified_counter_counts.POTENTIAL_EQUITY,3);
 assert.equal(audit.classified_counter_counts.ETF,1);
 assert.deepEqual(audit.staged_distinct_codes_matching_third_party,["AWX","G13"]);
 assert.deepEqual(audit.staged_distinct_codes_matching_financial,["G13"]);
 assert.equal(audit.ranking_eligible_count,0);
 assert.equal(issuer.issuer_count,2);
 assert.ok(issuer.issuers.every(x=>x.sgx_trading_code===null));
 assert.equal(issuer.official_complete_issuer_master_verified,false);
 assert.equal(staged.licensed_quote_access,false);
 assert.ok(!JSON.stringify(staged).includes('"Last"'));
 assert.ok(!JSON.stringify(issuer).includes('"Last"'));
 assert.ok(!JSON.stringify(issuer).includes('"Stock Code"'));
 // Real CLI must prevent silently replacing staged evidence.
 assert.notEqual(run("scripts/stage-sgx-csv-v199.js",[
  "--input",securitiesPath,"--out",localStaged,"--as-of","2026-11-14",
  "--source-url",quoteSource]).status,0);
 assert.notEqual(run("scripts/stage-sgx-issuer-directory-v230.js",[
  "--input",issuerPath,"--out",issuerStaged,"--as-of","2026-11-14",
  "--source-url",issuerSource]).status,0);
 // Malicious request to publish into public docs must be refused.
 assert.notEqual(run("scripts/stage-sgx-csv-v199.js",[
  "--input",securitiesPath,"--out",path.join(root,"docs","not-allowed-v232.json"),
  "--as-of","2026-11-14","--source-url",quoteSource]).status,0);
 assert.notEqual(run("scripts/stage-sgx-issuer-directory-v230.js",[
  "--input",issuerPath,"--out",path.join(root,"docs","not-allowed-issuer-v232.json"),
  "--as-of","2026-11-14","--source-url",issuerSource]).status,0);
 assert.ok(!fs.existsSync(path.join(root,"docs","not-allowed-v232.json")));
 assert.ok(!fs.existsSync(path.join(root,"docs","not-allowed-issuer-v232.json")));
 console.log("v232 PASS: three real Node CLI commands stage and audit synthetic SGX data without quote leaks, overwrites or public output");
}finally{
 fs.rmSync(tmp,{recursive:true,force:true});
}
