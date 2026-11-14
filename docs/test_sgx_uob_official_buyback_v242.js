"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const proof=JSON.parse(fs.readFileSync("docs/data/sgx-uob-official-buyback-v242.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const EXPECTED=[
 ["2026-11-10","SG261110OTHRQ7Q7",6776600,1646779591],
 ["2026-11-11","SG261111OTHRGYNT",6810600,1646745591],
 ["2026-11-12","SG261112OTHRSYPK",6844600,1646711591]
];
function validate(d,f){
 assert.equal(d.schema_version,"sgx-uob-official-daily-buyback-chain-v242");
 assert.equal(d.issuer,"UNITED OVERSEAS BANK LIMITED");
 assert.equal(d.symbol,"U11");assert.equal(d.isin,"SG1M31001969");
 assert.equal(d.unit,"shares");
 assert.equal(d.source_kind,"SGX_ORIGINAL_ANNOUNCEMENT_HTML");
 assert.equal(d.official_current_asof_date,"2026-11-12");
 assert.equal(d.rows.length,3);
 assert.equal(d.rows.at(-1).trade_date,d.official_current_asof_date);
 assert.equal(d.latest_2026_11_13_official_original_retrieved,false);
 assert.equal(d.latest_2026_11_13_secondary_not_promoted,true);
 assert.match(d.source_2026_11_13_secondary_url,/^https:\/\/b\.siasset\.com\//);
 for(const k of ["all_sgx_buyback_announcements_to_date_verified","licensed_timestamped_trade_quote_verified","third_party_independent_financial_verification","current_market_cap_per_pbr_verified","ranking_eligible"]) assert.equal(d[k],false,"unsafe promotion "+k);
 for(let i=0;i<d.rows.length;i++){
  const r=d.rows[i],e=EXPECTED[i];
  assert.equal(r.trade_date,e[0]);assert.equal(r.announcement_ref,e[1]);
  assert.equal(r.cumulative_purchased_under_mandate,e[2]);
  assert.equal(r.issued_excluding_treasury_after_purchase,e[3]);
  assert.equal(r.purchased,34000);assert.equal(r.cancelled,34000);
  assert.equal(r.held_treasury_from_daily_purchase,0);
  assert.equal(r.treasury_shares_after_purchase,14548000);
  assert.ok(r.source_url.startsWith("https://links.sgx.com/1.0.0/corporate-announcements/"));
  assert.match(r.broadcast_sgt,/^2026-11-(10|11|12)T\d\d:\d\d:\d\d\+08:00$/);
  assert.equal(r.broadcast_sgt.slice(0,10),r.trade_date);
  if(i){
   assert.equal(d.rows[i-1].issued_excluding_treasury_after_purchase-r.issued_excluding_treasury_after_purchase,r.cancelled);
   assert.equal(r.cumulative_purchased_under_mandate-d.rows[i-1].cumulative_purchased_under_mandate,r.purchased);
  }
 }
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 const uob=f.records.find(x=>x.symbol==="U11");
 assert.ok(uob);assert.equal(uob.ranking_eligible,false);
 assert.equal(uob.price_sgd,null);
 return true;
}
validate(proof,feed);
for(const mutate of [
 (d,f)=>{d.official_current_asof_date="2026-11-13"},
 (d,f)=>{d.latest_2026_11_13_official_original_retrieved=true},
 (d,f)=>{d.rows[0].source_url="https://b.siasset.com/mirror"},
 (d,f)=>{d.rows[1].purchased=34001},
 (d,f)=>{d.rows[1].issued_excluding_treasury_after_purchase++},
 (d,f)=>{d.rows[2].cumulative_purchased_under_mandate++},
 (d,f)=>{d.rows[2].announcement_ref="SG261113OTHRHOAF"},
 (d,f)=>{d.rows[1].treasury_shares_after_purchase=0},
 (d,f)=>{d.ranking_eligible=true},
 (d,f)=>{d.current_market_cap_per_pbr_verified=true},
 (d,f)=>{f.ranking_eligible_count=1}
]){
 const a=[proof,feed].map(x=>structuredClone(x));mutate(...a);assert.throws(()=>validate(...a));
}
console.log("v242 PASS: UOB original SGX Nov 10/11/12 cancelled shares and ex-treasury count reconcile; Nov 13 secondary not promoted");
