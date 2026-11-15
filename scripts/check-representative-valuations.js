"use strict";

const fs = require("node:fs");
const path = require("node:path");
const {createHash} = require("node:crypto");
const {spawnSync} = require("node:child_process");
const {
  buildMarketRows, evaluatePersonalQuotes, publishedShareSessions, readQuoteHistory,
} = require("../docs/market-research.js");

const data = path.join(__dirname, "../docs/data");
const representatives = ["JP:7203", "US:IBM", "SG:S63"];

function observedCoverage(sessions, priceField) {
  const observations = sessions.filter(session => session[priceField] !== null);
  return observations.length ?
    {first: observations[0].date, last: observations.at(-1).date, count: observations.length} : null;
}

function loadSnapshot(name) {
  return JSON.parse(fs.readFileSync(path.join(data, name), "utf8"));
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

function reviewQuoteRefresh(rows, shareReview, previous, current) {
  const latest = reviewRepresentativeValuations(rows, shareReview, current);
  const shareSessions = publishedShareSessions(rows, shareReview);
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
    if (shares && change !== "unchanged") {
      session.valuationImpact = {
        previous: before ? reviewShareSession(rows, shareReview, id, date, shares, before) : null,
        current: after ? reviewShareSession(rows, shareReview, id, date, shares, after) : null,
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
      sharedDateRange, datesMissingFromCurrentWithinRange, newTradingDates};
  });
  return {...latest, results: updates};
}

function main(args) {
  const refresh = args[0] === "--compare" && args.length === 3;
  const verifiedRefresh = args[0] === "--compare-jquants" && args.length === 5;
  if (!refresh && !verifiedRefresh && (args.length > 1 || args[0]?.startsWith("--"))) {
    throw Error("Usage: node scripts/check-representative-valuations.js [local-quotes.csv], --compare previous.csv current.csv, or --compare-jquants previous.csv previous.json current.csv current.json");
  }
  const research = loadSnapshot("market-research-v315.json");
  const sgx = loadSnapshot("latest.json");
  const shareReview = loadSnapshot("sgx-s63-two-website-close-v129.json");
  const rows = buildMarketRows(research, sgx);
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
  if (refresh || verifiedRefresh) {
    const previous = loadQuotes(args[1], verifiedRefresh ? args[2] : undefined);
    const current = verifiedRefresh ? loadQuotes(args[3], args[4]) : loadQuotes(args[2]);
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
    report = reviewQuoteRefresh(rows, shareReview, previous.quotes, current.quotes);
    if (verifiedRefresh) report.snapshotVerification = "jquants_personal_receipts_matched";
    report.snapshots = {
      previous: {sha256: previous.sha256, observations: previous.quotes.size},
      current: {sha256: current.sha256, observations: current.quotes.size},
    };
    if (verifiedRefresh) {
      report.snapshots.previous.retrievedAtUtc = previous.receiptEvidence.retrieved_at_utc;
      report.snapshots.current.retrievedAtUtc = current.receiptEvidence.retrieved_at_utc;
    }
  } else {
    report = reviewRepresentativeValuations(rows, shareReview, args.length ? loadQuotes(args[0]).quotes : new Map());
  }
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
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
