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
    let statuses = [];
    server = https.createServer({key: fs.readFileSync(key), cert: fs.readFileSync(cert)}, (req, res) => {
      requests.push(req.url);
      res.writeHead(statuses.shift() ?? 200, {"content-type": "application/json"});
      res.end(JSON.stringify(body));
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });

    const feed = {
      schema_version: "value_hunter_web_v29", updated_at_utc: "2026-11-13T11:30:00Z",
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

    requests.length = 0;
    statuses = [503, 502];
    assert.deepEqual(JSON.parse((await run(process.execPath, args, options)).stdout), candidate);
    assert.deepEqual(requests, Array(3).fill("/closes?session=2026-11-13"));

    for (const [status, count] of [[503, 3], [403, 1], [429, 1]]) {
      requests.length = 0;
      statuses = Array(3).fill(status);
      await assert.rejects(run(process.execPath, args, options), error =>
        error.code === 1 && error.stdout === "" && error.stderr.includes("HTTP " + status));
      assert.equal(requests.length, count);
    }
    requests.length = 0;
    statuses = [];
    body = [{...quote, timestamp: "2026-11-12T09:00:00Z"}];
    await assert.rejects(run(process.execPath, args, options), error =>
      error.code === 1 && error.stdout === "" && error.stderr.includes("SGX close SESSION:"));
    assert.equal(requests.length, 1);
    assert.deepEqual(JSON.parse(fs.readFileSync(feedFile)), feed);
    const applyArgs = [path.join(__dirname, "../scripts/apply-sgx-public-quotes.sh"), feedFile];
    const applyOptions = {timeout: options.timeout, env: {
      ...options.env, SGX_REQUESTED_SESSION: "2026-11-13", SGX_PREFLIGHT: "true",
      SGX_CLOSE_GRANT_JSON: JSON.stringify(grant),
    }};
    body = [quote];
    statuses = [503, 503, 503];
    const original = fs.readFileSync(feedFile);
    await assert.rejects(run("bash", applyArgs, applyOptions), {code: 1, stderr: /HTTP 503/});
    assert.deepEqual(fs.readFileSync(feedFile), original);

    await run("bash", applyArgs, applyOptions);
    assert.deepEqual(JSON.parse(fs.readFileSync(feedFile)), candidate);
    assert.deepEqual(fs.readdirSync(temp).sort(), ["cert.pem", "feed.json", "grant.json", "key.pem"]);
    const historyDir = path.join(temp, "history");
    const historyArgs = [path.join(__dirname, "../SGX_PDF_connection_probe/value_hunter_history_v34.py"),
      "--source", feedFile, "--history-dir", historyDir];
    await run("python3", historyArgs);
    const indexFile = path.join(historyDir, "index.json");
    const publishedHistory = fs.readFileSync(indexFile);
    const [snapshot] = JSON.parse(publishedHistory).entries;
    assert.equal(snapshot.records[0].ranking_eligible, true);
    assert.equal(snapshot.records[0].pbr_verified, 1);

    delete candidate.records[0].market_data_license_evidence;
    fs.writeFileSync(feedFile, JSON.stringify(candidate));
    await assert.rejects(run("python3", historyArgs), {code: 1, stderr: /dated grant evidence missing/});
    assert.deepEqual(fs.readFileSync(indexFile), publishedHistory);
    console.log("SGX daily refresh and history passed: licensed recovery recorded; invalid grants rejected");
  } finally {
    if (server?.listening) await new Promise(resolve => server.close(resolve));
    fs.rmSync(temp, {recursive: true, force: true});
  }
}

test().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
