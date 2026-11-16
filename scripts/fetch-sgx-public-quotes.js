"use strict";

const fs = require("node:fs");
const {stageQuotes} = require("./stage-sgx-public-quotes.js");
const {sgxQuoteDate, validDate} = require("../docs/sgx-ranking-validation.js");

const MAX_RESPONSE_BYTES = 1024 * 1024;

async function fetchAndStage(feed, grant, session, fetcher = fetch) {
  if (!validDate(session)) throw new Error("Expected a Singapore session date (YYYY-MM-DD)");
  if (grant?.grant_status !== "EXECUTED" ||
      !Array.isArray(grant.usage_scopes) ||
      !["BROWSER_DISPLAY", "BACKEND_NON_DISPLAY_ANALYTICS", "REDISTRIBUTION"]
        .every(scope => grant.usage_scopes.includes(scope)) ||
      !validDate(grant.valid_from) || !validDate(grant.valid_until) ||
      session < grant.valid_from || session > grant.valid_until) {
    throw new Error("An executed grant covering the session and all publication scopes is required");
  }
  const endpoint = new URL(grant.daily_close_feed_url);
  if (endpoint.protocol !== "https:" || endpoint.username || endpoint.password ||
      endpoint.search || endpoint.hash) {
    throw new Error("Expected an HTTPS feed URL without credentials, query or fragment");
  }
  endpoint.searchParams.set("session", session);
  const response = await fetcher(endpoint, {
    headers: {accept: "application/json"},
    redirect: "error",
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error("SGX daily close feed returned HTTP " + response.status);
  if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get("content-type") ?? "") ||
      !response.body) {
    throw new Error("Expected JSON from the SGX daily close feed");
  }
  const reader = response.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_RESPONSE_BYTES) throw new Error("SGX daily close feed exceeds 1 MiB");
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
  const quotes = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  if (!Array.isArray(quotes) || quotes.some(quote => sgxQuoteDate(quote?.timestamp) !== session)) {
    throw new Error("The feed must contain only closes for the requested Singapore session");
  }
  const {daily_close_feed_url, ...publicGrant} = grant;
  return stageQuotes(feed, quotes, publicGrant);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 3)
    throw new Error("Usage: node scripts/fetch-sgx-public-quotes.js FEED.json GRANT.json YYYY-MM-DD");
  const [feed, grant] = args.slice(0, 2).map(file => JSON.parse(fs.readFileSync(file, "utf8")));
  const staged = await fetchAndStage(feed, grant, args[2]);
  process.stdout.write(JSON.stringify(staged, null, 2) + "\n");
}

if (require.main === module) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = {fetchAndStage};
