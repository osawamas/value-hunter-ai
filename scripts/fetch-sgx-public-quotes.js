"use strict";

const fs = require("node:fs");
const {setTimeout: delay} = require("node:timers/promises");
const {stageQuotes} = require("./stage-sgx-public-quotes.js");
const {checkRefresh} = require("./check-ranking-license-evidence-v290.js");
const {sgxQuoteDate, validDate} = require("../docs/sgx-ranking-validation.js");

const MAX_RESPONSE_BYTES = 1024 * 1024;

class QuoteImportError extends Error {
  constructor(stage, message) {
    super(message);
    this.stage = stage;
  }
}

async function requestClose(endpoint, fetcher) {
  try {
    return await fetcher(endpoint, {
      headers: {accept: "application/json"},
      redirect: "error",
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new QuoteImportError("FETCH", "SGX daily close request failed or timed out");
  }
}

async function fetchAndStage(feed, grant, session, fetcher = fetch, reportTrial) {
  if (!validDate(session)) throw new QuoteImportError("SESSION", "Expected a Singapore session date (YYYY-MM-DD)");
  if (grant?.grant_status !== "EXECUTED" ||
      !Array.isArray(grant.usage_scopes) ||
      !["BROWSER_DISPLAY", "BACKEND_NON_DISPLAY_ANALYTICS", "REDISTRIBUTION"]
        .every(scope => grant.usage_scopes.includes(scope)) ||
      !validDate(grant.valid_from) || !validDate(grant.valid_until) ||
      session < grant.valid_from || session > grant.valid_until) {
    throw new QuoteImportError("GRANT", "An executed grant covering the session and all publication scopes is required");
  }
  const symbols = grant.daily_close_symbols;
  if (symbols !== undefined) {
    const registered = new Set(feed.records.map(row => row.symbol));
    if (!Array.isArray(symbols) || !symbols.length ||
        new Set(symbols).size !== symbols.length ||
        symbols.some(symbol => !registered.has(symbol))) {
      throw new QuoteImportError("CONFIG", "SGX close selection must contain unique registered symbols");
    }
  }
  let endpoint;
  try {
    endpoint = new URL(grant.daily_close_feed_url);
  } catch {
    throw new QuoteImportError("CONFIG", "Invalid SGX daily close feed URL");
  }
  if (endpoint.protocol !== "https:" || endpoint.username || endpoint.password ||
      endpoint.search || endpoint.hash) {
    throw new QuoteImportError("CONFIG", "Expected an HTTPS feed URL without credentials, query or fragment");
  }
  endpoint.searchParams.set("session", session);
  let response = await requestClose(endpoint, fetcher);
  for (const wait of [250, 500]) {
    if (![502, 503, 504].includes(response.status)) break;
    await response.body?.cancel().catch(() => {});
    await delay(wait);
    response = await requestClose(endpoint, fetcher);
  }
  if (!response.ok) {
    await response.body?.cancel().catch(() => {});
    throw new QuoteImportError("FETCH", "SGX daily close feed returned HTTP " + response.status);
  }
  if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "") ||
      !response.body) {
    throw new QuoteImportError("RESPONSE", "Expected JSON from the SGX daily close feed");
  }
  const reader = response.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_RESPONSE_BYTES) throw new QuoteImportError("RESPONSE", "SGX daily close feed exceeds 1 MiB");
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof QuoteImportError) throw error;
    throw new QuoteImportError("FETCH", "SGX daily close response was interrupted");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
  let quotes;
  try {
    quotes = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new QuoteImportError("RESPONSE", "Invalid JSON from the SGX daily close feed");
  }
  if (!Array.isArray(quotes)) {
    throw new QuoteImportError("RESPONSE", "Expected an array of SGX closing prices");
  }
  if (symbols !== undefined) {
    const selected = new Set(symbols);
    quotes = quotes.filter(quote => selected.has(quote?.symbol));
    const received = new Set(quotes.map(quote => quote.symbol));
    if (symbols.some(symbol => !received.has(symbol))) {
      throw new QuoteImportError("RESPONSE", "SGX response is missing a configured symbol");
    }
  }
  if (quotes.some(quote => sgxQuoteDate(quote?.timestamp) !== session)) {
    throw new QuoteImportError("SESSION", "The feed must contain only closes for the requested Singapore session");
  }
  if (reportTrial) {
    if (!quotes.length || quotes.some(quote => typeof quote.symbol !== "string" ||
        quote.currency !== "SGD" || quote.source_type !== "LICENSED_SGX_EQUITY" ||
        !Number.isFinite(quote.close) || quote.close <= 0) ||
        new Set(quotes.map(quote => quote.symbol)).size !== quotes.length) {
      throw new QuoteImportError("RESPONSE", "Expected unique licensed SGD closes for the requested session");
    }
    const s63 = quotes.find(quote => quote.symbol === "S63");
    if (s63) reportTrial(s63.close);
  }
  const {grant_status, grant_evidence_url, licensor, licensee, licensed_product,
    usage_scopes, valid_from, valid_until} = grant;
  const publicGrant = {grant_status, grant_evidence_url, licensor, licensee,
    licensed_product, usage_scopes, valid_from, valid_until};
  try {
    return stageQuotes(feed, quotes, publicGrant);
  } catch (error) {
    throw new QuoteImportError("VALIDATION", error.message);
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 3)
    throw new Error("Usage: node scripts/fetch-sgx-public-quotes.js FEED.json GRANT.json YYYY-MM-DD");
  let feed, grant;
  try {
    [feed, grant] = args.slice(0, 2).map(file => JSON.parse(fs.readFileSync(file, "utf8")));
  } catch {
    throw new QuoteImportError("CONFIG", "Could not read the public feed or grant configuration as JSON");
  }
  const reportTrial = process.env.SGX_PREFLIGHT === "true" ? close => {
    const {reviewStoredS63} = require("./check-sgx-close-readiness.js");
    const report = reviewStoredS63(feed, args[2], close);
    // Keep the preflight result out of both the candidate JSON and the workflow log prices.
    console.error("S63 valuation preflight: " + JSON.stringify({
      status: report.trial.status,
      calculated: Boolean(report.trial.valuation),
      completeRatios: Number.isFinite(report.trial.valuation?.per) &&
        Number.isFinite(report.trial.valuation?.pbr),
      interimStatus: report.interimTrial.status,
      interimPeriodEnd: report.interimTrial.periodEnd,
      blockers: report.blockers,
    }));
  } : undefined;
  if (reportTrial) {
    let validationErrors;
    try {
      const staged = await fetchAndStage(feed, grant, args[2], fetch, reportTrial);
      validationErrors = checkRefresh(feed, staged);
    } catch (error) {
      if (!(error instanceof QuoteImportError) || error.stage !== "VALIDATION") throw error;
      validationErrors = [error.message];
    }
    process.stdout.write(JSON.stringify({
      session: args[2],
      closeRetrieval: "retrieved",
      publicationCheck: validationErrors.length ? "blocked" : "passed",
      validationErrors,
    }, null, 2) + "\n");
    return;
  }

  const staged = await fetchAndStage(feed, grant, args[2]);
  process.stdout.write(JSON.stringify(staged, null, 2) + "\n");
}

if (require.main === module) {
  main().catch(error => {
    console.error("SGX close " + (error.stage || "IMPORT") + ": " + error.message);
    process.exitCode = 1;
  });
}

module.exports = {fetchAndStage};
