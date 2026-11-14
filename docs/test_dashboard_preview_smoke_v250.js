"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const script=fs.readFileSync("scripts/verify-preview-archive-v250.py","utf8");
const workflow=fs.readFileSync(".github/workflows/value-hunter-pages.yml","utf8");
const feed=JSON.parse(fs.readFileSync("docs/data/latest.json","utf8"));
const checklist=[
 /z\.testzip\(\)/,/MAX_UNCOMPRESSED/,/MAX_FILES/,/Duplicate path/,
 /Unsafe file path/,/Symlinks are not allowed/,
 /docs\/data\/latest\.json/,/docs\/README-PREVIEW-v249\.md/,
 /feed\.get\("ranking_enabled"\) is not False/,
 /feed\.get\("ranking_eligible_count"\) != 0/,
 /http\.server\.ThreadingHTTPServer/,
 /urllib\.request\.urlopen/,/server\.shutdown\(\)/,
 /github_pages_deployed_verified/,/licensed_sgx_quotes_verified/
];
for(const pattern of checklist)assert.match(script,pattern);
assert.match(workflow,/name: Verify extracted ZIP assets, local HTTP loads, and ranking hold/);
assert.match(workflow,/python3 scripts\/verify-preview-archive-v250\.py build\/preview\/value-hunter-dashboard-preview-v249\.zip/);
assert.match(workflow,/name: value-hunter-dashboard-preview-smoke-v250/);
assert.match(workflow,/name: value-hunter-dashboard-preview-v249/);
assert.ok(workflow.indexOf("Verify extracted ZIP assets")<workflow.indexOf("Retain downloadable dashboard preview"));
assert.equal(feed.ranking_enabled,false);
assert.equal(feed.ranking_eligible_count,0);
console.log("v250 PASS: real ZIP + HTTP smoke verification is a mandatory pre-upload step, independent of Pages and ranking");
