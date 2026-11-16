"use strict";

const assert = require("node:assert/strict");
const {execFileSync, spawnSync} = require("node:child_process");
const {createHash} = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {buildMarketRows, evaluatePersonalQuotes, personalBatchCsv, rankingEvidence, readQuoteHistory} = require("../docs/market-research.js");
const {reviewRepresentativeValuations, reviewQuoteRefresh} = require("../scripts/check-representative-valuations.js");
const research = require("../docs/data/market-research-v315.json");
const sgx = require("../docs/data/latest.json");
const shares = require("../docs/data/sgx-s63-two-website-close-v129.json");
const rows = buildMarketRows(research, sgx);
const equityReview = require("../docs/data/sgx-s63-parent-equity-v395.json");
const s63Issuer = rows.find(row => row.id === "SG:S63");
const {reviewIssuer, reviewS63, reviewStoredG13} = require("../scripts/check-sgx-close-readiness.js");
const g13 = reviewIssuer(sgx, research, [], "G13", "2026-06-30", 1);
assert.equal(g13.matchedShares.value, 12063642274);
assert.equal(g13.trial.valuation.cap, 12063642274);
assert.ok(g13.blockers.includes("FINANCIAL_INDEPENDENCE_UNVERIFIED"));
const juneBuyback = reviewStoredG13(sgx, "2026-06-10", 1);
assert.equal(juneBuyback.matchedShares.value, 12063642274);
assert.equal(juneBuyback.matchedShares.disclosedAt, "2026-06-10T17:55:09+08:00");
assert.equal(juneBuyback.trial.valuation.cap, 12063642274);
assert.ok(juneBuyback.blockers.includes("FINANCIAL_INDEPENDENCE_UNVERIFIED"));
assert.equal(reviewStoredG13(sgx, "2026-06-11", 1).matchedShares, null);
const g13November = reviewIssuer(sgx, research, [], "G13", "2026-11-13", 1);
assert.equal(g13November.matchedShares, null);
assert.equal(g13November.thirdPartyFinancialCrosscheck.attributableProfit.status, "matches_display_precision");
assert.equal(g13November.thirdPartyFinancialCrosscheck.parentEquity.status, "matches_display_precision");
assert.equal(g13November.thirdPartyFinancialCrosscheck.parentEquity.issuerValue, 8205416);
assert.ok(g13November.blockers.includes("FINANCIAL_INDEPENDENCE_UNVERIFIED"));
const g13DifferentPeriod = structuredClone(sgx);
g13DifferentPeriod.records.find(row => row.symbol === "G13").fiscal_year = 2026;
assert.equal(reviewIssuer(g13DifferentPeriod, research, [], "G13", "2026-11-13")
  .thirdPartyFinancialCrosscheck, null);
