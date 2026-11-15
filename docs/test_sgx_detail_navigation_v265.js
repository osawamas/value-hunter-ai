"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const app=require("./app.js");
const {buildWithOriginalProof}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const inputs=[
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const items=buildWithOriginalProof(...inputs);
const registered=items.filter(x=>x.financialRegistered);
assert.deepEqual(registered.map(x=>x.code).sort(),["D05","O39","S68","U11"]);
for(const x of registered){
 assert.equal(app.parseIssuerHash("#issuer="+x.code),x.code);
 assert.equal(inputs[5].records.find(r=>r.symbol===x.code).ranking_eligible,false);
}
for(const x of [null,undefined,"","#issuer=","#issuer=5WA%0A","#issuer=O39&ranking=true",
 "#issuer=<script>","#issuer=O39/../../","?#issuer=O39","#issuer=evil","#issuer=ＡＢＣ"]){
 assert.equal(app.parseIssuerHash(x),null);
}
assert.equal(app.parseIssuerHash("#issuer=G13"),"G13");
const appSource=fs.readFileSync("docs/app.js","utf8");
const browserSource=fs.readFileSync("docs/sgx-historical-code-search-v258.js","utf8");
assert.match(appSource,/window\.addEventListener\("hashchange",openIssuerFromHash\)/);
assert.match(appSource,/function openIssuerFromHash\(\)/);
assert.match(appSource,/if\(!rec \|\| rec\.ranking_eligible!==false\)return false/);
assert.match(appSource,/showDetail\(rec\)/);
assert.match(browserSource,/link\.href="#issuer="\+item\.code/);
assert.match(browserSource,/if\(item\.financialRegistered &&/);
assert.match(browserSource,/link\.textContent="財務詳細を見る"/);
console.log("v265 PASS: validated hash links for 4 SGX finance registrations; financial details use original feed, rankings stay gated");
