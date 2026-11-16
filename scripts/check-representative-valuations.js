"use strict";

const fs = require("node:fs");
const path = require("node:path");
const {createHash} = require("node:crypto");
const {spawnSync} = require("node:child_process");
const {
  buildMarketRows, evaluatePersonalQuotes, publishedShareSessions, readQuoteHistory, selectQuoteDate,
} = require("../docs/market-research.js");

const data = path.join(__dirname, "../docs/data");
const representatives = ["JP:7203", "US:IBM", "SG:S63"];

function observedCoverage(sessions, priceField) {
  const observations = sessions.filter(session => session[priceField] !== null);
  return observations.length ?
    {first: observations[0].date, last: observations.at(-1).date, count: observations.length} : null;
}

function loadSnapshot(directory, name, evidence) {
  const bytes = fs.readFileSync(path.join(directory, name));
  evidence[name] = createHash("sha256").update(bytes).digest("hex");
  return JSON.parse(bytes.toString("utf8"));
}

function loadS63Notice(url) {
  const parser = path.join(__dirname, "../SGX_PDF_connection_probe/sgx_s63_buyback_v109.py");
  const result = spawnSync("python3", [parser, "--output", "-", "--url=" + url], {encoding: "utf8"});
  if (result.error) throw result.error;
  if (result.status !== 0) throw Error(result.stderr.trim() || "S63 notice verification failed");
  const notice = JSON.parse(result.stdout);
  return {
    schema_version: "sgx-s63-dated-share-notice-v423",
    symbol: notice.symbol,
    session_date_sgt: notice.purchase_date,
    original_sgx_share_snapshot_on_same_date: true,
    original_sgx_shares_ex_treasury: notice.issued_excluding_treasury_after_purchase,
    sgx_share_source_url: notice.source_url,
    sgx_share_disclosed_at_sgt: notice.broadcast_at_sgt,
    sourceSha256: notice.source_sha256,
    announcementReference: notice.reference,
  };
}

function reviewShareSession(rows, shareReview, id, date, shares, observation) {
  const evidence = {id, date, shares: shares.value, shareSource: shares.source};
  if (shares.disclosedOn) {
    evidence.shareDisclosureDate = shares.disclosedOn;
    evidence.shareDisclosedAt = shares.disclosedAt;
    evidence.shareDisclosureTiming = shares.disclosureTiming;
    evidence.shareDisclosedAfterSession = shares.disclosureTiming === "time_unknown" ? null :
      ["after_date", "after_close"].includes(shares.disclosureTiming);
  }
  if (!observation) return {...evidence, status: "missing_exact_close"};
  const [valuation] = evaluatePersonalQuotes(rows, new Map([[id, observation]]), new Map(), shareReview);
  if (valuation.state !== "filing" || !valuation.result) return {...evidence, status: valuation.state};
  return {...evidence, status: "trial_calculated", price: observation.price,
    financeSource: valuation.financeSource, valuation: valuation.result};
}

function reviewRepresentativeValuations(rows, shareReview, history = new Map()) {
  const dates = publishedShareSessions(rows, shareReview);
  const results = representatives.map(id => {
    let latest;
    for (const [date, records] of dates) {
      const shares = records.find(record => record.id === id);
      if (!shares) continue;
      const observation = history.get(id + ":" + date);
      if (latest && !observation) continue;
      const trial = reviewShareSession(rows, shareReview, id, date, shares, observation);
      if (!latest) {
        latest = trial;
        if (trial.status === "trial_calculated") return trial;
      } else if (trial.status === "trial_calculated") {
        return {...latest, latestAvailableTrial: trial};
      }
    }
    return latest ?? {id, status: "missing_share_evidence"};
  });
  return {scope: "local_trial", basis: "retrospective", results};
}

