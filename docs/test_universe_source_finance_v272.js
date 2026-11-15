"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validateUniverse,joinCandidates,filterCandidates}=require("./universe.js");
const {buildWithOriginalProof}=require("./sgx-historical-code-search-v258.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const files=[
"docs/data/sgx-universe-candidates.json",
"docs/data/sgx-corporate-indexed-page-v253.json",
"docs/data/sgx-official-issuer-code-filings-v255.json",
"docs/data/sgx-net-eleven-codes-v256.json",
"docs/data/sgx-official-batch-seed-v196.json",
"docs/data/sgx-material-listing-events-v257.json",
"docs/data/latest.json",
"docs/data/sgx-nineteen-original-html-sha-v262.json"].map(read);
const rows=joinCandidates(files[0],buildWithOriginalProof(...files.slice(1)),files[6]);
assert.equal(rows.length,182);
assert.equal(validateUniverse(files[0]).provider_accepted_candidate_count,182);
assert.equal(new Set(rows.map(r=>r.symbol)).size,182);
assert.equal(rows.filter(r=>r.financialRegistered).length,7);
assert.equal(rows.filter(r=>r.officialHistoricalCode).length,17);
assert.equal(rows.filter(r=>!r.officialHistoricalCode&&!r.financialRegistered).length,162);
assert.ok(rows.filter(r=>r.originalHtmlProof).every(r=>r.officialHistoricalCode));
assert.ok(rows.every(r=>r.rankingEligible===false&&!r.listedCurrentlyVerified));
const covered=filterCandidates(rows,"","ALL");
const exchanged=filterCandidates(rows,"","OFFICIAL");
const financed=filterCandidates(rows,"","FINANCIAL");
const unknown=filterCandidates(rows,"","UNVERIFIED");
assert.equal(covered.length,182);
assert.equal(exchanged.length,rows.filter(r=>r.officialHistoricalCode).length);
assert.equal(financed.length,7);
assert.equal(unknown.length,rows.filter(r=>!r.officialHistoricalCode&&!r.financialRegistered).length);
assert.equal(filterCandidates(rows,"O39","FINANCIAL").length,1);
assert.equal(filterCandidates(rows,"nothing whatsoever","ALL").length,0);
const index=files.map(x=>structuredClone(x));
for(const bad of [
 a=>a[0].candidates[0].ranking_eligible=true,
 a=>a[0].full_sgx_listing_completeness_verified=true,
 a=>a[6].ranking_eligible_count=1,
 a=>a[6].records[0].ranking_eligible=true,
 a=>a[0].candidates[1].symbol=a[0].candidates[0].symbol
]){
 const changed=index.map(x=>structuredClone(x));bad(changed);
 assert.throws(()=>joinCandidates(changed[0],buildWithOriginalProof(...changed.slice(1)),changed[6]));
}
const html=fs.readFileSync("docs/index.html","utf8");
const js=fs.readFileSync("docs/universe.js","utf8");
assert.match(html,/id="universeCandidateProvenance"/);
assert.match(html,/<th>過去コードの根拠<\/th><th>財務登録/);
assert.match(js,/root\?\.SGX_SOURCE_DIRECTORY_READONLY\?\.buildWithOriginalProof/);
assert.match(js,/filter\.addEventListener\("change",repaint\)/);
assert.match(js,/a\.href="#issuer="\+item\.symbol/);
console.log("v272 PASS: 182 third-party candidates joined cautiously to 30 prior SGX original/static sources and 7 financial statuses");
