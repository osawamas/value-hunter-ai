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

function reviewQuoteRefresh(rows, shareReview, previous, current) {
  const latest = reviewRepresentativeValuations(rows, shareReview, current);
  const updates = latest.results.map(result => {
    const {id, date} = result;
    const key = id + ":" + date;
    const before = previous.get(key);
    const after = current.get(key);
    let change = "absent";
    if (after && !before) change = "added";
    else if (after && before) change = after.price === before.price ? "unchanged" : "revised";
    else if (before) change = "removed";

    const newer = [...current.values()].filter(quote => quote.id === id && date && quote.date > date)
      .map(quote => quote.date).sort();
    return {...result, closeChange: change, previousPrice: before?.price ?? null,
      newerUnmatchedDates: newer};
  });
  return {scope: latest.scope, results: updates};
}

function main(args) {
  const refresh = args[0] === "--compare" && args.length === 3;
  if (!refresh && (args.length > 1 || args[0] === "--compare")) {
    throw Error("Usage: node scripts/check-representative-valuations.js [local-quotes.csv] or --compare previous.csv current.csv");
  }
  const research = loadSnapshot("market-research-v315.json");
  const sgx = loadSnapshot("latest.json");
  const shareReview = loadSnapshot("sgx-s63-two-website-close-v129.json");
  const rows = buildMarketRows(research, sgx);
  const loadQuotes = filename => readQuoteHistory(fs.readFileSync(filename, "utf8"));
  const report = refresh ?
    reviewQuoteRefresh(rows, shareReview, loadQuotes(args[1]), loadQuotes(args[2])) :
    reviewRepresentativeValuations(rows, shareReview, args.length ? loadQuotes(args[0]) : new Map());
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

module.exports = {reviewRepresentativeValuations, reviewQuoteRefresh};
