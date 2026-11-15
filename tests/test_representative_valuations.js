"use strict";

const assert = require("node:assert/strict");
const {buildMarketRows, evaluatePersonalQuotes, personalBatchCsv, readQuoteHistory} = require("../docs/market-research.js");
const {reviewRepresentativeValuations, reviewQuoteRefresh} = require("../scripts/check-representative-valuations.js");
const research = require("../docs/data/market-research-v315.json");
const sgx = require("../docs/data/latest.json");
const shares = require("../docs/data/sgx-s63-two-website-close-v129.json");
const rows = buildMarketRows(research, sgx);
const noQuotes = reviewRepresentativeValuations(rows, shares);
assert.deepEqual(noQuotes.results.map(row => [row.id, row.date, row.status]), [
  ["JP:7203", "2026-09-30", "missing_exact_close"],
  ["US:IBM", "2026-09-30", "missing_exact_close"],
  ["SG:S63", "2026-11-13", "missing_exact_close"],
]);

const quotes = readQuoteHistory([
  "market_id,date,currency,close",
  "JP:7203,2026-09-30,JPY,2500",
  "JP:7203,2026-10-01,JPY,3000",
  "US:IBM,2026-09-30,USD,200",
  "SG:S63,2026-11-12,SGD,11",
  "SG:S63,2026-11-13,SGD,10",
].join("\n"));
const calculated = reviewRepresentativeValuations(rows, shares, quotes);
assert.equal(calculated.scope, "local_trial");
assert.equal(calculated.basis, "retrospective");
assert.deepEqual(calculated.results.map(row => [row.shareDisclosureDate, row.shareDisclosedAfterSession]), [
  ["2026-11-05", true], ["2026-10-22", true], ["2026-11-13", true],
]);
const s63 = calculated.results[2];
assert.equal(s63.shareDisclosedAt, "2026-11-13T18:21:18+08:00");
assert.equal(s63.shareDisclosureTiming, "after_close");
const s63Quote = new Map([["SG:S63", quotes.get("SG:S63:2026-11-13")]]);
const exported = personalBatchCsv(evaluatePersonalQuotes(rows, s63Quote, new Map(), shares));
assert.match(exported, /,share_disclosure_date,share_disclosed_at,share_disclosure_timing/);
assert.match(exported, /,"2026-11-13","2026-11-13T18:21:18\+08:00","after_close"/);
for (const unusable of [undefined, "2026-11-14T17:16:00+08:00", "2026-11-13T17:16:00Z"]) {
  const evidence = {...shares, sgx_session_end_at_sgt: unusable};
  const result = reviewRepresentativeValuations(rows, evidence, quotes).results[2];
  assert.equal(result.shareDisclosureTiming, "time_unknown");
  assert.equal(result.shareDisclosedAfterSession, null);
}
const onTime = {...shares, sgx_share_disclosed_at_sgt: shares.sgx_session_end_at_sgt};
assert.equal(reviewRepresentativeValuations(rows, onTime, quotes).results[2].shareDisclosedAfterSession, false);
assert.deepEqual(calculated.results.map(row => [row.price, row.valuation.cap]), [
  [2500, 29445618282500], [200, 189024161000], [10, 31158471150],
]);
assert.ok(calculated.results.every(row => row.status === "trial_calculated" &&
  row.valuation.per > 0 && row.valuation.pbr > 0 && row.financeSource.startsWith("https://")));
