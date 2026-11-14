"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const seed=JSON.parse(fs.readFileSync("docs/data/sgx-official-batch-seed-v196.json","utf8"));
const first=JSON.parse(fs.readFileSync("docs/data/sgx-additional-issuer-fy2025-v206.json","utf8"));
const doc=JSON.parse(fs.readFileSync("docs/data/sgx-remaining-issuer-research-v207.json","utf8"));
function verify(d,f,s,t){
 assert.equal(d.schema_version,"sgx-remaining-official-seed-fy2025-research-v207");
 assert.equal(d.period_end,"2025-12-31");
 assert.equal(d.all_sources_externally_audited_independently,false);
 assert.equal(d.primary_pdf_bytes_and_sha_checked,false);
 assert.equal(d.financial_feed_registered_increment,0);
 assert.equal(d.ranking_eligible_increment,0);
 assert.equal(d.cross_currency_peer_ranking_allowed,false);
 assert.equal(d.market_price_license_verified,false);
 assert.equal(d.current_ex_treasury_shares_verified,false);
 assert.equal(f.ranking_enabled,false);
 assert.equal(f.ranking_eligible_count,0);
 assert.equal(f.coverage.registered_count,7);
 const expected={
  "G07":{currency:"SGD",metric:"PROFIT_ATTRIBUTABLE_TO_SHAREHOLDERS",fy25:1207.1},
  "H02":{currency:"SGD",metric:"GROUP_REVENUE",fy25:229.967},
  "C07":{currency:"USD",metric:"UNDERLYING_NET_PROFIT",fy25:1110},
  "J36":{currency:"USD",metric:"UNDERLYING_PROFIT_ATTRIBUTABLE_SHAREHOLDERS",fy25:1681},
  "K6S":{currency:"USD",metric:"FY2025_IFRS_PROFIT_AFTER_TAX",fy25:4119}
 };
 assert.equal(d.items.length,5);
 const symbols=d.items.map(x=>x.symbol).sort();
 assert.deepEqual(symbols,Object.keys(expected).sort());
 assert.equal(t.items.length,2);
 const combined=[...d.items,...t.items].map(x=>x.symbol);
 const research=new Set(combined);
 assert.equal(research.size,combined.length);
 assert.equal(research.size,7);
 const registered=new Set(f.records.map(x=>x.symbol));
 for(const row of s.rows)assert.ok(registered.has(row.symbol)||research.has(row.symbol));
 for(const r of d.items){
  const ex=expected[r.symbol];
  assert.ok(s.rows.some(x=>x.symbol===r.symbol));
  assert.ok(!registered.has(r.symbol));
  assert.equal(r.reporting_currency,ex.currency);
  assert.equal(r.independently_verified,false);
  assert.equal(r.financial_feed_registered,false);
  assert.equal(r.ranking_eligible,false);
  assert.match(r.source_url,/^https:\/\//);
  assert.ok(Array.isArray(r.metrics)&&r.metrics.length>=1);
  const v=r.metrics.find(x=>x.name===ex.metric);
  assert.ok(v);
  assert.equal(v.y2025,ex.fy25);
  assert.equal(v.unit,ex.currency+"_millions");
 }
 assert.equal(d.items.find(x=>x.symbol==="C07").trading_currency,"SGD");
 assert.equal(d.items.find(x=>x.symbol==="C07").reporting_currency,"USD");
 assert.equal(d.items.find(x=>x.symbol==="J36").underlying_and_reported_not_interchangeable,true);
 assert.equal(d.items.find(x=>x.symbol==="K6S").ifrs_and_adjusted_metrics_not_comparable,true);
 return true;
}
verify(doc,feed,seed,first);
const html=fs.readFileSync("docs/index.html","utf8");
const {validate}=require("./remaining-issuer-research-v207.js");
assert.ok(html.includes('src="./remaining-issuer-research-v207.js"'));
assert.ok(html.includes('id="remainingIssuerResearchRows"'));
assert.ok(html.includes('id="remainingIssuerResearchStatus"'));
const displayed=validate(feed,seed,doc,first);
assert.deepEqual(displayed.map(x=>[x.symbol,x.currency,x.amount]),[
 ["G07","SGD",1207.1],["H02","SGD",229.967],["C07","USD",1110],
 ["J36","USD",1109],["K6S","USD",4119]
]);

for(const mutate of [
 (d,f,s,t)=>{d.items[0].ranking_eligible=true},
 (d,f,s,t)=>{d.items[2].reporting_currency="SGD"},
 (d,f,s,t)=>{d.items[4].metrics[0].y2025=3306},
 (d,f,s,t)=>{d.primary_pdf_bytes_and_sha_checked=true},
 (d,f,s,t)=>{d.items.push({...d.items[0]})},
 (d,f,s,t)=>{t.items.push({...d.items[0]})},
 (d,f,s,t)=>{f.ranking_eligible_count=1}
]){
 const x=structuredClone(doc),y=structuredClone(feed),z=structuredClone(seed),w=structuredClone(first);
 mutate(x,y,z,w);assert.throws(()=>verify(x,y,z,w));
}
console.log("v207 PASS: all seven missing from registered financial feed have research leads; mixed currencies and profit definitions remain separate");
