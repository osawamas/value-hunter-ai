"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const child=require("node:child_process");
const manifest=JSON.parse(fs.readFileSync("docs/data/sgx-ipo-financial-documents-v297.json","utf8"));
const ipo=JSON.parse(fs.readFileSync("docs/data/sgx-october-ipo-listing-v294.json","utf8"));
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
assert.equal(manifest.schema_version,"sgx-ipo-original-pdf-replay-v297");
assert.equal(manifest.original_pdf_content_checks_confirmed,3);
assert.equal(manifest.original_pdf_sha256_digests_from_real_github_actions,true);
assert.equal(manifest.sources.length,3);
assert.deepEqual(manifest.sources.map(x=>x.github_actions_confirmed_original_bytes),[8575301,8930729,160619]);
assert.deepEqual(manifest.sources.map(x=>x.github_actions_confirmed_sha256),[
 "6472db7e48bc45db8a056d196157d03589bf4ef880ee94eba3fd837b53c028de",
 "d6b49948af8167e6d2443ae22f7538907c46e94d62b414843e8444abc05f342c",
 "19d2b43322c36001e560d14f43650b0f6feab5e280770e42bb529ee63cd5ef60"
]);
for(const source of manifest.sources){
 assert.match(source.url,/^https:\/\/links\.sgx\.com\/FileOpen\//);
 assert.match(source.github_actions_confirmed_sha256,/^[a-f0-9]{64}$/);
 assert.equal(source.original_replay_run_id,43676027936);
 assert.ok(ipo.issuer_listing_confirmations.find(i=>i.trading_code===source.symbol));
}
assert.equal(manifest.sources[0].historical_audited_periods.at(-1),"2026-03-31");
assert.equal(manifest.sources[1].historical_audited_periods.at(-1),"2025-12-31");
assert.deepEqual(manifest.sources[2].historical_audited_periods,[]);
assert.equal(manifest.quote_feed_license_verified,false);
assert.equal(manifest.up_to_date_independent_financial_verification_complete,false);
assert.equal(feed.records.length,7);
assert.equal(feed.ranking_eligible_count,0);
assert.equal(feed.ranking_enabled,false);
const p=child.spawnSync("python3",["scripts/test_sgx_ipo_financial_pdfs_v297.py"],{encoding:"utf8",timeout:30000});
assert.equal(p.status,0,p.stderr||p.stdout);
console.log("v297 PASS: 3 real SGX raw PDF SHA256 fixed, distinct audited FY/unaudited 9M source scope, ranking 0");
