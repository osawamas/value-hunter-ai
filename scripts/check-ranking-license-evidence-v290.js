"use strict";
/* SGX v290 production feed license evidence guard.  A checkbox does not establish
 * rights.  A dated grant, permission scopes and application identity are required.
 * Local structure checks DO NOT independently establish legal authenticity.
 */
const fs = require("node:fs");
const path = require("node:path");
const {checkFeed: checkV289, sgxQuoteDate, validDate} = require("./check-ranking-provenance-v289.js");
function validHTTPS(v) {
  if (typeof v !== "string" || !/^https:\/\//i.test(v)) return false;
  try { const u = new URL(v); return Boolean(u.hostname && !u.username && !u.password); }
  catch { return false; }
}
function checkFeed(feed) {
  const errors=checkV289(feed);
  if(!feed || !Array.isArray(feed.records)) return errors;
  for (const [i,r] of feed.records.entries()) {
    if(r.ranking_eligible !== true) continue;
    const id=String(r.symbol||("row_"+i));
    const proof=r.market_data_license_evidence;
    if(!proof || typeof proof !== "object" || Array.isArray(proof)) {
      errors.push(id+": dated grant evidence missing"); continue;
    }
    if(proof.grant_status !== "EXECUTED" ||
       !validHTTPS(proof.grant_evidence_url) ||
       typeof proof.licensor !== "string" || !proof.licensor.trim() ||
       typeof proof.licensee !== "string" || !proof.licensee.trim() ||
       typeof proof.licensed_product !== "string" || !proof.licensed_product.trim())
      errors.push(id+": executed license provenance incomplete");
    // Eligible rows publish the raw close in latest.json and in the dashboard CSV.
    const scopes=proof.usage_scopes;
    if(!Array.isArray(scopes) ||
       !scopes.includes("BROWSER_DISPLAY") ||
       !scopes.includes("BACKEND_NON_DISPLAY_ANALYTICS") ||
       !scopes.includes("REDISTRIBUTION"))
      errors.push(id+": required SGX usage scopes missing");
    if(!validDate(proof.valid_from) || !validDate(proof.valid_until) ||
       proof.valid_from > proof.valid_until)
      errors.push(id+": license validity dates incorrect");
    else {
      const quoteDate=sgxQuoteDate(r.quote_timestamp_utc);
      if(!quoteDate || quoteDate<proof.valid_from || quoteDate>proof.valid_until)
        errors.push(id+": quote timestamp outside license validity");
    }
    if(!validHTTPS(r.quote_url))
      errors.push(id+": licensed quote origin URL missing");
  }
  return errors;
}
if(require.main===module){
 const feed=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../docs/data/latest.json"),"utf8"));
 const errors=checkFeed(feed);
 if(errors.length){console.error(errors.join("\n"));process.exitCode=1}
 else console.log("v290 PASS: real feed fail-closed; no license inferred");
}
module.exports={checkFeed,validDate};
