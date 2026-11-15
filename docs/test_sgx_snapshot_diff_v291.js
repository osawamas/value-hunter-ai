"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),os=require("node:os"),{execFileSync}=require("node:child_process");
const {normalize}=require("../scripts/stage-sgx-csv-v199.js");
const {diff,validate,parseDate}=require("../scripts/diff-sgx-snapshots-v291.js");
const source="https://www.sgx.com/securities/securities-prices?code=stocks";
const oldRaw="Trading Code,Trading Name,Traded Currency,Instrument Type,Listing Board\nD05,DBS Group,SGD,STOCK,MAINBOARD\nU11,UOB,SGD,STOCK,MAINBOARD\nS68,SGX,SGD,STOCK,MAINBOARD\n";
const newRaw="Trading Code,Trading Name,Traded Currency,Instrument Type,Listing Board\nD05,DBS Group Holdings,SGD,STOCK,MAINBOARD\nU11,UOB,USD,STOCK,MAINBOARD\nG13,Genting Singapore,SGD,STOCK,MAINBOARD\n";
const old=normalize(oldRaw,{as_of_date:"2026-11-12",source_url:source});
const newer=normalize(newRaw,{as_of_date:"2026-11-15",source_url:source});
const result=diff(old,newer);
assert.deepEqual(result.counts,{added:2,removed:2,changed:1,code_variants:1});
assert.deepEqual(result.code_currency_or_instrument_type_changes_for_review,["U11"]);
assert.ok(result.possible_removals.find(x=>x.identity==="S68|SGD|STOCK"));
assert.ok(result.possible_additions.find(x=>x.identity==="G13|SGD|STOCK"));
assert.ok(result.metadata_changes.find(x=>x.identity==="D05|SGD|STOCK"));
assert.equal(result.confirmed_listing_events,false);
assert.equal(result.ranking_enabled,false);
assert.equal(result.published_feed_modified,false);
assert.equal(result.completeness_verified,false);
assert.throws(()=>parseDate("2026-02-30"));
assert.throws(()=>diff(newer,old));
assert.throws(()=>diff(old,old));
for(const mutate of [
 x=>x.ranking_enabled=true,
 x=>x.full_sgx_universe_verified=true,
 x=>x.source_authentication="VERIFIED",
 x=>x.original_csv_sha256="invalid",
 x=>x.items.push({...x.items[0]}),
 x=>x.items[0].trading_code="../"
]){const c=structuredClone(old);mutate(c);assert.throws(()=>validate(c));}
const dir=fs.mkdtempSync(path.join(os.tmpdir(),"sgx-v291-"));
try{
 const p1=path.join(dir,"old.csv"),p2=path.join(dir,"new.csv"),out=path.join(dir,"changes.json");
 fs.writeFileSync(p1,oldRaw);fs.writeFileSync(p2,newRaw);
 execFileSync(process.execPath,["scripts/diff-sgx-snapshots-v291.js","--older",p1,"--older-date","2026-11-12","--older-url",source,"--newer",p2,"--newer-date","2026-11-15","--newer-url",source,"--out",out],{cwd:path.resolve(__dirname,"..")});
 assert.equal(JSON.parse(fs.readFileSync(out,"utf8")).counts.added,2);
 assert.throws(()=>execFileSync(process.execPath,["scripts/diff-sgx-snapshots-v291.js","--older",p1,"--older-date","2026-11-12","--older-url",source,"--newer",p2,"--newer-date","2026-11-15","--newer-url",source,"--out",out],{cwd:path.resolve(__dirname,".."),stdio:"pipe"}));
}finally{fs.rmSync(dir,{recursive:true,force:true});}
console.log("v291 PASS: local SGX snapshot delta, SHA preservation, no false delisting, no feed/rank promotion");

