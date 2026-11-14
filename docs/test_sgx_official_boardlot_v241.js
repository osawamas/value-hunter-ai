"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const official=JSON.parse(fs.readFileSync("docs/data/sgx-boardlot-official-v241.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const candidates=JSON.parse(fs.readFileSync("docs/data/sgx-universe-candidates.json","utf8"));
const EXPECTED=Object.freeze({D05:"SGD",G07:"SGD",H02:"SGD",C07:"SGD",J36:"USD",BN4:"SGD",O39:"SGD",K6S:"USD",S68:"SGD",U11:"SGD",V03:"SGD"});
function validate(d,f,c){
 assert.equal(d.schema_version,"sgx-official-boardlot-ten-share-subset-v241");
 assert.equal(d.effective_date,"2026-10-05");
 assert.equal(d.source_url,"https://www.sgx.com/securities/trading");
 assert.equal(d.source_kind,"SGX_OFFICIAL_TRADING_PAGE_NAMED_ELEVEN_SECURITY_SUBSET");
 assert.equal(d.source_scope,"INITIAL_BATCH_OF_SECURITIES_WITH_REDUCED_BOARD_LOT");
 assert.equal(d.board_lot_shares,10);
 assert.equal(d.reported_subset_count,11);
 assert.equal(d.rows.length,11);
 assert.equal(new Set(d.rows.map(x=>x.symbol)).size,11,"duplicate SGX security code");
 assert.deepEqual(d.rows.map(x=>x.symbol).sort(),Object.keys(EXPECTED).sort());
 for(const row of d.rows){
  assert.equal(row.traded_currency,EXPECTED[row.symbol],"currency mismatch for "+row.symbol);
  assert.equal(row.board_lot_shares,10);
  assert.ok(row.issuer&&typeof row.issuer==="string");
  assert.equal(row.official_listing_scope,"NAMED_2026_10_05_BOARD_LOT_BATCH_ONLY");
  assert.equal(row.ranking_eligible,false);
 }
 for(const key of ["official_full_security_master","official_list_issuer_universe_complete","ranking_eligible","financial_data_validated","licensed_quote_feed_available","latest_ex_treasury_shares_verified"]){
  assert.equal(d[key],false,"unsafe evidence promotion: "+key);
 }
 assert.equal(f.coverage.listed_universe,"SGX");
 assert.equal(f.coverage.all_sgx_listed,false);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 assert.equal(c.full_sgx_listing_completeness_verified,false);
 assert.equal(c.eligible_for_ranking,false);
 assert.equal(c.records_not_added_to_verified_financial_feed,true);
 assert.equal(c.provider_accepted_candidate_count,c.candidates.length);
 for(const rec of f.records){
  assert.equal(rec.ranking_eligible,false);
 }
 return true;
}
validate(official,feed,candidates);
for(const alter of [
 (d,f,c)=>{d.official_full_security_master=true},
 (d,f,c)=>{d.official_list_issuer_universe_complete=true},
 (d,f,c)=>{d.licensed_quote_feed_available=true},
 (d,f,c)=>{d.latest_ex_treasury_shares_verified=true},
 (d,f,c)=>{d.rows[0].ranking_eligible=true},
 (d,f,c)=>{d.rows[0].board_lot_shares=100},
 (d,f,c)=>{d.rows[0].symbol="O39"},
 (d,f,c)=>{d.rows[4].traded_currency="SGD"},
 (d,f,c)=>{d.rows.pop()},
 (d,f,c)=>{c.full_sgx_listing_completeness_verified=true},
 (d,f,c)=>{f.ranking_enabled=true},
 (d,f,c)=>{f.coverage.all_sgx_listed=true},
 (d,f,c)=>{f.ranking_eligible_count=1}
]){
 const args=[official,feed,candidates].map(x=>structuredClone(x));
 alter(...args);assert.throws(()=>validate(...args));
}
console.log("v241 PASS: official 11-code 10-share batch; currencies correct; universe / prices / shares / rankings remain unverified");
