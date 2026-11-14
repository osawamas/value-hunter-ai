"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validateExpanded}=require("./pdf-sha-evidence-v234.js");
const read=p=>JSON.parse(fs.readFileSync("docs/data/"+p+".json","utf8"));
const base=[
 read("sgx-original-pdf-sha-v233"),
 read("sgx-h02-primary-filing-v212"),
 read("sgx-v03-primary-statements-v213"),
 read("sgx-annual-report-sha-v237"),
 read("sgx-four-pdf-replay-evidence-v248"),
 read("latest")
];
function check(a){
 const rows=validateExpanded(...a);
 assert.equal(rows.length,4);
 assert.deepEqual(rows.map(x=>x.symbol+" "+x.kind),[
 "H02 通期決算発表 FY2025","V03 通期決算発表 FY2025",
 "H02 年次報告書 FY2025","V03 年次報告書 FY2025"
 ]);
 assert.deepEqual(rows.map(x=>x.bytes),[706174,520231,4754838,8502570]);
 assert.equal(new Set(rows.map(x=>x.sha)).size,4);
 assert.ok(rows.every(x=>x.independent_numeric_audit===false&&x.ranking_eligible===false));
}
check(base);
for(const mutate of [
 a=>{a[3].records[0].sha256="a".repeat(64)},
 a=>{a[3].records[1].bytes++},
 a=>{a[3].records[0].symbol="V03"},
 a=>{a[3].records[0].source_url="https://thirdparty.example/1.pdf"},
 a=>{a[3].records[1].ranking_eligible=true},
 a=>{a[3].records[1].issuer_numerical_audit_independently_verified=true},
 a=>{a[4].github_run_id=0},
 a=>{a[4].matching_original_pdf_count=3},
 a=>{a[4].source_pdf_sha256_recomputed_in_real_actions=false},
 a=>{a[4].financial_fields_independently_recalculated=true},
 a=>{a[4].rankings_enabled=true},
 a=>{a[5].ranking_eligible_count=1}
]){
 const a=base.map(x=>structuredClone(x));
 mutate(a);assert.throws(()=>check(a));
}
const html=fs.readFileSync("docs/index.html","utf8");
const script=fs.readFileSync("docs/pdf-sha-evidence-v234.js","utf8");
assert.match(html,/id="issuerPdfDigestRows"/);
assert.match(html,/43614340513/);
assert.match(script,/validateExpanded\(\.\.\.items\)/);
assert.match(script,/sgx-four-pdf-replay-evidence-v248\.json/);
console.log("v248 PASS: four original SGX source PDFs display exact SHA/length and real replay metadata; audit still blocked");