function reviewQuoteRefresh(rows, shareReview, previous, current, previousRows = rows, previousShareReview = shareReview) {
  const latest = reviewRepresentativeValuations(rows, shareReview, current);
  const shareSessions = publishedShareSessions(rows, shareReview);
  const previousShareSessions = previousRows === rows && previousShareReview === shareReview ?
    shareSessions : publishedShareSessions(previousRows, previousShareReview);
  const changesByIssuer = new Map(representatives.map(id => [id, []]));
  const keys = new Set([...previous.keys(), ...current.keys()]);
  for (const key of keys) {
    const before = previous.get(key);
    const after = current.get(key);
    const {id, date} = after || before;
    const changes = changesByIssuer.get(id);
    if (!changes) continue;
    const change = !before ? "added" : !after ? "removed" :
      before.price === after.price ? "unchanged" : "revised";
    const shares = shareSessions.get(date)?.find(record => record.id === id);
    const session = {
      date, change, previousPrice: before?.price ?? null, currentPrice: after?.price ?? null,
      hasExactShares: Boolean(shares),
    };
    const earlierShares = previousShareSessions.get(date)?.find(record => record.id === id);
    if ((shares || earlierShares) && change !== "unchanged") {
      session.valuationImpact = {
        previous: before && earlierShares ?
          reviewShareSession(previousRows, previousShareReview, id, date, earlierShares, before) : null,
        current: after && shares ? reviewShareSession(rows, shareReview, id, date, shares, after) : null,
      };
    }
    changes.push(session);
  }

  const updates = latest.results.map(result => {
    const {id, date} = result;
    const sessionChanges = changesByIssuer.get(id).sort((a, b) => a.date.localeCompare(b.date));
    const matchedSession = sessionChanges.find(entry => entry.date === date);
    const newerUnmatchedDates = sessionChanges.filter(entry =>
      date && entry.date > date && entry.currentPrice !== null && !entry.hasExactShares).map(entry => entry.date);
    const before = observedCoverage(sessionChanges, "previousPrice");
    const after = observedCoverage(sessionChanges, "currentPrice");
    const lastTrial = (coverage, history, trialRows, trialShareReview, trialShareSessions) => {
      if (!coverage) return null;
      const date = coverage.last;
      const quote = history.get(id + ":" + date);
      const shares = trialShareSessions.get(date)?.find(record => record.id === id);
      return shares ? reviewShareSession(trialRows, trialShareReview, id, date, shares, quote) :
        {id, date, price: quote.price, status: "no_exact_share_evidence"};
    };
    // File coverage bounds alone cannot establish that a session was dropped by the provider.
    const first = before && after ? [before.first, after.first].sort().at(-1) : null;
    const last = before && after ? [before.last, after.last].sort()[0] : null;
    const sharedDateRange = first && first <= last ? {first, last} : null;
    const hasSharedDateRange = entry => sharedDateRange && entry.date >= first && entry.date <= last;
    const datesMissingFromCurrentWithinRange = sessionChanges
      .filter(entry => entry.change === "removed" && hasSharedDateRange(entry)).map(entry => entry.date);
    const newTradingDates = before ? sessionChanges
      .filter(entry => entry.change === "added" && entry.date > before.last)
      .map(entry => entry.date) : [];
    return {...result, closeChange: matchedSession?.change ?? "absent",
      previousPrice: matchedSession?.previousPrice ?? null, newerUnmatchedDates, sessionChanges,
      quoteCoverage: {previous: before, current: after},
      latestObservedTrials: {
        previous: lastTrial(before, previous, previousRows, previousShareReview, previousShareSessions),
        current: lastTrial(after, current, rows, shareReview, shareSessions),
      },
      sharedDateRange, datesMissingFromCurrentWithinRange, newTradingDates};
  });
  return {...latest, results: updates};
}

