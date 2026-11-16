"use strict";

const fs = require("node:fs");
const {checkFeed, sgxQuoteDate} = require("../docs/sgx-ranking-validation.js");

// These exclusions describe the old close or calculations replaced below.
const REPLACED_QUOTE_FLAGS = new Set([
  "PRICE_MISSING", "QUOTE_OLD_OR_UNDATED", "QUOTE_NOT_AVAILABLE",
  "QUOTE_TIMESTAMP_MISSING", "QUOTE_STALE", "QUOTE_DATE_IN_FUTURE",
  "MARKET_CAP_ARITHMETIC_MISMATCH", "PER_ARITHMETIC_MISMATCH_OR_INVALID",
  "VERIFIED_PBR_LABEL_UNSUPPORTED",
]);

function stageQuotes(feed, quotes, grant) {
  const baselineErrors = checkFeed(feed);
  if (baselineErrors.length) throw new Error(baselineErrors.join("\n"));
  if (!Array.isArray(quotes) || !quotes.length) throw new Error("Expected at least one SGX quote");
  const staged = structuredClone(feed);
  const records = new Map(staged.records.map(row => [row.symbol, row]));
  const seen = new Set();
  for (const quote of quotes) {
    const symbol = quote?.symbol;
    const row = records.get(symbol);
    if (!row) throw new Error("Unknown SGX symbol in provider response");
    if (seen.has(symbol)) throw new Error("Repeated SGX symbol: " + symbol);
    seen.add(symbol);
    if (quote.currency !== "SGD" || quote.source_type !== "LICENSED_SGX_EQUITY" ||
        !Number.isFinite(quote.close) || quote.close <= 0 ||
        !Number.isFinite(quote.ranking_score)) {
      throw new Error(symbol + ": invalid licensed SGD close or ranking score");
    }
    const session = sgxQuoteDate(quote.timestamp);
    if (!session || row.shares_as_of_date !== session)
      throw new Error(symbol + ": close and shares need the same Singapore date");
    const existingSession = sgxQuoteDate(row.quote_timestamp_utc);
    if (existingSession && session < existingSession)
      throw new Error(symbol + ": incoming close predates the published close");
    if (row.ranking_eligible && session === existingSession && quote.close !== row.price_sgd)
      throw new Error(symbol + ": same-session close conflicts with the published close");
    if (!Array.isArray(row.exclusion_reasons) ||
        row.exclusion_reasons.some(reason => !REPLACED_QUOTE_FLAGS.has(reason) &&
          reason !== "VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE")) {
      throw new Error(symbol + ": existing financial or publication exclusions remain");
    }
    const qualityFlags = (row.quality_flags ?? []).filter(flag =>
      !REPLACED_QUOTE_FLAGS.has(flag) && flag !== "VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE");
    if (qualityFlags.length)
      throw new Error(symbol + ": existing data quality exclusions remain");
    const cap = quote.close * row.shares_outstanding;
    Object.assign(row, {
      price_sgd: quote.close,
      quote_timestamp_utc: quote.timestamp,
      quote_url: quote.source_url,
      quote_source_type: quote.source_type,
      quote_license_display_allowed: grant?.usage_scopes?.includes("BROWSER_DISPLAY") === true,
      quote_license_non_display_analytics_allowed:
        grant?.usage_scopes?.includes("BACKEND_NON_DISPLAY_ANALYTICS") === true,
      market_data_license_evidence: grant,
      quote_publicly_redistributed: true,
      market_cap_sgd: Number(cap.toFixed(2)),
      per_reference: Number((cap / (1000 * row.attributable_profit_sgd_thousands)).toFixed(4)),
      pbr_reference_unverified: null,
      pbr_verified: Number((cap / (1000 * row.parent_equity_sgd_thousands)).toFixed(4)),
      exclusion_reasons: [],
      quality_flags: qualityFlags,
      ranking_eligible: true,
      ranking_score: quote.ranking_score,
    });
  }
  staged.ranking_eligible_count = staged.records.filter(row => row.ranking_eligible === true).length;
  staged.ranking_enabled = staged.ranking_eligible_count > 0;
  const errors = checkFeed(staged);
  if (errors.length) throw new Error(errors.join("\n"));
  return staged;
}

if (require.main === module) {
  try {
    const files = process.argv.slice(2);
    if (files.length !== 3)
      throw new Error("Usage: node scripts/stage-sgx-public-quotes.js FEED.json QUOTES.json GRANT.json");
    const [feed, quotes, grant] = files.map(file => JSON.parse(fs.readFileSync(file, "utf8")));
    const result = stageQuotes(feed, quotes, grant);
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
module.exports = {stageQuotes};
