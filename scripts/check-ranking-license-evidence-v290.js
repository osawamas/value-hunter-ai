"use strict";
const fs = require("node:fs");
const path = require("node:path");
const {checkFeed, validDate, sgxQuoteDate} = require("../docs/sgx-ranking-validation.js");

function checkRefresh(previous, candidate) {
  const errors = checkFeed(candidate);
  if (errors.length) return errors;
  const published = new Map(candidate.records.map(row => [row.symbol, row]));
  for (const row of previous.records) {
    if (row.ranking_eligible !== true) continue;
    const replacement = published.get(row.symbol);
    if (replacement?.ranking_eligible !== true) {
      errors.push(row.symbol + ": routine refresh would remove a ranked record");
      continue;
    }
    const previousSession = sgxQuoteDate(row.quote_timestamp_utc);
    const nextSession = sgxQuoteDate(replacement.quote_timestamp_utc);
    if (previousSession && nextSession < previousSession) {
      errors.push(row.symbol + ": routine refresh would roll back the ranked close");
    } else if (nextSession === previousSession && replacement.price_sgd !== row.price_sgd) {
      errors.push(row.symbol + ": routine refresh would replace a ranked close for the same session");
    }
  }
  return errors;
}

if (require.main === module) {
  try {
    const args = process.argv.slice(2);
    if (args.length && (args.length !== 1 || args[0] !== "--previous-stdin"))
      throw new Error("Usage: node scripts/check-ranking-license-evidence-v290.js [--previous-stdin]");
    const feed = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../docs/data/latest.json"), "utf8"));
    const errors = args.length ? checkRefresh(JSON.parse(fs.readFileSync(0, "utf8")), feed) : checkFeed(feed);
    if (errors.length) throw new Error(errors.join("\n"));
    console.log("v290 PASS: public feed ranking checks");
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
module.exports = {checkFeed, checkRefresh, validDate};