function main(args) {
  let filingDirectory = data;
  if (args[0] === "--filing-dir") {
    if (!args[1] || args[1].startsWith("--")) throw Error("--filing-dir requires a directory");
    filingDirectory = args[1];
    args = args.slice(2);
  }
  let previousFilingDirectory;
  if (args[0] === "--previous-filing-dir") {
    if (!args[1] || args[1].startsWith("--")) throw Error("--previous-filing-dir requires a directory");
    previousFilingDirectory = args[1];
    args = args.slice(2);
  }
  const s63NoticeUrls = new Set();
  while (args[0] === "--s63-notice-url") {
    if (!args[1] || args[1].startsWith("--")) throw Error("--s63-notice-url requires an official SGXNet URL");
    s63NoticeUrls.add(args[1]);
    args = args.slice(2);
  }
  const requireToyotaRefresh = args[0] === "--require-toyota-refresh";
  const requireBothTrials = requireToyotaRefresh || args[0] === "--require-both-trials";
  const requireNewSessions = requireBothTrials || args[0] === "--require-new-sessions";
  const requireLatestTrials = requireNewSessions || args[0] === "--require-latest-trials";
  if (requireLatestTrials) args = args.slice(1);
  const refresh = args[0] === "--compare" && args.length === 3;
  const verifiedRefresh = args[0] === "--compare-jquants" && args.length === 5;
  const verifiedSnapshot = args[0] === "--jquants" && args.length === 3;
  if (requireToyotaRefresh && !verifiedRefresh) {
    throw Error("--require-toyota-refresh requires --compare-jquants");
  }
  if (previousFilingDirectory && !refresh && !verifiedRefresh) {
    throw Error("--previous-filing-dir requires a two-snapshot comparison");
  }
  if (requireNewSessions && !refresh && !verifiedRefresh) {
    throw Error("The requested session check requires a two-snapshot comparison");
  }
  if (!refresh && !verifiedRefresh && !verifiedSnapshot && (args.length > 1 || args[0]?.startsWith("--"))) {
    throw Error("Usage: node scripts/check-representative-valuations.js [--filing-dir directory] [--previous-filing-dir directory] [--s63-notice-url URL ...] [--require-latest-trials | --require-new-sessions | --require-both-trials | --require-toyota-refresh] [local-quotes.csv | --jquants quotes.csv receipt.json | --compare previous.csv current.csv | --compare-jquants previous.csv previous.json current.csv current.json]");
  }
  const filingDataSha256 = {};
  const loadFilings = (directory, evidence) => {
    const research = loadSnapshot(directory, "market-research-v315.json", evidence);
    const sgx = loadSnapshot(directory, "latest.json", evidence);
    const shares = loadSnapshot(directory, "sgx-s63-two-website-close-v129.json", evidence);
    const shareReview = [shares].flat();
    const historicalName = "sgx-s63-historical-shares-v423.json";
    if (fs.existsSync(path.join(directory, historicalName))) {
      shareReview.push(loadSnapshot(directory, historicalName, evidence));
    }
    return {rows: buildMarketRows(research, sgx), shareReview};
  };
  const currentFilings = loadFilings(filingDirectory, filingDataSha256);
  const rows = currentFilings.rows;
  const notices = Array.from(s63NoticeUrls, loadS63Notice);
  const shareReview = currentFilings.shareReview.concat(notices);
  const loadQuotes = (filename, receipt) => {
    const bytes = fs.readFileSync(filename);
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    let receiptEvidence;
    if (receipt !== undefined) {
      const verifier = path.join(__dirname, "verify-jquants-personal-snapshot.py");
      const result = spawnSync("python3", [verifier, "--", filename, receipt], {encoding: "utf8"});
      if (result.error) throw result.error;
      if (result.status !== 0) throw Error(result.stderr.trim() || "J-Quants snapshot verification failed");
      receiptEvidence = JSON.parse(result.stdout);
      if (receiptEvidence.csv_sha256 !== sha256) {
        throw Error("CSV changed during snapshot verification");
      }
    }
    return {
      quotes: readQuoteHistory(bytes.toString("utf8")),
      sha256,
      receiptEvidence,
    };
  };
  let report;
  let currentQuotes;
  if (refresh || verifiedRefresh) {
    const previous = loadQuotes(args[1], verifiedRefresh ? args[2] : undefined);
    const current = verifiedRefresh ? loadQuotes(args[3], args[4]) : loadQuotes(args[2]);
    currentQuotes = current.quotes;
    if (verifiedRefresh) {
      const before = previous.receiptEvidence;
      const after = current.receiptEvidence;
      if (!before.retrieved_at_utc || !after.retrieved_at_utc || before.retrieved_at_utc >= after.retrieved_at_utc) {
        throw Error("J-Quants receipts need UTC retrieval timestamps in strictly increasing order");
      }
      if (before.codes.join(",") !== after.codes.join(",")) {
        throw Error("J-Quants receipts must cover the same requested securities");
      }
    }
    const previousFilingDataSha256 = {};
    const baseline = previousFilingDirectory && loadFilings(previousFilingDirectory, previousFilingDataSha256);
    report = reviewQuoteRefresh(rows, shareReview, previous.quotes, current.quotes,
      baseline?.rows, baseline?.shareReview);
    if (baseline) report.previousFilingDataSha256 = previousFilingDataSha256;
    if (verifiedRefresh) report.snapshotVerification = "jquants_personal_receipts_matched";
    report.snapshots = {
      previous: {sha256: previous.sha256, observations: previous.quotes.size},
      current: {sha256: current.sha256, observations: current.quotes.size},
    };
    if (verifiedRefresh) {
      report.snapshots.previous.retrievedAtUtc = previous.receiptEvidence.retrieved_at_utc;
      report.snapshots.current.retrievedAtUtc = current.receiptEvidence.retrieved_at_utc;
    }
  } else if (verifiedSnapshot) {
    const current = loadQuotes(args[1], args[2]);
    currentQuotes = current.quotes;
    report = reviewRepresentativeValuations(rows, shareReview, current.quotes);
    report.snapshotVerification = "jquants_personal_receipt_matched";
    report.snapshots = {current: {
      sha256: current.sha256, observations: current.quotes.size,
      retrievedAtUtc: current.receiptEvidence.retrieved_at_utc,
    }};
  } else {
    currentQuotes = args.length ? loadQuotes(args[0]).quotes : new Map();
    report = reviewRepresentativeValuations(rows, shareReview, currentQuotes);
  }
  if (requireLatestTrials) {
    const newest = selectQuoteDate(currentQuotes);
    const checkedIssuers = requireToyotaRefresh ? ["JP:7203"] : representatives;
    const checks = checkedIssuers.map(id => {
      const quote = newest.get(id);
      const comparison = requireNewSessions ? report.results.find(row => row.id === id) : null;
      const previousDate = comparison?.quoteCoverage.previous?.last ?? null;
      const sessionAdvance = comparison ? {
        previousDate, hasNewSession: Boolean(quote && previousDate && quote.date > previousDate),
      } : {};
      if (requireBothTrials) {
        const previousTrial = comparison.latestObservedTrials.previous;
        const ratios = previousTrial?.valuation;
        sessionAdvance.previousStatus = previousTrial?.status ?? "missing_close";
        if (previousTrial?.status === "trial_calculated" &&
            !(Number.isFinite(ratios?.per) && Number.isFinite(ratios?.pbr))) {
          sessionAdvance.previousStatus = "incomplete_ratios";
        }
      }
      if (!quote) return {id, status: "missing_close", ...sessionAdvance};
      const [trial] = evaluatePersonalQuotes(rows, new Map([[id, quote]]), new Map(), shareReview);
      const valuation = trial.result;
      const status = trial.state !== "filing" ? trial.state :
        Number.isFinite(valuation?.per) && Number.isFinite(valuation?.pbr) ?
          "trial_calculated" : "incomplete_ratios";
      return {id, date: quote.date, status, price: quote.price, shares: trial.shares,
        shareSource: trial.shareSource, financeSource: trial.financeSource, valuation, ...sessionAdvance};
    });
    const passed = checks.every(check => check.status === "trial_calculated" &&
      (!requireNewSessions || check.hasNewSession) &&
      (!requireBothTrials || check.previousStatus === "trial_calculated"));
    report.latestTrialCheck = {passed, results: checks};
    if (requireToyotaRefresh) report.latestTrialCheck.scope = "jquants_personal_toyota";
    if (!passed) process.exitCode = 2;
  }
  if (notices.length) report.s63ShareNotices = notices;
  if (notices.length === 1) report.s63ShareNotice = notices[0];
  process.stdout.write(JSON.stringify({...report, filingDataSha256}, null, 2) + "\n");
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
