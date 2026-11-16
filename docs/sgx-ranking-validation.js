"use strict";
// Shared structural validation for the publication workflows and dashboard.
(function (root) {
  const UNOFFICIAL = /YAHOO|UNOFFICIAL|SCRAP|COMMUNITY|MANUAL|USER_INPUT/i;
  const singaporeDate = new Intl.DateTimeFormat("sv-SE", {timeZone: "Asia/Singapore"});
  function validDate(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const date = new Date(value + "T00:00:00Z");
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
  }
  function sgxQuoteDate(value) {
    if (typeof value !== "string" ||
        !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) ||
        !validDate(value.slice(0, 10))) return null;
    const time = Date.parse(value);
    return Number.isFinite(time) ? singaporeDate.format(time) : null;
  }
  const VALUE_SCORE_METHOD = "average_earnings_and_book_yield_v1";

  function valueScore(row) {
    const cap = row.price_sgd * row.shares_outstanding;
    return Number(((row.attributable_profit_sgd_thousands + row.parent_equity_sgd_thousands) *
      50000 / cap).toFixed(6));
  }

  function valuationErrors(row, id) {
    const {price_sgd: price, shares_outstanding: shares,
      attributable_profit_sgd_thousands: profit, parent_equity_sgd_thousands: equity} = row;
    const cap = price * shares;
    if (!Number.isFinite(price) || price <= 0 || !Number.isSafeInteger(shares) || shares <= 0 ||
        !Number.isFinite(cap) || cap > Number.MAX_SAFE_INTEGER / 100) {
      return [id + ": invalid price or shares for valuation"];
    }
    const errors = [];
    const positiveThousands = amount => Number.isSafeInteger(amount) && amount > 0 &&
      Number.isSafeInteger(amount * 1000);
    const checks = [
      ["market cap", row.market_cap_sgd, cap, 100],
      ["PER", row.per_reference, positiveThousands(profit) ? cap / (profit * 1000) : NaN, 10000],
      ["PBR", row.pbr_verified, positiveThousands(equity) ? cap / (equity * 1000) : NaN, 10000],
    ];
    for (const [label, actual, expected, scale] of checks) {
      // The feed rounds cap to cents and the ratios to four decimal places.
      if (!Number.isFinite(actual) || actual <= 0 || !Number.isFinite(expected) ||
          Math.abs(actual - expected) > 0.5 / scale + Number.EPSILON * expected) {
        errors.push(id + ": " + label + " missing or inconsistent with valuation inputs");
      }
    }
    return errors;
  }
  function checkProvenance(feed) {
    const errors = [];
    if (!feed || !Array.isArray(feed.records)) return ["Missing records array"];
    const seen = new Set();
    let eligible = 0;
    for (const [i, r] of feed.records.entries()) {
      if (!r || typeof r !== "object") { errors.push("Invalid row " + i); continue; }
      const id = String(r.symbol || ("row_" + i));
      if (seen.has(id)) errors.push(id + ": duplicate symbol");
      seen.add(id);
      const reasons = Array.isArray(r.exclusion_reasons) ? r.exclusion_reasons : [];
      if (r.ranking_eligible === true) {
        eligible++;
        errors.push(...valuationErrors(r, id));
        if (r.ranking_score == null || !Number.isFinite(r.ranking_score))
          errors.push(id + ": ranking score missing/invalid");
        if (r.ranking_score_method !== undefined &&
            (r.ranking_score_method !== VALUE_SCORE_METHOD || r.ranking_score !== valueScore(r)))
          errors.push(id + ": ranking score does not match the valuation inputs");
        if (UNOFFICIAL.test(String(r.quote_source_type || "")))
          errors.push(id + ": unofficial quote in investable ranking");
        if (r.quote_license_display_allowed !== true ||
            r.quote_license_non_display_analytics_allowed !== true)
          errors.push(id + ": both quote display/non-display licenses not evidenced");
        if (r.independent_cross_source_verification !== true)
          errors.push(id + ": independent financial evidence not verified");
        if (!Number.isInteger(r.shares_outstanding) || r.shares_outstanding <= 0 ||
            r.shares_count_basis !== "issued_excluding_treasury")
          errors.push(id + ": ex-treasury share count not verified");
        const quoteDate = sgxQuoteDate(r.quote_timestamp_utc);
        if (!quoteDate || !validDate(r.shares_as_of_date))
          errors.push(id + ": missing dated quote/shares");
        else if (r.shares_as_of_date !== quoteDate)
          errors.push(id + ": quote and shares are not on the same Singapore date");
        if (reasons.length) errors.push(id + ": eligible while exclusion reasons remain");
      } else {
        if (r.ranking_score != null) errors.push(id + ": excluded record has ranking score");
      }
    }
    if (eligible !== feed.ranking_eligible_count) errors.push("eligible count differs from rows");
    if (feed.ranking_enabled !== (eligible > 0))
      errors.push("ranking_enabled inconsistent with eligible rows");
    if (feed.coverage && feed.coverage.registered_count !== feed.records.length)
      errors.push("registered_count inconsistent with records");
    return errors;
  }
  function validHTTPS(v) {
    if (typeof v !== "string" || !/^https:\/\//i.test(v)) return false;
    try { const u = new URL(v); return Boolean(u.hostname && !u.username && !u.password); }
    catch { return false; }
  }
  function checkFeed(feed) {
    const errors=checkProvenance(feed);
    if(!feed || !Array.isArray(feed.records)) return errors;
    for (const [i,r] of feed.records.entries()) {
      if(r?.ranking_eligible !== true) continue;
      const id=String(r.symbol||("row_"+i));
      const proof=r.market_data_license_evidence;
      if(!proof || typeof proof !== "object" || Array.isArray(proof)) {
        errors.push(id+": dated grant evidence missing"); continue;
      }
      if(proof.grant_status !== "EXECUTED" ||
         !validHTTPS(proof.grant_evidence_url) ||
         typeof proof.licensor !== "string" || !proof.licensor.trim() ||
         typeof proof.licensee !== "string" || !proof.licensee.trim() ||
         typeof proof.licensed_product !== "string" || !proof.licensed_product.trim())
        errors.push(id+": executed license provenance incomplete");
      // Eligible rows publish the raw close in latest.json and in the dashboard CSV.
      const scopes=proof.usage_scopes;
      if(!Array.isArray(scopes) ||
         !scopes.includes("BROWSER_DISPLAY") ||
         !scopes.includes("BACKEND_NON_DISPLAY_ANALYTICS") ||
         !scopes.includes("REDISTRIBUTION"))
        errors.push(id+": required SGX usage scopes missing");
      if(!validDate(proof.valid_from) || !validDate(proof.valid_until) ||
         proof.valid_from > proof.valid_until)
        errors.push(id+": license validity dates incorrect");
      else {
        const quoteDate=sgxQuoteDate(r.quote_timestamp_utc);
        if(!quoteDate || quoteDate<proof.valid_from || quoteDate>proof.valid_until)
          errors.push(id+": quote timestamp outside license validity");
      }
      if(!validHTTPS(r.quote_url))
        errors.push(id+": licensed quote origin URL missing");
    }
    return errors;
  }

  const api = {checkFeed, checkProvenance, sgxQuoteDate, validDate, valueScore, VALUE_SCORE_METHOD};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.SgxRankingValidation = api;
})(typeof window !== "undefined" ? window : null);