assert.equal(g13November.previousShares.date, "2026-06-30");
assert.equal(g13November.previousShares.value, 12063642274);
assert.match(g13November.previousShares.source, /^https:\/\//);
assert.ok(g13November.blockers.includes("NO_MATCHING_SHARE_FILING"));
assert.equal(g13November.trial.valuation, undefined);
const s63October = require("../docs/data/sgx-s63-historical-shares-v423.json");
const notices = [shares, s63October];
assert.equal(reviewS63(sgx, research, notices, "2026-10-26").matchedShares.value, 3116347115);
const s63Readiness = reviewS63(sgx, research, notices, "2026-11-13");
assert.equal(s63Readiness.matchedShares.value, 3115847115);
assert.ok(s63Readiness.blockers.includes("MATCHED_SHARES_NOT_IN_IMPORT_FEED"));
assert.equal(s63Readiness.matchedShares.disclosureTiming, "after_close");
const crosscheck = s63Readiness.thirdPartyFinancialCrosscheck;
assert.equal(crosscheck.attributableProfit.status, "matches_display_precision");
assert.equal(crosscheck.parentEquity.status, "matches_display_precision");
assert.equal(crosscheck.parentEquity.displayValue - crosscheck.parentEquity.issuerValue, 362);
const ftCrosscheck = s63Readiness.ftFinancialCrosscheck;
assert.equal(ftCrosscheck.provider, "LSEG via FT Markets");
assert.equal(ftCrosscheck.attributableProfit.status, "matches_display_precision");
assert.equal(ftCrosscheck.parentEquity.status, "matches_display_precision");
assert.equal(ftCrosscheck.parentEquity.displayIncrement, 1000);
assert.ok(ftCrosscheck.attributableProfit.definitionSource.endsWith("=IncomeStatement"));
const s63DifferentPeriod = structuredClone(sgx);
s63DifferentPeriod.records.find(row => row.symbol === "S63").fiscal_year = 2026;
assert.equal(reviewS63(s63DifferentPeriod, research, notices, "2026-11-13").ftFinancialCrosscheck, null);
const changedEquity = structuredClone(sgx);
changedEquity.records.find(row => row.symbol === "S63").parent_equity_sgd_thousands -= 1000;
const changedEquityReview = reviewS63(changedEquity, research, notices, "2026-11-13");
assert.equal(changedEquityReview.thirdPartyFinancialCrosscheck.parentEquity.status, "mismatch");
assert.equal(changedEquityReview.ftFinancialCrosscheck.parentEquity.status, "mismatch");

const readinessTrial = reviewS63(sgx, research, notices, "2026-11-13", 10);
assert.equal(readinessTrial.trial.status, "filing");
assert.equal(readinessTrial.trial.valuation.cap, 31158471150);
assert.ok(Number.isFinite(readinessTrial.trial.valuation.per));
assert.ok(Number.isFinite(readinessTrial.trial.valuation.pbr));
assert.deepEqual(readinessTrial.blockers, s63Readiness.blockers);
assert.equal(readinessTrial.interimTrial.status, "calculated");
assert.equal(readinessTrial.interimTrial.trailingProfit, 572067000);
assert.equal(readinessTrial.interimTrial.parentEquity, 2524548000);
assert.equal(readinessTrial.interimTrial.per, readinessTrial.trial.valuation.cap / 572067000);
assert.equal(readinessTrial.interimTrial.pbr, readinessTrial.trial.valuation.cap / 2524548000);
assert.equal(reviewS63(changedEquity, research, notices, "2026-11-13", 10)
  .interimTrial.status, "annual_comparative_mismatch");
assert.equal(reviewS63(sgx, research, notices, "2026-11-16", 10)
  .interimTrial.status, "annual_valuation_unavailable");
const beforeInterim = {...shares, session_date_sgt: "2026-08-13"};
assert.equal(reviewS63(sgx, research, [beforeInterim], "2026-08-13", 10)
  .interimTrial.status, "interim_not_yet_available");
assert.ok(s63Readiness.blockers.includes("FINANCIAL_INDEPENDENCE_UNVERIFIED"));
assert.ok(s63Readiness.blockers.includes("PARENT_EQUITY_INDEPENDENCE_UNVERIFIED"));
assert.equal(reviewS63(sgx, research, notices, "2026-11-16").matchedShares, null);
const conflictingNotices = [...notices, {...shares, original_sgx_shares_ex_treasury: 3115847116}];
assert.equal(reviewS63(sgx, research, conflictingNotices, "2026-11-13").matchedShares, null);
assert.ok(reviewS63(sgx, research, conflictingNotices, "2026-11-13").conflictingShares);
assert.ok(reviewS63(sgx, research, conflictingNotices, "2026-11-13").blockers.includes("CONFLICTING_SHARE_FILINGS"));
assert.ok(reviewS63(sgx, research, notices, "2026-11-16").blockers.includes("NO_MATCHING_SHARE_FILING"));
const laterS63 = {...shares, session_date_sgt: "2026-11-16",
  original_sgx_shares_ex_treasury: 3115347115,
  sgx_share_disclosed_at_sgt: "2026-11-16T18:21:18+08:00", sgx_session_end_at_sgt: undefined};
const laterQuote = new Map([["SG:S63", {date: "2026-11-16", currency: "SGD", price: 10}]]);
const [laterTrial] = evaluatePersonalQuotes(rows, laterQuote, new Map(), [shares, laterS63]);
assert.equal(laterTrial.result.cap, 31153471150);
assert.equal(laterTrial.shareDisclosureTiming, "time_unknown");
const [conflict] = evaluatePersonalQuotes(rows, laterQuote, new Map(),
  [shares, laterS63, {...laterS63, original_sgx_shares_ex_treasury: 3115347116}]);
assert.equal(conflict.state, "conflict");
assert.equal(conflict.result, undefined);
const s63Previous = readQuoteHistory("market_id,date,currency,close\nSG:S63,2026-11-13,SGD,10");
const s63Current = readQuoteHistory("market_id,date,currency,close\nSG:S63,2026-11-16,SGD,11");
const s63Refresh = reviewQuoteRefresh(rows, [shares, laterS63], s63Previous, s63Current).results[2];
assert.deepEqual(Object.values(s63Refresh.latestObservedTrials).map(trial => [
  trial.date, trial.shares, trial.valuation.cap, trial.shareSource,
]), [
  ["2026-11-13", 3115847115, 31158471150, shares.sgx_share_source_url],
  ["2026-11-16", 3115347115, 34268818265, laterS63.sgx_share_source_url],
]);
const competingNotice = {...laterS63, original_sgx_shares_ex_treasury: 3115347116,
  sgx_share_source_url: "https://links.sgx.com/fixture-corrected-notice"};
const conflictRefresh = reviewQuoteRefresh(rows, [shares, laterS63, competingNotice], s63Previous, s63Current).results[2];
const conflictTrial = conflictRefresh.latestObservedTrials.current;
assert.equal(conflictTrial.status, "conflict");
assert.deepEqual(conflictTrial.shareConflicts, [
  {value: 3115347115, source: laterS63.sgx_share_source_url},
  {value: 3115347116, source: competingNotice.sgx_share_source_url},
]);
assert.equal(conflictTrial.valuation, undefined);
assert.deepEqual(conflictRefresh.sessionChanges.at(-1).valuationImpact.current, conflictTrial);
const priorConflict = reviewQuoteRefresh(
  rows, [shares, laterS63], s63Current, s63Current, rows, [laterS63, competingNotice]
).results[2];
assert.equal(priorConflict.latestObservedTrials.previous.status, "conflict");
assert.equal(priorConflict.latestObservedTrials.current.status, "trial_calculated");
const correctedShares = reviewQuoteRefresh(
  rows, [laterS63], s63Current, s63Current, rows, [competingNotice]
).results[2].sessionChanges[0];
assert.equal(correctedShares.change, "unchanged");
assert.equal(correctedShares.valuationEvidenceChanged, true);
assert.equal(correctedShares.valuationImpact.previous.valuation.cap, 3115347116 * 11);
assert.equal(correctedShares.valuationImpact.current.valuation.cap, 3115347115 * 11);
const unchangedEvidence = reviewQuoteRefresh(
  rows, [laterS63], s63Current, s63Current, rows, [{...laterS63}]
).results[2].sessionChanges[0];
assert.equal(unchangedEvidence.valuationImpact, undefined);
const correctedFinanceRows = structuredClone(rows);
correctedFinanceRows.find(row => row.id === "SG:S63").sgxEvidence.attributable_profit_sgd_thousands++;
const correctedFinance = reviewQuoteRefresh(
  correctedFinanceRows, [laterS63], s63Current, s63Current, rows, [laterS63]
).results[2].sessionChanges[0];
assert.equal(correctedFinance.valuationEvidenceChanged, true);
assert.equal(correctedFinance.valuationImpact.previous.shares, correctedFinance.valuationImpact.current.shares);
assert.notEqual(correctedFinance.valuationImpact.previous.valuation.per,
  correctedFinance.valuationImpact.current.valuation.per);
assert.equal(reviewQuoteRefresh(rows, shares, s63Previous, s63Current)
  .results[2].latestObservedTrials.current.status, "no_exact_share_evidence");
const toyota = structuredClone(rows.find(row => row.id === "JP:7203"));
const latestToyota = toyota.financials.periods.at(-1);
latestToyota.net_income = -1;
latestToyota.parent_equity = 0;
const [undefinedRatios] = evaluatePersonalQuotes([toyota],
  new Map([["JP:7203", {date: "2026-09-30", currency: "JPY", price: 2500}]]), new Map(), shares);
assert.equal(undefinedRatios.result.cap, 2500 * 11778247313);
const juneToyota = reviewRepresentativeValuations(rows, shares,
  readQuoteHistory("market_id,date,currency,close\nJP:7203,2026-06-30,JPY,2900")).results[0].latestAvailableTrial;
assert.equal(juneToyota.shares, 11841833660);
assert.equal(juneToyota.valuation.cap, 2900 * 11841833660);
assert.match(juneToyota.shareSource, /2027_1q_summary_en\.pdf$/);
assert.equal(juneToyota.shareDisclosureDate, "2026-08-04");
assert.equal(undefinedRatios.result.per, null);
assert.equal(undefinedRatios.result.pbr, null);
assert.match(personalBatchCsv([undefinedRatios]), /-1,0,"non_positive_net_income","non_positive_parent_equity",{8}\r\n/);
assert.equal(rankingEvidence(s63Issuer, shares, equityReview).matchedEquity.parent_equity, 2573638);
for (const mismatch of [{period_end: "2024-12-31"}, {parent_equity: 2921245},
  {non_controlling_interests: 0}, {independent_verification: true}]) {
  assert.equal(rankingEvidence(s63Issuer, shares, {...equityReview, ...mismatch}).matchedEquity, null);
}
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
assert.deepEqual(calculated.results.map(({valuation}) =>
  [valuation.annualNetIncome, valuation.annualParentEquity]), [
  [3848098000000, 39918854000000], [10593000000, 32648000000], [462770000, 2573638000],
]);
for (const {valuation} of calculated.results) {
  assert.equal(valuation.per, valuation.cap / valuation.annualNetIncome);
  assert.equal(valuation.pbr, valuation.cap / valuation.annualParentEquity);
}
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
assert.deepEqual(refreshed[1].quoteCoverage, {
  previous: {first: "2026-09-30", last: "2026-09-30", count: 1},
  current: {first: "2026-10-01", last: "2026-10-01", count: 1},
});
assert.equal(refreshed[1].sharedDateRange, null);
assert.deepEqual(refreshed[1].datesMissingFromCurrentWithinRange, []);
assert.equal(refreshed[2].status, "trial_calculated");
assert.deepEqual(reviewQuoteRefresh(rows, shares, current, current).results.map(row => row.closeChange),
  ["unchanged", "absent", "unchanged"]);
const sessionPrices = result => result.sessionChanges.map(({valuationImpact, ...session}) => session);
assert.deepEqual(sessionPrices(refreshed[0]), [
  {date: "2026-09-30", change: "revised", previousPrice: 2500, currentPrice: 2501, hasExactShares: true},
  {date: "2026-10-01", change: "unchanged", previousPrice: 3000, currentPrice: 3000, hasExactShares: false},
]);
assert.deepEqual(sessionPrices(refreshed[2]), [
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
assert.deepEqual(sessionPrices(subsequent), [
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

const toyotaRevision = refreshed[0].sessionChanges[0].valuationImpact;
assert.deepEqual([toyotaRevision.previous.valuation.cap, toyotaRevision.current.valuation.cap],
  [2500 * 11778247313, 2501 * 11778247313]);
assert.ok(toyotaRevision.current.valuation.per > toyotaRevision.previous.valuation.per);
assert.ok(toyotaRevision.current.valuation.pbr > toyotaRevision.previous.valuation.pbr);
assert.equal(toyotaRevision.current.shareSource, toyotaRevision.previous.shareSource);
assert.equal(refreshed[1].sessionChanges[0].valuationImpact.current, null);
assert.equal(refreshed[1].sessionChanges[0].valuationImpact.previous.valuation.cap, 200 * 945120805);
assert.equal(refreshed[2].sessionChanges[1].valuationImpact.previous, null);
assert.equal(refreshed[2].sessionChanges[1].valuationImpact.current.shareDisclosureTiming, "after_close");
assert.equal(subsequent.sessionChanges[0].valuationImpact.current.date, "2026-03-31");
assert.equal(subsequent.sessionChanges[1].valuationImpact, undefined);
assert.equal(subsequent.sessionChanges[2].valuationImpact, undefined);
const correctedOlderToyota = readQuoteHistory([
  "market_id,date,currency,close",
  "JP:7203,2026-03-31,JPY,3000",
  "JP:7203,2026-09-30,JPY,2501",
].join("\n"));
const [olderRevision] = reviewQuoteRefresh(rows, shares, updated, correctedOlderToyota).results;
assert.equal(olderRevision.closeChange, "unchanged");
assert.equal(olderRevision.valuation.cap, 2501 * 11778247313);
const olderImpact = olderRevision.sessionChanges[0].valuationImpact;
assert.equal(olderImpact.previous.valuation.cap, 2900 * 13033384474);
assert.equal(olderImpact.current.valuation.cap, 3000 * 13033384474);
assert.equal(olderRevision.quoteCoverage.current.count, 2);
assert.equal(reviewQuoteRefresh(rows, shares, updated, correctedOlderToyota).results[1].quoteCoverage.current, null);
const overlapping = new Map(quotes);
overlapping.set("JP:7203:2026-03-31", onlyOlderToyota.get("JP:7203:2026-03-31"));
const [overlap] = reviewQuoteRefresh(rows, shares, overlapping, onlyOlderToyota).results;
assert.deepEqual(overlap.sharedDateRange, {first: "2026-03-31", last: "2026-10-01"});
assert.deepEqual(overlap.datesMissingFromCurrentWithinRange, ["2026-09-30"]);
assert.deepEqual(olderRevision.sharedDateRange, {first: "2026-03-31", last: "2026-09-30"});
assert.deepEqual(olderRevision.datesMissingFromCurrentWithinRange, []);
assert.deepEqual(olderRevision.newTradingDates, []);
assert.deepEqual(subsequent.newTradingDates, []);
assert.deepEqual(refreshed[1].newTradingDates, ["2026-10-01"]);
assert.deepEqual(refreshed[2].newTradingDates, ["2026-11-13"]);
const noPreviousSgx = reviewQuoteRefresh(rows, shares, onlyOlderToyota, current).results[2];
assert.equal(noPreviousSgx.quoteCoverage.previous, null);
assert.deepEqual(noPreviousSgx.newTradingDates, []);
const work = fs.mkdtempSync(path.join(os.tmpdir(), "value-hunter-replay-"));
try {
  const previous = path.join(work, "previous.csv");
  const current = path.join(work, "current.csv");
  const csv = [
    "market_id,date,currency,close",
    "JP:7203,2026-09-30,JPY,2500",
    "US:IBM,2026-09-30,USD,200",
    "SG:S63,2026-11-13,SGD,10",
  ].join("\n");
  fs.writeFileSync(previous, csv);
  fs.writeFileSync(current, csv.replace(",USD,200", ",USD,201") + "\nSG:S63,2026-11-16,SGD,11");
  const cli = path.join(__dirname, "../scripts/check-representative-valuations.js");
  const report = JSON.parse(execFileSync(process.execPath, [cli, "--compare", previous, current], {encoding: "utf8"}));
  const hash = name => createHash("sha256").update(fs.readFileSync(name)).digest("hex");
  const evidence = ["market-research-v315.json", "latest.json", "sgx-s63-two-website-close-v129.json",
    "sgx-s63-historical-shares-v423.json", "sgx-s63-shares-2026-11-16-v479.json"];
  assert.deepEqual(report.filingDataSha256, Object.fromEntries(evidence.map(name =>
    [name, hash(path.join(__dirname, "../docs/data", name))])));
  assert.equal(report.snapshots.previous.sha256, hash(previous));
  assert.equal(report.snapshots.current.sha256, hash(current));
  assert.deepEqual(report.results.map(row => row.status), Array(3).fill("trial_calculated"));
  assert.equal(report.results[1].valuation.cap, 201 * 945120805);
  assert.deepEqual(report.results[2].newTradingDates, ["2026-11-16"]);
  assert.deepEqual(report.results[2].newerUnmatchedDates, []);
  assert.equal(report.results[2].latestObservedTrials.current.shares, 3115347115);
  const october = path.join(work, "october.csv");
  fs.writeFileSync(october, "market_id,date,currency,close\nSG:S63,2026-10-26,SGD,10");
  const historical = JSON.parse(execFileSync(process.execPath, [cli, "--compare", october, previous], {encoding: "utf8"}));
  const trials = historical.results.find(row => row.id === "SG:S63").latestObservedTrials;
  assert.deepEqual([trials.previous.date, trials.previous.shares, trials.previous.valuation.cap],
    ["2026-10-26", 3116347115, 31163471150]);
  assert.equal(trials.current.shares, 3115847115);
  const strict = (...args) => {
    const result = spawnSync(process.execPath, [cli, "--require-latest-trials", ...args], {encoding: "utf8"});
    assert.equal(result.stderr, "");
    return [result.status, JSON.parse(result.stdout)];
  };
  const [pass, matched] = strict(previous);
  assert.equal(pass, 0);
  assert.equal(matched.latestTrialCheck.passed, true);
  assert.ok(matched.latestTrialCheck.results.every(row =>
    row.valuation.cap === row.price * row.shares && row.shareSource && row.financeSource));
  const unmatched = path.join(work, "unmatched.csv");
  fs.writeFileSync(unmatched, fs.readFileSync(current, "utf8").replace("2026-11-16,SGD", "2026-11-17,SGD"));
  const [fail, missingShares] = strict("--compare", previous, unmatched);
  assert.equal(fail, 2);
  assert.equal(missingShares.latestTrialCheck.passed, false);
  assert.deepEqual(missingShares.latestTrialCheck.results.map(row => [row.id, row.status]), [
    ["JP:7203", "trial_calculated"], ["US:IBM", "trial_calculated"], ["SG:S63", "missing"],
  ]);
  assert.equal(missingShares.latestTrialCheck.results[2].date, "2026-11-17");
  const [noQuotes, empty] = strict();
  assert.equal(noQuotes, 2);
  assert.ok(empty.latestTrialCheck.results.every(row => row.status === "missing_close"));
  const requiresNew = (baseline, newest) => {
    const result = spawnSync(process.execPath, [cli, "--require-new-sessions", "--compare", baseline, newest], {encoding: "utf8"});
    assert.equal(result.stderr, "");
    return [result.status, JSON.parse(result.stdout).latestTrialCheck];
  };
  const [sameExit, sameSessions] = requiresNew(previous, previous);
  assert.equal(sameExit, 2);
  assert.ok(sameSessions.results.every(row => row.status === "trial_calculated" && !row.hasNewSession));
  const [laterExit, laterSessions] = requiresNew(previous, unmatched);
  assert.equal(laterExit, 2);
  assert.equal(laterSessions.results[1].hasNewSession, false, "a correction is not a new session");
  assert.equal(laterSessions.results[2].previousDate, "2026-11-13");
  assert.equal(laterSessions.results[2].hasNewSession, true);
  assert.equal(laterSessions.results[2].status, "missing");
  fs.writeFileSync(current, csv.replace("SG:S63,2026-11-13,SGD,10", "SG:S63,2026-11-12,SGD,10"));
  const [advancedExit, advanced] = requiresNew(current, previous);
  assert.equal(advancedExit, 2, "advancing only one of the three markets is insufficient");
  assert.equal(advanced.results[2].hasNewSession, true);
  assert.equal(advanced.results[2].status, "trial_calculated");
  fs.writeFileSync(current, csv.replaceAll("2026-09-30", "2026-09-29").replace("2026-11-13", "2026-11-12"));
  const [allAdvancedExit, allAdvanced] = requiresNew(current, previous);
  assert.equal(allAdvancedExit, 0);
  assert.equal(allAdvanced.passed, true);
  const bothTrials = (...options) => {
    const result = spawnSync(process.execPath, [cli, ...options, "--require-both-trials", "--compare", current, previous], {encoding: "utf8"});
    assert.equal(result.stderr, "");
    return [result.status, JSON.parse(result.stdout).latestTrialCheck];
  };
  const [baselineFailed, baselineCheck] = bothTrials();
  assert.equal(baselineFailed, 2);
  assert.ok(baselineCheck.results.every(row => row.status === "trial_calculated" &&
    row.hasNewSession && row.previousStatus === "no_exact_share_evidence"));
  const custom = path.join(work, "filings");
  fs.mkdirSync(custom);
  fs.writeFileSync(path.join(custom, "sgx-s63-two-website-close-v129.json"), JSON.stringify([
    shares, {...shares, session_date_sgt: "2026-11-12"},
  ]));
  const earlierFinance = structuredClone(research);
  for (const row of earlierFinance.records.filter(row => ["JP:7203", "US:IBM"].includes(row.id))) {
    row.financials.shares = {as_of: "2026-09-29", value: row.quarterly.shares.value};
  }
  fs.writeFileSync(path.join(custom, "market-research-v315.json"), JSON.stringify(earlierFinance));
  fs.writeFileSync(path.join(custom, "latest.json"), JSON.stringify(sgx));
  const [bothExit, bothCheck] = bothTrials("--filing-dir", custom);
  assert.equal(bothExit, 0);
  assert.ok(bothCheck.results.every(row => row.previousStatus === "trial_calculated"));
  const [separateExit, separateCheck] = bothTrials("--previous-filing-dir", custom);
  assert.equal(separateExit, 0, "each side can use its own dated share evidence");
  assert.ok(separateCheck.results.every(row => row.previousStatus === "trial_calculated"));
  const [wrongBaseline, wrongCheck] = bothTrials("--filing-dir", custom,
    "--previous-filing-dir", path.join(__dirname, "../docs/data"));
  assert.equal(wrongBaseline, 2, "current filings must not backfill an explicit previous snapshot");
  assert.ok(wrongCheck.results.every(row => row.previousStatus === "no_exact_share_evidence"));

  const jpUsPrevious = path.join(work, "jp-us-previous.csv");
  const jpUsCurrent = path.join(work, "jp-us-current.csv");
  fs.writeFileSync(jpUsPrevious, [
    "market_id,date,currency,close",
    "JP:7203,2026-06-30,JPY,2900",
    "US:IBM,2026-06-30,USD,200",
  ].join("\n"));
  fs.writeFileSync(jpUsCurrent, csv.split("\n").slice(0, 3).join("\n"));
  const checkJpUs = () => {
    const result = spawnSync(process.execPath,
      [cli, "--require-jp-us-refresh", "--compare", jpUsPrevious, jpUsCurrent], {encoding: "utf8"});
    assert.equal(result.stderr, "");
    return [result.status, JSON.parse(result.stdout).latestTrialCheck];
  };
  const [jpUsExit, jpUsCheck] = checkJpUs();
  assert.equal(jpUsExit, 0);
  assert.equal(jpUsCheck.scope, "local_trial_jp_us");
  assert.deepEqual(jpUsCheck.results.map(row => row.id), ["JP:7203", "US:IBM"]);
  assert.ok(jpUsCheck.results.every(row => row.hasNewSession && row.previousStatus === "trial_calculated"));
  fs.writeFileSync(jpUsCurrent, fs.readFileSync(jpUsCurrent, "utf8").replace("2026-09-30,USD", "2026-11-13,USD"));
  const [jpUsMissingExit, jpUsMissingCheck] = checkJpUs();
  assert.equal(jpUsMissingExit, 2);
  assert.equal(jpUsMissingCheck.results[1].hasNewSession, true);
  assert.equal(jpUsMissingCheck.results[1].status, "missing");
  assert.equal(jpUsMissingCheck.results[1].referenceShareDate, "2026-09-30");
  assert.match(jpUsMissingCheck.results[1].referenceShareSource, /^https:\/\/www\.sec\.gov\//);
  assert.equal(jpUsMissingCheck.results[1].valuation, undefined);
  fs.writeFileSync(jpUsPrevious, fs.readFileSync(jpUsPrevious, "utf8").replace("2026-06-30,USD", "2026-07-01,USD"));
  fs.writeFileSync(jpUsCurrent, csv.split("\n").slice(0, 3).join("\n"));
  const [jpUsMissingBaselineExit, jpUsMissingBaseline] = checkJpUs();
  assert.equal(jpUsMissingBaselineExit, 2);
  assert.equal(jpUsMissingBaseline.results[1].status, "trial_calculated");
  assert.equal(jpUsMissingBaseline.results[1].previousStatus, "no_exact_share_evidence");
  assert.equal(jpUsMissingBaseline.results[1].previousReferenceShareDate, "2026-06-30");
  assert.match(jpUsMissingBaseline.results[1].previousReferenceShareSource, /^https:\/\/www\.sec\.gov\//);
} finally {
  fs.rmSync(work, {recursive: true, force: true});
}
console.log("Representative valuation checks passed for JP, US and SG.");
