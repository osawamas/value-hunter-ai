"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const {compose,build}=require("../scripts/build-sgx-ipo-candidate-union-v295.js");
const read=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const result=build();
assert.equal(result.total_distinct_historical_codes,32);
assert.equal(result.provenance.historical_code_count,30);
assert.equal(result.provenance.dated_sgx_st_ipo_count,2);
assert.equal(result.provenance.third_party_candidate_count,182);
assert.deepEqual(result.provenance.confirmed_ipo_absent_from_third_party,["9DC","MIM"]);
assert.equal(new Set(result.entries.map(x=>x.symbol)).size,32);
assert.equal(result.entries.filter(x=>x.ipo_admission_event).length,2);
for(const [symbol,isin] of [["9DC","SGXE96931105"],["MIM","SGXE49931863"]]){
 const x=result.entries.find(x=>x.symbol===symbol);
 assert.equal(x.isin,isin);
 assert.equal(x.source_class,"ORIGINAL_SGX_ST_DATED_IPO_ADMISSION");
 assert.equal(x.ranking_eligible,false);
 assert.equal(x.current_active_listing_verified,false);
 assert.match(x.primary_source_url,/^https:\/\/links\.sgx\.com\//);
}
assert.equal(result.full_current_sgx_security_master_verified,false);
assert.equal(result.market_data_license_verified,false);
assert.equal(result.financial_feed_modified,false);
assert.equal(result.investment_ranking_enabled,false);
assert.equal(result.ranking_eligible_count,0);
const hist=result.entries.filter(x=>!x.ipo_admission_event).map(x=>({
 code:x.symbol,name:x.issuer,isin:x.isin,source:x.primary_source_url,
 ranking_eligible:false,all_current_trading_verified:false,financial_or_quote_verified:false
}));
const ipo=read("docs/data/sgx-october-ipo-listing-v294.json"),
third=read("docs/data/sgx-universe-candidates.json"),feed=read("docs/data/latest.json");
function fail(mutator){
 const items=structuredClone(hist),ip=structuredClone(ipo),c=structuredClone(third),f=structuredClone(feed);
 mutator(items,ip,c,f);assert.throws(()=>compose(items,ip,c,f));
}
fail((h)=>{h[0].code="9DC"});
fail((h)=>{h[0].ranking_eligible=true});
fail((h)=>{h.pop()});
fail((h,i)=>{i.issuer_listing_confirmations[0].ranking_eligible=true});
fail((h,i,c)=>{c.eligible_for_ranking=true});
fail((h,i,c)=>{c.candidates[0].ranking_eligible=true});
fail((h,i,c,f)=>{f.ranking_enabled=true});
console.log("v295 PASS: merged 30+2 historical SGX identities, absent IPOs in 182 candidates, no finance/ranking promotion");
