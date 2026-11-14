"use strict";
const assert=require("node:assert/strict");
const {validIsin,reconcile}=require("../scripts/sgx-isin-linkage-v204.js");
assert.equal(validIsin("SG1M31001969"),true);
assert.equal(validIsin("US0378331005"),true);
assert.equal(validIsin("GB0002634946"),true);
assert.equal(validIsin("SG1M31001968"),false);
assert.equal(validIsin("sg1m31001969"),false);
assert.equal(validIsin("SG1M3100196"),false);
const items=[
 {trading_code:"U11",trading_name:"United Overseas Bank",trading_currency:"SGD",instrument_type:"STOCK",listing_board:"MAINBOARD"},
 {trading_code:"A1A",trading_name:"Synthetic foreign counter",trading_currency:"USD",instrument_type:"STOCK",listing_board:"MAINBOARD"},
 {trading_code:"B1B",trading_name:"Synthetic second counter",trading_currency:"SGD",instrument_type:"STOCK",listing_board:"MAINBOARD"}
];
const staged={schema_version:"sgx-manual-security-list-staging-v199",
 original_file_is_sgx_verified:false,full_sgx_universe_verified:false,
 quote_columns_stripped:true,licensed_quote_access:false,
 ranking_eligible_count:0,items};
const refs=[
 {trading_code:"U11",trading_currency:"SGD",instrument_type:"STOCK",isin:"SG1M31001969",source_url:"https://links.sgx.com/FileOpen/example",assertion_level:"MANUAL_UNVERIFIED_EVIDENCE"},
 {trading_code:"A1A",trading_currency:"USD",instrument_type:"STOCK",isin:"US0378331005",source_url:"https://www.sgx.com/example",assertion_level:"MANUAL_UNVERIFIED_EVIDENCE"},
 {trading_code:"B1B",trading_currency:"SGD",instrument_type:"STOCK",isin:"US0378331005",source_url:"https://www.sgx.com/example",assertion_level:"MANUAL_UNVERIFIED_EVIDENCE"}
];
const result=reconcile(staged,refs);
assert.equal(result.validated_isin_checksums,3);
assert.equal(result.by_isin["US0378331005"].length,2);
assert.equal(result.verified_issuer_links,0);
assert.equal(result.investment_ranking_eligible,0);
assert.ok(result.mapping_rows.every(r=>r.issuer_entity_verified===false&&r.ranking_eligible===false));
for(const edit of [
 (s,r)=>{r[0].isin="SG1M31001968"},
 (s,r)=>{r[0].assertion_level="OFFICIAL_VERIFIED"},
 (s,r)=>{r.push({...r[0]})},
 (s,r)=>{s.items.splice(0,1)},
 (s,r)=>{s.full_sgx_universe_verified=true},
 (s,r)=>{s.licensed_quote_access=true}
]){
 const s=structuredClone(staged),r=structuredClone(refs);
 edit(s,r);assert.throws(()=>reconcile(s,r));
}
console.log("v204 PASS: ISIN format checks distinguish securities from issuer claims across multiple currency counters");
