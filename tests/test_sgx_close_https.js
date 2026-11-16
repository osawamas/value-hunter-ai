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
      close: 2, source_url: "https://example.org/quote",
      timestamp: "2026-11-12T09:00:00Z",
    };
    const requests = [];
    const authorizations = [];
    let redirectTo;
    let body = [quote, {...quote, symbol: "OTHER", timestamp: "2026-11-11T09:00:00Z"}];
    let statuses = [];
    const sessionBodies = new Map();
    server = https.createServer({key: fs.readFileSync(key), cert: fs.readFileSync(cert)}, (req, res) => {
      requests.push(req.url);
      authorizations.push(req.headers.authorization);
      if (redirectTo) {
        res.writeHead(302, {location: redirectTo});
        res.end();
        return;
      }
      res.writeHead(statuses.shift() ?? 200, {"content-type": "application/json"});
      res.end(JSON.stringify(sessionBodies.get(req.url) ?? body));
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });

    const feed = {
      schema_version: "value_hunter_web_v29", updated_at_utc: "2026-11-12T11:30:00Z",
      quality_counts: {quote_stale: 1, quote_missing: 0, ranking_eligible: 0},
      ranking_enabled: false, ranking_eligible_count: 0, records: [{
        symbol: "S63", ranking_eligible: false,
        exclusion_reasons: ["QUOTE_STALE", "VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE"],
        quality_flags: ["QUOTE_STALE", "VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE"],
        quote_freshness: "STALE", pbr_reference_unverified: 4,
        shares_as_of_date: "2026-11-12", shares_outstanding: 1000,
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
      daily_close_symbols: ["S63"],
      daily_close_feed_url: "https://127.0.0.1:" + server.address().port + "/closes",
    };
    const feedFile = path.join(temp, "feed.json");
    const grantFile = path.join(temp, "grant.json");
    fs.writeFileSync(feedFile, JSON.stringify(feed));
    fs.writeFileSync(grantFile, JSON.stringify(grant));
    const args = [path.join(__dirname, "../scripts/fetch-sgx-public-quotes.js"),
      feedFile, grantFile, "2026-11-12"];
    const options = {env: {...process.env, NODE_EXTRA_CA_CERTS: cert}, timeout: 20000};

    for (const invalid of [
      {licensor: " "}, {licensee: null}, {licensed_product: ""}, {grant_evidence_url: "http://example.org/license"},
    ]) {
      fs.writeFileSync(grantFile, JSON.stringify({...grant, ...invalid}));
      await assert.rejects(run(process.execPath, args, options),
        {code: 1, stdout: "", stderr: /SGX close GRANT:/});
    }
    assert.deepEqual(requests, []);
    fs.writeFileSync(grantFile, JSON.stringify(grant));
    const {stdout} = await run(process.execPath, args, options);
    const candidate = JSON.parse(stdout);
    assert.deepEqual(requests, ["/closes?session=2026-11-12"]);
    assert.equal(candidate.ranking_eligible_count, 1);
    const [row] = candidate.records;
    assert.equal(row.market_cap_sgd, 2000);
    assert.equal(row.per_reference, 2);
    assert.equal(row.pbr_verified, 1);
    assert.equal(row.ranking_score, 75);
    assert.equal(row.quote_freshness, "RECENT");
    assert.equal(candidate.quality_counts.quote_stale, 0);
    assert.equal(candidate.quality_counts.ranking_eligible, 1);
    assert.equal(row.pbr_reference_unverified, null);
    assert.deepEqual(row.exclusion_reasons, []);
    assert.deepEqual(row.quality_flags, []);
    assert.equal(row.market_data_license_evidence.daily_close_feed_url, undefined);
    assert.equal(row.market_data_license_evidence.daily_close_symbols, undefined);
    const authToken = "fixture-private-token_123";
    const authenticatedGrant = {...grant, daily_close_bearer_token: authToken};
    fs.writeFileSync(grantFile, JSON.stringify(authenticatedGrant));
    const authorized = await run(process.execPath, args, options);
    assert.equal(authorizations.at(-1), "Bearer " + authToken);
    assert.deepEqual(JSON.parse(authorized.stdout), candidate);
    assert.ok(!authorized.stdout.includes(authToken));

    const firstRequestCount = requests.length;
    redirectTo = "/redirect-target";
    await assert.rejects(run(process.execPath, args, options), error => {
      assert.equal(error.code, 1);
      assert.match(error.stderr, /failed or timed out/);
      assert.ok(!error.stderr.includes(authToken));
      return true;
    });
    assert.deepEqual(requests.slice(firstRequestCount), ["/closes?session=2026-11-12"]);
    redirectTo = undefined;

    const beforeInvalid = requests.length;
    fs.writeFileSync(grantFile, JSON.stringify({...grant, daily_close_bearer_token: "bad token"}));
    await assert.rejects(run(process.execPath, args, options), {
      code: 1, stdout: "", stderr: /Invalid SGX bearer token format/,
    });
    assert.equal(requests.length, beforeInvalid);
    fs.writeFileSync(grantFile, JSON.stringify(grant));

    const completeResponse = body;
    body = [{...quote, symbol: "OTHER"}];
    await assert.rejects(run(process.execPath, args, options), {
      code: 1, stderr: /missing a configured symbol/,
    });
    body = [quote, quote];
    await assert.rejects(run(process.execPath, args, options), {code: 1, stderr: /Repeated SGX symbol/});
    body = completeResponse;

    requests.length = 0;
    statuses = [503, 502];
    assert.deepEqual(JSON.parse((await run(process.execPath, args, options)).stdout), candidate);
    assert.deepEqual(requests, Array(3).fill("/closes?session=2026-11-12"));

    for (const [status, count] of [[503, 3], [403, 1], [429, 1]]) {
      requests.length = 0;
      statuses = Array(3).fill(status);
      await assert.rejects(run(process.execPath, args, options), error =>
        error.code === 1 && error.stdout === "" && error.stderr.includes("HTTP " + status));
      assert.equal(requests.length, count);
    }
    requests.length = 0;
    statuses = [];
    body = [{...quote, timestamp: "2026-11-11T09:00:00Z"}];
    await assert.rejects(run(process.execPath, args, options), error =>
      error.code === 1 && error.stdout === "" && error.stderr.includes("SGX close SESSION:"));
    assert.equal(requests.length, 1);
    assert.deepEqual(JSON.parse(fs.readFileSync(feedFile)), feed);
    const applyArgs = [path.join(__dirname, "../scripts/apply-sgx-public-quotes.sh"), feedFile];
    const applyOptions = {timeout: options.timeout, env: {
      ...options.env, SGX_REQUESTED_SESSION: "2026-11-12", SGX_PREFLIGHT: "false",
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
    assert.equal(snapshot.records[0].quote_freshness, "RECENT");

    // Replay a licensed close against a lagging feed and the bundled SGXNet share notice.
    const matchedSession = "2026-11-13";
    const noticeQuote = {...quote, timestamp: matchedSession + "T09:00:00Z"};
    const noticeArgs = [...args.slice(0, -1), matchedSession];
    body = [noticeQuote];
    const lagging = {...structuredClone(feed), currency: "SGD", financial_unit: "SGD_thousands"};
    lagging.updated_at_utc = matchedSession + "T11:30:00Z";
    const originalS63 = require("../docs/data/latest.json").records.find(row => row.symbol === "S63");
    Object.assign(lagging.records[0], {
      financial_source_url: originalS63.financial_source_url,
      fiscal_year: originalS63.fiscal_year,
      revenue_sgd_thousands: originalS63.revenue_sgd_thousands,
      shares_as_of_date: "2026-03-31", share_freshness: "STALE", shares_outstanding: 999,
      shares_source_url: "https://example.org/earlier-filing",
      exclusion_reasons: ["QUOTE_STALE", "SHARES_STALE"],
      quality_flags: ["QUOTE_STALE", "SHARES_STALE"],
    });
    fs.writeFileSync(feedFile, JSON.stringify(lagging));
    const reconciled = JSON.parse((await run(process.execPath, noticeArgs, options)).stdout);
    const [s63] = reconciled.records;
    assert.equal(s63.shares_outstanding, 3115847115);
    assert.equal(s63.shares_as_of_date, "2026-11-13");
    assert.match(s63.shares_source_url, /links\.sgx\.com/);
    assert.equal(s63.shares_disclosure_timing, "after_close");
    assert.equal(s63.market_cap_sgd, quote.close * s63.shares_outstanding);
    assert.equal(reconciled.quality_counts.shares_stale, 0);
    assert.equal(s63.ranking_eligible, true);
    assert.deepEqual(JSON.parse(fs.readFileSync(feedFile)), lagging);

    lagging.records[0].exclusion_reasons.push("PARENT_EQUITY_NOT_INDEPENDENTLY_VERIFIED");
    fs.writeFileSync(feedFile, JSON.stringify(lagging));
    await assert.rejects(run(process.execPath, noticeArgs, options), {
      code: 1, stderr: /existing financial or publication exclusions remain/,
    });

    lagging.records[0].shares_as_of_date = matchedSession;
    fs.writeFileSync(feedFile, JSON.stringify(lagging));
    await assert.rejects(run(process.execPath, noticeArgs, options), {
      code: 1, stderr: /conflicting same-session share counts/,
    });

    body = [{...quote, timestamp: "2026-11-17T09:00:00Z"}];
    lagging.updated_at_utc = "2026-11-17T11:30:00Z";
    fs.writeFileSync(feedFile, JSON.stringify(lagging));
    await assert.rejects(run(process.execPath, [...args.slice(0, -1), "2026-11-17"], options), {
      code: 1, stderr: /close and shares need the same Singapore date/,
    });
    body = [quote];

    delete candidate.records[0].market_data_license_evidence;
    fs.writeFileSync(feedFile, JSON.stringify(candidate));
    await assert.rejects(run("python3", historyArgs), {code: 1, stderr: /dated grant evidence missing/});
    assert.deepEqual(fs.readFileSync(indexFile), publishedHistory);
    const realFeed = fs.readFileSync(path.join(__dirname, "../docs/data/latest.json"));
    fs.writeFileSync(feedFile, realFeed);
    const evidenceOnlyOptions = {env: {...applyOptions.env, SGX_PREFLIGHT: "true", SGX_CLOSE_GRANT_JSON: "", SGX_REQUESTED_SESSION: matchedSession}};
    const requestCount = requests.length;
    const evidenceOnly = await run("bash", applyArgs, evidenceOnlyOptions);
    assert.match(evidenceOnly.stdout, /3115847115/);
    assert.match(evidenceOnly.stdout, /"symbol": "G13"/);
    assert.match(evidenceOnly.stdout, /Evidence-only SGX preflight/);
    assert.equal(requests.length, requestCount);
    assert.deepEqual(fs.readFileSync(feedFile), realFeed);
    await assert.rejects(run("bash", applyArgs, {
      env: {...evidenceOnlyOptions.env, SGX_PREFLIGHT: "false"},
    }), {code: 1, stdout: /reviewed SGX close grant/});

    body = [noticeQuote];
    const preflightOptions = {...options, env: {...options.env, SGX_PREFLIGHT: "true"}};
    const blocked = await run(process.execPath, noticeArgs, preflightOptions);
    const diagnostic = JSON.parse(blocked.stdout);
    assert.equal(diagnostic.closeRetrieval, "retrieved");
    assert.equal(diagnostic.publicationCheck, "blocked");
    assert.ok(diagnostic.validationErrors.length > 0);
    assert.equal(diagnostic.records, undefined);
    const line = blocked.stderr.split("\n").find(text => text.startsWith("S63 valuation preflight: "));
    assert.ok(line);
    const report = JSON.parse(line.slice("S63 valuation preflight: ".length));
    assert.equal(report.calculated, true);
    assert.equal(report.completeRatios, true);
    assert.equal(report.interimStatus, "calculated");
    assert.equal(report.interimPeriodEnd, "2026-06-30");
    assert.equal(report.per, undefined);
    assert.equal(report.pbr, undefined);
    assert.ok(report.blockers.includes("FINANCIAL_INDEPENDENCE_UNVERIFIED"));
    assert.deepEqual(fs.readFileSync(feedFile), realFeed);

    const summary = path.join(temp, "summary.md");
    const livePreflight = {env: {...applyOptions.env, SGX_REQUESTED_SESSION: matchedSession,
      SGX_PREFLIGHT: "true", GITHUB_STEP_SUMMARY: summary}};
    await run("bash", applyArgs, livePreflight);
    assert.match(fs.readFileSync(summary, "utf8"), /"publicationCheck": "blocked"/);
    assert.deepEqual(fs.readFileSync(feedFile), realFeed);

    const publishable = structuredClone(JSON.parse(realFeed));
    const sourceRow = publishable.records.find(row => row.symbol === "S63");
    Object.assign(sourceRow, {
      quote_timestamp_utc: noticeQuote.timestamp,
      independent_cross_source_verification: true,
      exclusion_reasons: [], quality_flags: [],
    });
    publishable.quality_checked_at_utc = "2026-11-13T11:30:00Z";
    const input = JSON.stringify(publishable);
    fs.writeFileSync(feedFile, input);
    const valid = await run(process.execPath, noticeArgs, preflightOptions);
    assert.deepEqual(JSON.parse(valid.stdout), {
      session: matchedSession, closeRetrieval: "retrieved", publicationCheck: "passed",
      validationErrors: [],
      issuerChecks: [{symbol: "S63", stagingCheck: "passed"}],
    });
    await run("bash", applyArgs, livePreflight);
    assert.match(fs.readFileSync(summary, "utf8"), /"publicationCheck": "passed"/);
    assert.equal(fs.readFileSync(feedFile, "utf8"), input);

    const mixedGrant = {...grant, daily_close_symbols: ["S63", "G13"]};
    fs.writeFileSync(grantFile, JSON.stringify(mixedGrant));
    body = [noticeQuote, {...noticeQuote, symbol: "G13"}];
    const mixed = await run(process.execPath, noticeArgs, preflightOptions);
    const mixedResult = JSON.parse(mixed.stdout);
    assert.equal(mixedResult.publicationCheck, "blocked");
    assert.deepEqual(mixedResult.issuerChecks.map(({symbol, stagingCheck}) => [symbol, stagingCheck]),
      [["S63", "passed"], ["G13", "blocked"]]);
    assert.match(mixed.stderr, /G13 valuation preflight: .*NO_MATCHING_SHARE_FILING/);
    await assert.rejects(run(process.execPath, noticeArgs, options), {code: 1, stdout: ""});
    assert.equal(fs.readFileSync(feedFile, "utf8"), input);
    fs.writeFileSync(grantFile, JSON.stringify(grant));

    body = [{...noticeQuote, close: 0}];
    await assert.rejects(run("bash", applyArgs, livePreflight), {
      code: 1, stderr: /Expected unique licensed SGD closes/,
    });
    assert.equal(fs.readFileSync(feedFile, "utf8"), input);

    const june = "2026-06-10";
    const juneArgs = [...args.slice(0, -1), june];
    const genting = JSON.parse(realFeed);
    const g13 = genting.records.find(row => row.symbol === "G13");
    const originalG13 = structuredClone(g13);
    genting.quality_checked_at_utc = june + "T11:30:00Z";
    Object.assign(g13, {
      quote_timestamp_utc: null,
      shares_as_of_date: "2026-06-09",
      shares_outstanding: 12065642274,
    });
    const g13Grant = {...grant, daily_close_symbols: ["G13"]};
    fs.writeFileSync(grantFile, JSON.stringify(g13Grant));
    fs.writeFileSync(feedFile, JSON.stringify(genting));
    body = [{...quote, symbol: "G13", timestamp: june + "T09:00:00Z"}];
    await assert.rejects(run(process.execPath, juneArgs, options), {
      code: 1, stderr: /existing financial or publication exclusions remain/,
    });

    Object.assign(g13, {
      independent_cross_source_verification: true, exclusion_reasons: [], quality_flags: [],
    });
    fs.writeFileSync(feedFile, JSON.stringify(genting));
    const stagedG13 = JSON.parse((await run(process.execPath, juneArgs, options)).stdout)
      .records.find(row => row.symbol === "G13");
    assert.equal(stagedG13.shares_outstanding, 12063642274);
    assert.equal(stagedG13.shares_as_of_date, june);
    assert.equal(stagedG13.shares_disclosed_at_sgt, june + "T17:55:09+08:00");
    assert.match(stagedG13.shares_source_url, /CHP29KEV0YJ4ZBNY/);
    assert.equal(stagedG13.market_cap_sgd, 24127284548);

    body[0].timestamp = "2026-06-11T09:00:00Z";
    await assert.rejects(run(process.execPath, [...args.slice(0, -1), "2026-06-11"], options), {
      code: 1, stderr: /close and shares need the same Singapore date/,
    });
    body[0].timestamp = june + "T09:00:00Z";
    g13.shares_as_of_date = originalG13.shares_as_of_date;
    fs.writeFileSync(feedFile, JSON.stringify(genting));
    await assert.rejects(run(process.execPath, juneArgs, options), {
      code: 1, stderr: /close and shares need the same Singapore date/,
    });
    fs.writeFileSync(feedFile, realFeed);
    await assert.rejects(run(process.execPath, juneArgs, options), {
      code: 1, stderr: /incoming close predates the published close/,
    });
    fs.writeFileSync(feedFile, input);
    fs.writeFileSync(grantFile, JSON.stringify(grant));

    statuses = [403];
    await assert.rejects(run("bash", applyArgs, livePreflight), {
      code: 1, stderr: /HTTP 403/,
    });
    assert.equal(fs.readFileSync(feedFile, "utf8"), input);
    const pairArgs = [...args.slice(0, -1), "--compare-s63", "2026-11-13", "2026-11-16"];
    fs.writeFileSync(feedFile, realFeed);
    sessionBodies.set("/closes?session=2026-11-13", [noticeQuote]);
    sessionBodies.set("/closes?session=2026-11-16", [{...noticeQuote, timestamp: "2026-11-16T09:00:00Z"}]);
    const pair = JSON.parse((await run(process.execPath, pairArgs, options)).stdout);
    assert.equal(pair.valuationCheck, "passed");
    assert.deepEqual(pair.sessions.map(check => [check.session, check.annualStatus, check.interimStatus]),
      [["2026-11-13", "filing", "calculated"], ["2026-11-16", "filing", "calculated"]]);
    assert.ok(pair.sessions.every(check => check.publicationErrors.length));
    assert.ok(pair.sessions.every(check => !("valuation" in check) && !("price" in check)));
    assert.deepEqual(fs.readFileSync(feedFile), realFeed);
    await assert.rejects(run(process.execPath, [...pairArgs.slice(0, -2), "2026-11-16", "2026-11-13"], options),
      {code: 1, stderr: /in increasing/});
    sessionBodies.set("/closes?session=2026-11-17", [{...noticeQuote, timestamp: "2026-11-17T09:00:00Z"}]);
    await assert.rejects(run(process.execPath, [...pairArgs.slice(0, -1), "2026-11-17"], options), error => {
      assert.equal(error.code, 2);
      assert.equal(JSON.parse(error.stdout).valuationCheck, "blocked");
      return true;
    });
    sessionBodies.set("/closes?session=2026-11-16", []);
    await assert.rejects(run(process.execPath, pairArgs, options), {code: 1, stdout: "", stderr: /missing a configured symbol/});
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