quotes.delete("SG:S63:2026-11-13");
assert.equal(reviewRepresentativeValuations(rows, shares, quotes).results[2].status, "missing_exact_close");
const current = readQuoteHistory([
  "market_id,date,currency,close",
  "JP:7203,2026-09-30,JPY,2501",
  "JP:7203,2026-10-01,JPY,3000",
  "US:IBM,2026-10-01,USD,210",
  "SG:S63,2026-11-13,SGD,10",
].join("\n"));
const refreshed = reviewQuoteRefresh(rows, shares, quotes, current).results;
assert.deepEqual(refreshed.map(row => row.closeChange), ["revised", "removed", "added"]);
assert.equal(refreshed[0].previousPrice, 2500);
assert.equal(refreshed[0].valuation.cap, 2501 * 11778247313);
assert.equal(refreshed[1].status, "missing_exact_close");
assert.equal(refreshed[1].valuation, undefined);
assert.deepEqual(refreshed[1].newerUnmatchedDates, ["2026-10-01"]);
assert.equal(refreshed[2].status, "trial_calculated");
assert.deepEqual(reviewQuoteRefresh(rows, shares, current, current).results.map(row => row.closeChange),
  ["unchanged", "absent", "unchanged"]);
assert.deepEqual(refreshed[0].sessionChanges, [
  {date: "2026-09-30", change: "revised", previousPrice: 2500, currentPrice: 2501, hasExactShares: true},
  {date: "2026-10-01", change: "unchanged", previousPrice: 3000, currentPrice: 3000, hasExactShares: false},
]);
assert.deepEqual(refreshed[2].sessionChanges, [
  {date: "2026-11-12", change: "removed", previousPrice: 11, currentPrice: null, hasExactShares: false},
  {date: "2026-11-13", change: "added", previousPrice: null, currentPrice: 10, hasExactShares: true},
]);
const updated = readQuoteHistory([
  "market_id,date,currency,close",
  "JP:7203,2026-03-31,JPY,2900",
  "JP:7203,2026-09-30,JPY,2501",
  "JP:7203,2026-10-01,JPY,3010",
  "JP:7201,2026-10-01,JPY,300",
].join("\n"));
const subsequent = reviewQuoteRefresh(rows, shares, current, updated).results[0];
assert.equal(subsequent.closeChange, "unchanged");
assert.deepEqual(subsequent.newerUnmatchedDates, ["2026-10-01"]);
assert.deepEqual(subsequent.sessionChanges, [
  {date: "2026-03-31", change: "added", previousPrice: null, currentPrice: 2900, hasExactShares: true},
  {date: "2026-09-30", change: "unchanged", previousPrice: 2501, currentPrice: 2501, hasExactShares: true},
  {date: "2026-10-01", change: "revised", previousPrice: 3000, currentPrice: 3010, hasExactShares: false},
]);

const onlyOlderToyota = readQuoteHistory([
  "market_id,date,currency,close",
  "JP:7203,2026-03-31,JPY,2900",
  "JP:7203,2026-10-01,JPY,3010",
].join("\n"));
const [olderTrial] = reviewRepresentativeValuations(rows, shares, onlyOlderToyota).results;
assert.equal(olderTrial.date, "2026-09-30");
assert.equal(olderTrial.status, "missing_exact_close");
assert.equal(olderTrial.valuation, undefined);
assert.equal(olderTrial.latestAvailableTrial.date, "2026-03-31");
assert.equal(olderTrial.latestAvailableTrial.price, 2900);
assert.equal(olderTrial.latestAvailableTrial.valuation.cap, 2900 * 13033384474);
assert.ok(olderTrial.latestAvailableTrial.shareSource.startsWith("https://"));
assert.ok(olderTrial.latestAvailableTrial.financeSource.startsWith("https://"));
const [removedLatest] = reviewQuoteRefresh(rows, shares, updated, onlyOlderToyota).results;
assert.equal(removedLatest.closeChange, "removed");
assert.deepEqual(removedLatest.latestAvailableTrial, olderTrial.latestAvailableTrial);
assert.deepEqual(removedLatest.newerUnmatchedDates, ["2026-10-01"]);
const [restoredLatest] = reviewQuoteRefresh(rows, shares, onlyOlderToyota, updated).results;
assert.equal(restoredLatest.closeChange, "added");
assert.equal(restoredLatest.status, "trial_calculated");
assert.equal(restoredLatest.latestAvailableTrial, undefined);
assert.equal(refreshed[1].latestAvailableTrial, undefined);
console.log("Representative valuation checks passed for JP, US and SG.");
