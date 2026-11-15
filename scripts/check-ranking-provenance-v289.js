"use strict";
/* v289: Fail closed on quote rights / independent evidence before investment
   ranking. This is a local feed-integrity gate, NOT evidence of market licensing. */
const fs = require("node:fs");
const path = require("node:path");
const UNOFFICIAL = /YAHOO|UNOFFICIAL|SCRAP|COMMUNITY|MANUAL|USER_INPUT/i;
const singaporeDate = new Intl.DateTimeFormat("sv-SE", {timeZone: "Asia/Singapore"});
function validDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + "T00:00:00Z");
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
function sgxQuoteDate(value) {
  if (typeof value !== "string" ||
      !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) ||
      !validDate(value.slice(0, 10))) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) ? singaporeDate.format(time) : null;
}
function checkFeed(feed) {
  const errors = [];
  if (!feed || !Array.isArray(feed.records)) return ["Missing records array"];
  const seen = new Set();
  let eligible = 0;
  for (const [i, r] of feed.records.entries()) {
    const id = String(r.symbol || ("row_" + i));
    if (seen.has(id)) errors.push(id + ": duplicate symbol");
    seen.add(id);
    const reasons = Array.isArray(r.exclusion_reasons) ? r.exclusion_reasons : [];
    if (r.ranking_eligible === true) {
      eligible++;
      if (r.ranking_score == null || !Number.isFinite(r.ranking_score))
        errors.push(id + ": ranking score missing/invalid");
      if (UNOFFICIAL.test(String(r.quote_source_type || "")))
        errors.push(id + ": unofficial quote in investable ranking");
      if (r.quote_license_display_allowed !== true ||
          r.quote_license_non_display_analytics_allowed !== true)
        errors.push(id + ": both quote display/non-display licenses not evidenced");
      if (r.independent_cross_source_verification !== true)
        errors.push(id + ": independent financial evidence not verified");
      if (!Number.isInteger(r.shares_outstanding) || r.shares_outstanding <= 0 ||
          r.shares_count_basis !== "issued_excluding_treasury")
        errors.push(id + ": ex-treasury share count not verified");
      const quoteDate = sgxQuoteDate(r.quote_timestamp_utc);
      if (!quoteDate || !validDate(r.shares_as_of_date))
        errors.push(id + ": missing dated quote/shares");
      else if (r.shares_as_of_date !== quoteDate)
        errors.push(id + ": quote and shares are not on the same Singapore date");
      if (reasons.length) errors.push(id + ": eligible while exclusion reasons remain");
    } else {
      if (r.ranking_score != null) errors.push(id + ": excluded record has ranking score");
    }
  }
  if (eligible !== feed.ranking_eligible_count) errors.push("eligible count differs from rows");
  if (Boolean(feed.ranking_enabled) !== (eligible > 0))
    errors.push("ranking_enabled inconsistent with eligible rows");
  if (feed.coverage && feed.coverage.registered_count !== feed.records.length)
    errors.push("registered_count inconsistent with records");
  return errors;
}
if (require.main === module) {
  const file = path.resolve(__dirname, "../docs/data/latest.json");
  const errors = checkFeed(JSON.parse(fs.readFileSync(file, "utf8")));
  if (errors.length) { console.error(errors.join("\\n")); process.exitCode = 1; }
  else console.log("v289 PASS: published feed ranking requires licensed quote plus independently verified financials");
}
module.exports = {checkFeed, sgxQuoteDate, validDate};
