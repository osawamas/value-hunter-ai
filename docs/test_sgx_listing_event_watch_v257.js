"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const {validate}=require("./sgx-listing-event-watch-v257.js");
const data=JSON.parse(fs.readFileSync("docs/data/sgx-material-listing-events-v257.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
function check(d,f){
 const rows=validate(d,f);
 assert.equal(rows.length,2);
 assert.deepEqual(rows.map(x=>x.symbol),["5WA","P11"]);
 assert.equal(rows[0].status,"PENDING_COURT_AND_EXCHANGE_APPROVAL");
 assert.equal(rows[0].provisionalDelist,"2026-12-23");
 assert.equal(rows[1].status,"RESTRUCTURING_MONITOR");
 assert.equal(rows[1].provisionalDelist,null);
 assert.ok(rows.every(x=>x.eligible===false));
}
check(data,feed);
for(const m of [
 (d,f)=>{d.events[0].delisted_confirmed=true},
 (d,f)=>{d.events[1].active_listing_today_confirmed=true},
 (d,f)=>{d.events[0].dates_are_firm=true},
 (d,f)=>{d.events[0].indicative_delisting_date="2026-12-24"},
 (d,f)=>{d.events[1].indicative_delisting_date="2026-12-31"},
 (d,f)=>{d.events[0].source_url="https://fake.test/announcement"},
 (d,f)=>{d.events[0].ranking_eligible=true},
 (d,f)=>{d.events[0].event_code="DELISTED"},
 (d,f)=>{d.definitive_current_trading_status_verified=true},
 (d,f)=>{d.latest_licensed_market_price_available=true},
 (d,f)=>{d.complete_master_covered=true},
 (d,f)=>{d.events.push(structuredClone(d.events[0]))},
 (d,f)=>{f.ranking_eligible_count=1}
]){const d=structuredClone(data),f=structuredClone(feed);m(d,f);assert.throws(()=>check(d,f))}
const html=fs.readFileSync("docs/index.html","utf8");
assert.match(html,/src="\.\/sgx-listing-event-watch-v257\.js"/);
assert.match(html,/id="sgxListingEventRows"/);
assert.match(html,/id="sgxListingEventStatus"/);
console.log("v257 PASS: 5WA and P11 risky corporate events displayed as pending, never falsely delisted or rank eligible");
