"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const https = require("node:https");
const os = require("node:os");
const path = require("node:path");
const {execFile, execFileSync} = require("node:child_process");
const {promisify} = require("node:util");
const run = promisify(execFile);

async function test() {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "sgx-close-https-"));
  let server;
  try {
    const key = path.join(temp, "key.pem");
    const cert = path.join(temp, "cert.pem");
    execFileSync("openssl", [
      "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
      "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
      "-keyout", key, "-out", cert,
    ], {stdio: "ignore"});

    const quote = {
      symbol: "S63", currency: "SGD", source_type: "LICENSED_SGX_EQUITY",
      close: 2, ranking_score: 1, source_url: "https://example.org/quote",
      timestamp: "2026-11-13T09:00:00Z",
    };
    const requests = [];
    let body = [quote];
    server = https.createServer({key: fs.readFileSync(key), cert: fs.readFileSync(cert)}, (req, res) => {
      requests.push(req.url);
      res.writeHead(200, {"content-type": "application/json"});
      res.end(JSON.stringify(body));
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });

    const feed = {
      ranking_enabled: false, ranking_eligible_count: 0, records: [{
        symbol: "S63", ranking_eligible: false, exclusion_reasons: [],
        shares_as_of_date: "2026-11-13", shares_outstanding: 1000,
        shares_count_basis: "issued_excluding_treasury",
        independent_cross_source_verification: true,
        attributable_profit_sgd_thousands: 1, parent_equity_sgd_thousands: 2,
      }],
    };
    const grant = {
      grant_status: "EXECUTED", grant_evidence_url: "https://example.org/license",
      licensor: "Test vendor", licensee: "Test app", licensed_product: "Test SGX closes",
      usage_scopes: ["BROWSER_DISPLAY", "BACKEND_NON_DISPLAY_ANALYTICS", "REDISTRIBUTION"],
      valid_from: "2026-01-01", valid_until: "2026-12-31",
      daily_close_feed_url: "https://127.0.0.1:" + server.address().port + "/closes",
    };
    const feedFile = path.join(temp, "feed.json");
    const grantFile = path.join(temp, "grant.json");
    fs.writeFileSync(feedFile, JSON.stringify(feed));
    fs.writeFileSync(grantFile, JSON.stringify(grant));
    const args = [path.join(__dirname, "../scripts/fetch-sgx-public-quotes.js"),
      feedFile, grantFile, "2026-11-13"];
    const options = {env: {...process.env, NODE_EXTRA_CA_CERTS: cert}, timeout: 20000};

    const {stdout} = await run(process.execPath, args, options);
    const candidate = JSON.parse(stdout);
    assert.deepEqual(requests, ["/closes?session=2026-11-13"]);
    assert.equal(candidate.ranking_eligible_count, 1);
    const [row] = candidate.records;
    assert.equal(row.market_cap_sgd, 2000);
    assert.equal(row.per_reference, 2);
    assert.equal(row.pbr_verified, 1);
    assert.equal(row.market_data_license_evidence.daily_close_feed_url, undefined);

    body = [{...quote, timestamp: "2026-11-12T09:00:00Z"}];
    await assert.rejects(run(process.execPath, args, options), error =>
      error.code === 1 && error.stdout === "" && error.stderr.includes("SGX close SESSION:"));
    assert.deepEqual(JSON.parse(fs.readFileSync(feedFile)), feed);
    console.log("SGX HTTPS CLI passed: requested session, ranking candidate, and stale response rejection");
  } finally {
    if (server?.listening) await new Promise(resolve => server.close(resolve));
    fs.rmSync(temp, {recursive: true, force: true});
  }
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
