"use strict";

const fs = require("node:fs");
const {buildMarketRows, conflictingFilingShares, evaluatePersonalQuotes, publishedShareSessions} = require("../docs/market-research.js");
const {validDate} = require("../docs/sgx-ranking-validation.js");

const thirdPartyEvidence = new Map([
  ["S63", require("../docs/data/sgx-s63-third-party-financial-crosscheck-v448.json")],
  ["G13", require("../docs/data/sgx-g13-third-party-financial-crosscheck-v454.json")],
]);

function compareThirdPartyFinancials(row, evidence) {
  if (evidence.symbol !== row.symbol || evidence.unit !== "SGD_thousands" ||
      evidence.period_end !== row.fiscal_year + "-12-31") return null;
  const compare = (issuerValue, reference) => ({
    status: !Number.isSafeInteger(issuerValue) ? "issuer_value_missing" :
      Math.abs(issuerValue - reference.display_value) <= reference.display_increment / 2 ?
        "matches_display_precision" : "mismatch",
    issuerValue,
    displayValue: reference.display_value,
    displayIncrement: reference.display_increment,
    source: reference.source,
  });
  return {
    provider: evidence.provider,
    periodEnd: evidence.period_end,
    unit: evidence.unit,
    scope: evidence.scope,
    attributableProfit: compare(row.attributable_profit_sgd_thousands, evidence.attributable_profit),
    parentEquity: compare(row.parent_equity_sgd_thousands, evidence.parent_equity),
  };
}

function reviewIssuer(feed, research, notices, symbol, session, close) {
  if (!validDate(session)) throw new Error("Expected a Singapore trading date (YYYY-MM-DD)");
  const rows = buildMarketRows(research, feed).filter(row => row.id === "SG:" + symbol);
  const issuer = rows[0];
  if (!issuer?.sgxEvidence) throw new Error(symbol + " is absent from the SGX feed");
  const sessions = publishedShareSessions(rows, notices);
  const matched = sessions.get(session)?.[0];
  const conflicts = conflictingFilingShares(issuer, session, notices);
  const previous = [...sessions].find(([date]) => date < session);
  const previousShares = previous ? {date: previous[0], ...previous[1][0]} : null;
  const {shares_as_of_date: feedShareDate, shares_outstanding: feedShares,
    shares_count_basis: shareBasis, exclusion_reasons: exclusions,
    independent_cross_source_verification: independentFinancials} = issuer.sgxEvidence;
  const sameDateFeedShares = feedShareDate === session &&
    shareBasis === "issued_excluding_treasury" && Number.isSafeInteger(feedShares) && feedShares > 0;
  const blockers = [];
  if (conflicts) blockers.push("CONFLICTING_SHARE_FILINGS");
  else if (!matched) blockers.push("NO_MATCHING_SHARE_FILING");
  else if (!sameDateFeedShares || feedShares !== matched.value)
    blockers.push("MATCHED_SHARES_NOT_IN_IMPORT_FEED");
  if (independentFinancials !== true) blockers.push("FINANCIAL_INDEPENDENCE_UNVERIFIED");
  if (Array.isArray(exclusions) && exclusions.includes("PARENT_EQUITY_NOT_INDEPENDENTLY_VERIFIED"))
    blockers.push("PARENT_EQUITY_INDEPENDENCE_UNVERIFIED");

  const financialEvidence = thirdPartyEvidence.get(symbol);
  const trial = close === undefined ? null : evaluatePersonalQuotes(rows,
    new Map([[issuer.id, {date: session, currency: "SGD", price: close}]]),
    new Map(), notices)[0];
  return {
    symbol: issuer.symbol,
    session,
    matchedShares: matched ?? null,
    previousShares,
    conflictingShares: conflicts ?? null,
    availableShareDates: [...sessions.keys()],
    currentFeedShareDate: feedShareDate,
    currentFeedExclusions: exclusions,
    independentlyVerifiedFinancials: independentFinancials === true,
    blockers,
    ...(financialEvidence && {
      thirdPartyFinancialCrosscheck: compareThirdPartyFinancials(issuer.sgxEvidence, financialEvidence),
    }),
    ...(trial && {trial: {
      status: trial.state,
      ...(trial.result && {
        shares: trial.shares, shareSource: trial.shareSource,
        financeSource: trial.financeSource, valuation: trial.result,
      }),
    }}),
  };
}

function reviewS63(feed, research, notices, session, close) {
  const report = reviewIssuer(feed, research, notices, "S63", session, close);
  if (close === undefined) return report;

  const interim = require("../docs/data/sgx-s63-interim-v469.json");
  const annual = report.trial?.valuation;
  const {cap, periodEnd, annualNetIncome, annualParentEquity} = annual ?? {};
  const matchedAnnual = periodEnd === "2025-12-31" && annual?.currency === interim.currency &&
    annualParentEquity === interim.prior_year_end_parent_equity * 1000;
  const trailingProfit = annualNetIncome +
    (interim.attributable_profit_h1 - interim.attributable_profit_prior_h1) * 1000;
  const parentEquity = interim.parent_equity * 1000;
  // Require a later session when the evidence has a filing date but no verified release time.
  const status = !annual ? "annual_valuation_unavailable" :
    session <= interim.published_on ? "interim_not_yet_available" :
    !matchedAnnual ? "annual_comparative_mismatch" :
    trailingProfit <= 0 || parentEquity <= 0 ? "non_positive_denominator" : "calculated";
  return {...report, interimTrial: {
    status,
    periodEnd: interim.period_end,
    publishedOn: interim.published_on,
    source: interim.source_url,
    assurance: interim.assurance,
    ...(status === "calculated" && {
      trailingProfit, parentEquity, per: cap / trailingProfit, pbr: cap / parentEquity,
    }),
  }};
}

function reviewStoredS63(feed, session, close) {
  return reviewS63(feed, require("../docs/data/market-research-v315.json"), [
    require("../docs/data/sgx-s63-two-website-close-v129.json"),
    require("../docs/data/sgx-s63-historical-shares-v423.json"),
  ], session, close);
}

function reviewStoredG13(feed, session, close) {
  return reviewIssuer(feed, require("../docs/data/market-research-v315.json"),
    [require("../docs/data/sgx-g13-june10-shares-v122.json")], "G13", session, close);
}

if (require.main === module) {
  try {
    const [feedPath, session, symbol = "S63"] = process.argv.slice(2);
    if (!["S63", "G13"].includes(symbol)) throw new Error("Expected S63 or G13");
    const feed = JSON.parse(fs.readFileSync(feedPath, "utf8"));
    const report = symbol === "S63" ? reviewStoredS63(feed, session) :
      reviewStoredG13(feed, session);
    process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = {reviewIssuer, reviewS63, reviewStoredS63, reviewStoredG13};
