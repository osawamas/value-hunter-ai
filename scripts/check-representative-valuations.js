"use strict";

const fs = require("node:fs");
const path = require("node:path");
const {
  buildMarketRows, evaluatePersonalQuotes, publishedShareSessions, readQuoteHistory,
} = require("../docs/market-research.js");

const data = path.join(__dirname, "../docs/data");
const representatives = ["JP:7203", "US:IBM", "SG:S63"];

function loadSnapshot(name) {
  return JSON.parse(fs.readFileSync(path.join(data, name), "utf8"));
}

function reviewRepresentativeValuations(rows, shareReview, history = new Map()) {
  const dates = publishedShareSessions(rows, shareReview);
  const results = representatives.map(id => {
    const issuer = rows.find(row => row.id === id);
    const latest = [...dates].find(([, records]) => records.some(record => record.id === id));
    if (!issuer || !latest) return {id, status: "missing_share_evidence"};
    const [date, records] = latest;
    const shares = records.find(record => record.id === id);
    const observation = history.get(id + ":" + date);
    const evidence = {id, date, shares: shares.value, shareSource: shares.source};
    if (!observation) return {...evidence, status: "missing_exact_close"};
    const [valuation] = evaluatePersonalQuotes(rows, new Map([[id, observation]]), new Map(), shareReview);
    if (valuation.state !== "filing" || !valuation.result) return {...evidence, status: valuation.state};
    return {...evidence, status: "trial_calculated", price: observation.price,
      financeSource: valuation.financeSource, valuation: valuation.result};
  });
  return {scope: "local_trial", results};
}

function main(args) {
  if (args.length > 1) throw Error("Usage: node scripts/check-representative-valuations.js [local-quotes.csv]");
  const research = loadSnapshot("market-research-v315.json");
  const sgx = loadSnapshot("latest.json");
  const shareReview = loadSnapshot("sgx-s63-two-website-close-v129.json");
  const quotes = args.length ? readQuoteHistory(fs.readFileSync(args[0], "utf8")) : new Map();
  const report = reviewRepresentativeValuations(buildMarketRows(research, sgx), shareReview, quotes);
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(error.message + "\n");
    process.exitCode = 1;
  }
}

module.exports = {reviewRepresentativeValuations};
