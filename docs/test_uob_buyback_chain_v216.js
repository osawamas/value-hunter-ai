"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const research=JSON.parse(fs.readFileSync("docs/data/uob-buyback-chain-v216.json","utf8"));
const original=JSON.parse(fs.readFileSync("docs/data/sgx-bank-corporate-actions-v190.json","utf8"));
const microsite=JSON.parse(fs.readFileSync("docs/data/uob-share-display-research-v201.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function verify(d,o,m,f){
 assert.equal(d.schema_version,"uob-primary-share-buyback-chain-v216");
 assert.equal(d.symbol,"U11");assert.equal(d.isin,"SG1M31001969");
 assert.equal(d.earliest_official_date,"2026-10-20");
 assert.equal(d.latest_official_date,"2026-11-12");
 assert.equal(d.original_official_disclosures.length,3);
 assert.equal(d.displayed_issuer_microsite_shares_match_official_2026_10_20_number,true);
 assert.equal(d.issuer_microsite_effective_share_date_confirmed,false);
 assert.equal(d.issuer_microsite_share_basis_equivalent_to_sgx_ex_treasury_confirmed,false);
 assert.equal(d.original_2026_11_13_sgx_form_obtained,false);
 assert.equal(d.full_buyback_daily_originals_between_oct20_nov12_retrieved,false);
 assert.equal(d.later_2026_11_13_syndicated_count_not_officially_confirmed,true);
 assert.equal(d.cumulative_delta_equals_share_delta_on_observed_endpoints,true);
 assert.equal(d.official_current_outstanding_verified,false);
 assert.equal(d.licensed_timestamped_price_available,false);
 assert.equal(d.ranking_eligible,false);assert.equal(d.financial_feed_modified,false);
 assert.equal(f.ranking_enabled,false);assert.equal(f.ranking_eligible_count,0);
 const [oct,nov11,nov12]=d.original_official_disclosures;
 assert.equal(oct.announcement_reference,"SG261020OTHRZ7CY");
 assert.equal(oct.post_purchase_issued_ex_treasury,1646915591);
 assert.equal(oct.cumulative_market_buyback_since_mandate,6640600);
 assert.equal(oct.post_purchase_issued_ex_treasury,m.issuer_microsite.displayed_issued_paid_up_shares);
 assert.equal(nov11.announcement_reference,o.uob.observations[0].announcement_reference);
 assert.equal(nov12.announcement_reference,o.uob.observations[1].announcement_reference);
 assert.equal(nov11.post_purchase_issued_ex_treasury,o.uob.observations[0].issued_excluding_treasury_after);
 assert.equal(nov12.post_purchase_issued_ex_treasury,o.uob.observations[1].issued_excluding_treasury_after);
 assert.equal(nov11.announcement_url,o.uob.observations[0].source_url);
 assert.equal(nov12.announcement_url,o.uob.observations[1].source_url);
 assert.deepEqual([oct.cumulative_market_buyback_since_mandate,
 nov11.cumulative_market_buyback_since_mandate,
 nov12.cumulative_market_buyback_since_mandate],[6640600,6810600,6844600]);
 for(const x of d.original_official_disclosures){
  assert.equal(x.treasury_after,14548000);
  assert.match(x.announcement_url,/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\//);
 }
 for(let i=0;i<2;i++){
  const a=d.original_official_disclosures[i],b=d.original_official_disclosures[i+1];
  assert.equal(a.post_purchase_issued_ex_treasury-b.post_purchase_issued_ex_treasury,
   b.cumulative_market_buyback_since_mandate-a.cumulative_market_buyback_since_mandate);
 }
 assert.equal(oct.post_purchase_issued_ex_treasury-nov12.post_purchase_issued_ex_treasury,204000);
 assert.equal(nov12.cumulative_market_buyback_since_mandate-oct.cumulative_market_buyback_since_mandate,204000);
 assert.equal(o.verified_as_of_date,d.latest_official_date);
 assert.equal(o.uob.latest_unverified.official_verified,false);
 assert.equal(o.uob.latest_unverified.may_enter_ranking,false);
 assert.equal(m.original_nov13_sgx_filing_downloaded,false);
 assert.equal(m.issuer_page_share_timestamp_verified,false);
 return true;
}
verify(research,original,microsite,feed);
for(const edit of [
 (d,o,m,f)=>{d.original_official_disclosures[0].post_purchase_issued_ex_treasury++},
 (d,o,m,f)=>{d.original_official_disclosures[1].cumulative_market_buyback_since_mandate++},
 (d,o,m,f)=>{d.issuer_microsite_effective_share_date_confirmed=true},
 (d,o,m,f)=>{d.original_2026_11_13_sgx_form_obtained=true},
 (d,o,m,f)=>{d.official_current_outstanding_verified=true},
 (d,o,m,f)=>{d.original_official_disclosures[0].treasury_after++},
 (d,o,m,f)=>{o.uob.latest_unverified.official_verified=true},
 (d,o,m,f)=>{f.ranking_eligible_count++}
]){
 const d=structuredClone(research),o=structuredClone(original),m=structuredClone(microsite),f=structuredClone(feed);
 edit(d,o,m,f);assert.throws(()=>verify(d,o,m,f));
}
console.log("v216 PASS: official UOB Oct20-Nov12 cumulative repurchase delta equals 204,000 cancelled shares; Nov13 is still unverified");
