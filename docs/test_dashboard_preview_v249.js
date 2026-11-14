"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,".."),docs=path.join(root,"docs");
const html=fs.readFileSync(path.join(docs,"index.html"),"utf8");
const wf=fs.readFileSync(path.join(root,".github/workflows/value-hunter-pages.yml"),"utf8");
const feed=JSON.parse(fs.readFileSync(path.join(docs,"data/latest.json"),"utf8"));
assert.match(wf,/dashboard-preview:\s*\n\s*needs: validate/);
assert.match(wf,/name: value-hunter-dashboard-preview-v249/);
assert.match(wf,/path: build\/preview\/value-hunter-dashboard-preview-v249\.zip/);
assert.match(wf,/retention-days: 30/);
assert.match(wf,/archive\.write\(file, file\.relative_to\(root\.parent\)\.as_posix\(\)\)/);
assert.match(wf,/pages:\s*\n\s*needs: \[validate, pages-setup\]/);
assert.match(wf,/needs\.pages-setup\.outputs\.enabled == 'true'/);
assert.ok(!/dashboard-preview:[\s\S]*?\n  pages-setup:/.exec(wf)?.[0].includes("pages: write"),"preview job must not require Pages permission");
assert.equal(feed.ranking_enabled,false);
assert.equal(feed.ranking_eligible_count,0);
assert.equal(feed.coverage.all_sgx_listed,false);
assert.equal(feed.coverage.registered_count,feed.records.length);
const assets=[];
for(const [,u] of html.matchAll(/<(?:script|link)\b[^>]*?(?:src|href)="(\.\/[^"#?]+)"/g)){
 const decoded=decodeURIComponent(u);
 assert.ok(!decoded.includes(".."),"traversal asset "+decoded);
 const relative=decoded.replace(/^\.\//,"");
 const full=path.resolve(docs,relative);
 assert.ok(full.startsWith(docs+path.sep),"asset outside docs "+relative);
 assert.ok(fs.statSync(full).isFile(),"missing preview asset "+relative);
 assets.push(relative);
}
assert.ok(assets.length>=25,"incomplete HTML static dependencies");
for(const p of ["index.html","style.css","app.js","data/latest.json",
 "data/sgx-four-pdf-replay-evidence-v248.json",
 "data/sgx-uob-official-buyback-v242.json",
 "data/sgx-ocbc-issuer-identity-v244.json",
 "data/sgx-source-rights-review-v222.json"]){
 assert.ok(fs.statSync(path.join(docs,p)).isFile(),"missing required static preview file "+p);
}
assert.ok(assets.includes("pdf-sha-evidence-v234.js"));
assert.ok(assets.includes("bank-share-evidence-v193.js"));
console.log("v249 PASS: static dashboard ZIP source complete, "+assets.length+" HTML assets resolved; preview independent of unenabled Pages; ranking stays blocked");
