"use strict";

const fs = require("node:fs");
const {buildMarketRows, conflictingFilingShares, publishedShareSessions} = require("../docs/market-research.js");
const {validDate} = require("../docs/sgx-ranking-validation.js");

function reviewS63(feed, research, notices, session) {
  if (!validDate(session)) throw new Error("Expected a Singapore trading date (YYYY-MM-DD)");
  const rows = buildMarketRows(research, feed).filter(row => row.id === "SG:S63");
  const issuer = rows[0];
  if (!issuer?.sgxEvidence) throw new Error("S63 is absent from the SGX feed");
  const sessions = publishedShareSessions(rows, notices);
  const matched = sessions.get(session)?.[0];
  const conflicts = conflictingFilingShares(issuer, session, notices);
  return {
    symbol: issuer.symbol,
    session,
    matchedShares: matched ?? null,
    conflictingShares: conflicts ?? null,
    availableShareDates: [...sessions.keys()],
    currentFeedShareDate: issuer.sgxEvidence.shares_as_of_date,
    currentFeedExclusions: issuer.sgxEvidence.exclusion_reasons,
    independentlyVerifiedFinancials:
      issuer.sgxEvidence.independent_cross_source_verification === true,
  };
}

if (require.main === module) {
  try {
    const [feedPath, session] = process.argv.slice(2);
    const feed = JSON.parse(fs.readFileSync(feedPath, "utf8"));
    const report = reviewS63(feed, require("../docs/data/market-research-v315.json"), [
      require("../docs/data/sgx-s63-two-website-close-v129.json"),
      require("../docs/data/sgx-s63-historical-shares-v423.json"),
    ], session);
    process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = {reviewS63};
