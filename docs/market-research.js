"use strict";

const marketLabels = {JP: "日本", US: "米国", SG: "シンガポール"};
const money = new Intl.NumberFormat("ja-JP");
const percent = new Intl.NumberFormat("ja-JP", {style: "percent", maximumFractionDigits: 1});

function annualGrowth(previous, current) {
  return previous > 0 && Number.isFinite(current) ? (current - previous) / previous : null;
}

function buildMarketRows(research, sgx) {
  if (research.schema !== "market-research-v315" || !Array.isArray(research.records) ||
      !Array.isArray(sgx.records)) throw Error("銘柄資料の形式が不明");
  const rows = [...research.records, ...sgx.records.map(record => ({
    id: "SG:" + record.symbol,
    market: "SG",
    symbol: record.symbol,
    label: record.issuer || record.name || record.company_name || record.symbol,
    identity_source: "./sgx-32-research.html",
    sgxAnnual: sgxComparison(sgx, record),
    sgxEvidence: record,
    rankingEligible: sgx.ranking_enabled === true && record.ranking_eligible === true,
  }))];
  const ids = new Set();
  for (const row of rows) {
    if (!Object.hasOwn(marketLabels, row.market) || row.id !== row.market + ":" + row.symbol ||
        !/^[A-Z0-9.-]{1,12}$/.test(row.symbol) || ids.has(row.id) || typeof row.label !== "string") {
      throw Error("銘柄識別子の重複または形式不一致");
    }
    ids.add(row.id);
  }
  return rows;
}

function rankingEvidence(row, shareReview) {
  const sgx = row.sgxEvidence;
  const finance = row.financials;
  const shares = row.quarterly?.share_classes || row.quarterly?.shares || finance?.shares || finance?.share_classes;
  if (!sgx) {
    return {
      quote: "未接続",
      share: shares ? shares.as_of + (finance?.share_classes ? "（クラス別開示）" : shares.rounded ? "（概数）" : "（開示資料）") : "未取得",
      shareSource: (row.quarterly?.shares || row.quarterly?.share_classes) ? row.quarterly.source : finance?.filing_url || finance?.source,
      reasons: [finance ? "正式順位の財務審査が未実装" : "年次財務が未取得",
        "公開用の株価データが未接続", "株価と株数の同日照合が未完了",
        ...(finance?.share_classes ? ["株式クラスごとの評価が必要"] : [])],
    };
  }

  const observedAt = sgx.quote_timestamp_utc;
  const observed = typeof observedAt === "string" && Number.isFinite(Date.parse(observedAt));
  const quoteDate = observed ? new Intl.DateTimeFormat("sv-SE", {timeZone: "Asia/Singapore"}).format(new Date(observedAt)) : null;
  const shareDate = isMarketDate(sgx.shares_as_of_date) ? sgx.shares_as_of_date : null;
  const reasons = [];
  if (sgx.exclusion_reasons?.includes("INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE")) reasons.push("財務の独立検証が未完了");
  if (sgx.exclusion_reasons?.includes("NEGATIVE_EARNINGS_PER_NOT_APPLICABLE")) reasons.push("赤字のためPER対象外");
  if (!observed) reasons.push("日付付き株価が未取得");
  if (sgx.quote_source_type === "YAHOO_FINANCE_UNOFFICIAL_CHART") reasons.push("掲載株価は参考取得。取引所の照合が未完了");
  if (!shareDate) reasons.push("日付付き株数が未取得");
  if (shareDate && quoteDate && shareDate !== quoteDate) reasons.push("掲載データの株価と株数の基準日が異なる");
  return {
    supplementalShare: sgxSupplementalShare(row, quoteDate, shareReview),
    quote: observed ? quoteDate + (sgx.quote_source_type === "YAHOO_FINANCE_UNOFFICIAL_CHART" ? "（参考）" : "（掲載資料）") : "未取得",
    quoteSource: observed ? sgx.quote_url : null,
    share: shareDate || "未取得",
    shareSource: shareDate ? sgx.shares_source_url : null,
    reasons,
  };
}

function sgxSupplementalShare(row, date, review) {
  if (row.id !== "SG:S63" || review?.schema_version !== "sgx-s63-historical-close-second-website-v129" ||
      review.symbol !== row.symbol || review.session_date_sgt !== date ||
      review.original_sgx_share_snapshot_on_same_date !== true ||
      !Number.isSafeInteger(review.original_sgx_shares_ex_treasury) || review.original_sgx_shares_ex_treasury <= 0 ||
      !review.sgx_share_source_url?.startsWith("https://links.sgx.com/")) return null;
  return {date, value: review.original_sgx_shares_ex_treasury, source: review.sgx_share_source_url};
}

function sgxComparison(feed, record) {
  const revenue = record.revenue_sgd_thousands * 1000;
  if (feed.currency !== "SGD" || feed.financial_unit !== "SGD_thousands" ||
      !Number.isInteger(record.fiscal_year) || !record.financial_source_url?.startsWith("https://") ||
      !Number.isSafeInteger(revenue) || revenue <= 0) return null;
  const toRatio = value => Number.isFinite(value) ? value / 100 : null;
  const assets = record.assets_sgd_thousands;
  const parentEquity = record.parent_equity_sgd_thousands;
  return {
    end: "FY" + record.fiscal_year,
    currency: feed.currency,
    revenue,
    salesGrowth: toRatio(record.revenue_growth_pct),
    operatingMargin: toRatio(record.operating_margin_pct),
    equityRatio: Number.isFinite(assets) && assets > 0 && Number.isFinite(parentEquity) ? parentEquity / assets : null,
    source: record.financial_source_url,
    sourceLabel: record.data_state === "VERIFIED" ? "SGX出典" : "SGX出典（照合途中）",
  };
}

function summarizeMarketCoverage(rows) {
  return Object.entries(marketLabels).map(([market, label]) => {
    const listed = rows.filter(row => row.market === market);
    return {
      label,
      listed: listed.length,
      comparable: listed.filter(row => row.financials || row.sgxAnnual).length,
      quarterly: listed.filter(row => row.quarterly).length,
      rankable: listed.filter(row => row.rankingEligible === true).length,
    };
  });
}

function filterMarketRows(rows, market, query, evidence = "all") {
  const term = query.trim().normalize("NFKC").toUpperCase();
  return rows.filter(row => (!market || row.market === market) &&
    (evidence === "all" ||
      (evidence === "annual" && Boolean(row.financials || row.sgxAnnual)) ||
      (evidence === "quarterly" && Boolean(row.quarterly)) ||
      (evidence === "missing" && !row.financials && !row.sgxAnnual)) &&
    [row.id, row.symbol, row.label, row.name,
      ...(row.financials?.share_classes?.classes.map(item => item.symbol) || [])].some(value =>
      value?.normalize("NFKC").toUpperCase().includes(term)));
}

function compareAnnual(finance) {
  if (!["JPY", "USD"].includes(finance.currency) || finance.periods.length !== 2) {
    throw Error("年間決算の資料範囲が不明");
  }
  const [prior, latest] = finance.periods;
  const days = (start, end) => (Date.parse(end) - Date.parse(start)) / 86400000 + 1;
  if (![prior, latest].every(row => {
    const duration = days(row.start, row.end);
    return duration >= 350 && duration <= 380 &&
      [row.revenue, row.net_income, row.assets, row.parent_equity].every(Number.isSafeInteger) &&
      (row.operating_income === null || Number.isSafeInteger(row.operating_income)) &&
      row.revenue > 0 && row.assets > 0;
  }) || days(prior.end, latest.start) !== 2) throw Error("連続した年間決算を照合できない");
  return finance.periods.map((row, i) => ({
    ...row,
    salesGrowth: i ? annualGrowth(prior.revenue, latest.revenue) : null,
    operatingGrowth: i ? annualGrowth(prior.operating_income, latest.operating_income) : null,
    operatingMargin: row.operating_income === null ? null : row.operating_income / row.revenue,
    equityRatio: row.parent_equity / row.assets,
  }));
}

function isMarketDate(date) {
  const parsed = new Date(date + "T00:00:00Z");
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === date;
}

function readQuoteHistory(csv) {
  const lines = csv.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.shift() !== "market_id,date,currency,close") {
    throw Error("CSVの見出しは market_id,date,currency,close");
  }
  const currencies = {JP: "JPY", US: "USD", SG: "SGD"};
  const quotes = new Map();
  for (const [index, line] of lines.entries()) {
    const [id, date, currency, close, extra] = line.split(",").map(value => value.trim());
    const price = Number(close);
    const key = id + ":" + date;
    if (extra !== undefined || !/^(JP|US|SG):[A-Z0-9.-]{1,12}$/.test(id) || !isMarketDate(date) ||
        currency !== currencies[id.slice(0, 2)] || !/^\d+(\.\d+)?$/.test(close) ||
        !Number.isFinite(price) || price <= 0 || quotes.has(key)) {
      throw Error("CSVの " + (index + 2) + " 行目を確認して。銘柄、日付、通貨、終値、重複の有無が合っているか見て");
    }
    quotes.set(key, {id, date, currency, price});
  }
  if (quotes.size === 0) throw Error("CSVに株価の行がない");
  return quotes;
}

function selectQuoteDate(history, date = "") {
  const result = new Map();
  for (const {id, ...quote} of history.values()) {
    if (date && quote.date !== date) continue;
    if (!result.has(id) || quote.date > result.get(id).date) result.set(id, quote);
  }
  return result;
}

function readPersonalQuotes(csv) {
  return selectQuoteDate(readQuoteHistory(csv));
}

function parsePublishedShareRow(line) {
  const match = /^"([^"]+)","([^"]+)","(\d+)","(?:[^"]|"")*"$/.exec(line);
  return match ? match.slice(1) : [];
}

function readPersonalShares(csv) {
  const lines = csv.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const header = lines.shift();
  const expected = "market_id,date,shares_excluding_treasury";
  const sourced = header === expected + ",filing_source_url";
  if (header !== expected && !sourced) throw Error("CSVの見出しは " + expected);
  const shares = new Map();
  for (const [index, line] of lines.entries()) {
    // An exported source URL is informational. Only the in-app filing records
    // can establish the source link and evidence state of a valuation.
    const cells = sourced ? parsePublishedShareRow(line) : line.split(",").map(value => value.trim());
    const [id, date, count, extra] = cells;
    const value = Number(count);
    const key = id + ":" + date;
    if (extra !== undefined || !/^(JP|US|SG):[A-Z0-9.-]{1,12}$/.test(id) ||
        !isMarketDate(date) || !/^\d+$/.test(count) || !Number.isSafeInteger(value) ||
        value <= 0 || shares.has(key)) {
      throw Error("株数CSVの " + (index + 2) + " 行目を確認して。銘柄、日付、株数、重複の有無が合っているか見て");
    }
    shares.set(key, value);
  }
  if (shares.size === 0) throw Error("CSVに株数の行がない");
  return shares;
}

const sgxValuationPeriods = {
  S68: {end: "2026-06-30",
    source: "https://investorrelations.sgx.com/static-files/3f7a49c0-fc5e-44fa-a851-bf26067249c5"},
  G13: {end: "2025-12-31",
    source: "https://links.sgx.com/FileOpen/Annual%20Report%202025.ashx?App=Announcement&FileID=880160"},
  S20: {end: "2025-12-31",
    source: "https://links.sgx.com/FileOpen/Annual%20Report%20FY2025.ashx?App=Announcement&FileID=881971"},
  S63: {end: "2025-12-31",
    source: "https://links.sgx.com/FileOpen/ST%20Engineering%20Annual%20Report%202025.ashx?App=Announcement&FileID=880328"},
};

function sgxValuationFinance(row) {
  const record = row.sgxEvidence;
  const filing = sgxValuationPeriods[row.symbol];
  if (!record || !row.sgxAnnual || !filing || record.financial_source_url !== filing.source ||
      record.fiscal_year !== Number(filing.end.slice(0, 4)) ||
      ![record.attributable_profit_sgd_thousands, record.parent_equity_sgd_thousands]
        .every(value => Number.isSafeInteger(value) && Number.isSafeInteger(value * 1000))) return null;
  return {
    currency: "SGD", end: filing.end, source: filing.source, net_income: record.attributable_profit_sgd_thousands * 1000,
    parent_equity: record.parent_equity_sgd_thousands * 1000,
  };
}

function filingSharesOn(row, date, shareReview) {
  const withSource = (share, source) => share ? {...share, source} : null;
  const interim = withSource(row.quarterly?.shares, row.quarterly?.source);
  const annual = withSource(row.financials?.shares, row.financials?.filing_url || row.financials?.source);
  const sgx = row.sgxEvidence;
  const currentShare = sgx?.shares_count_basis === "issued_excluding_treasury" &&
    sgx.shares_source_url?.startsWith("https://") && [
      "LIVE_OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED", "LIVE_1H2026_TREASURY_ROLLFORWARD_RECONCILED",
      "DATE_ANCHORED_RECONCILED",
    ].includes(sgx.shares_verification_status)
    ? {as_of: sgx.shares_as_of_date, value: sgx.shares_outstanding, source: sgx.shares_source_url} : null;
  const supplemental = sgxSupplementalShare(row, date, shareReview);
  const datedSupplement = supplemental ? {as_of: supplemental.date, value: supplemental.value, source: supplemental.source} : null;
  return [interim, annual, currentShare, datedSupplement].filter(share => share?.as_of === date && !share.rounded);
}

function publishedShareSessions(rows, shareReview) {
  const sessions = new Map();
  for (const row of rows) {
    if (row.financials?.share_classes || (!row.financials && !sgxValuationFinance(row))) continue;
    const dates = new Set([row.financials?.shares?.as_of, row.quarterly?.shares?.as_of,
      row.sgxEvidence?.shares_as_of_date, row.market === "SG" ? shareReview?.session_date_sgt : null]);
    for (const date of dates) {
      if (!isMarketDate(date)) continue;
      const evidence = filingSharesOn(row, date, shareReview).filter(share => share.source?.startsWith("https://"));
      const match = matchScenarioShares(row.id, date, evidence, new Map());
      if (match.state !== "filing") continue;
      if (!sessions.has(date)) sessions.set(date, []);
      sessions.get(date).push({id: row.id, value: match.value, source: match.source});
    }
  }
  return new Map([...sessions].sort(([a], [b]) => b.localeCompare(a)));
}

function matchScenarioShares(id, date, published, personalShares) {
  const csv = personalShares.get(id + ":" + date);
  const filings = Array.isArray(published) ? published : [published];
  const exactCounts = new Set(filings.filter(share => share?.as_of === date && !share.rounded &&
    Number.isSafeInteger(share.value) && share.value > 0).map(share => share.value));
  if (exactCounts.size > 1) return {value: null, state: "conflict"};
  const exact = exactCounts.values().next().value;
  if (exact !== undefined && csv !== undefined && exact !== csv) return {value: null, state: "conflict"};
  if (exact !== undefined) return {value: exact, state: "filing",
    source: filings.find(share => share?.as_of === date && !share.rounded && share.value === exact)?.source};
  if (csv !== undefined) return {value: csv, state: "csv"};
  return {value: null, state: "missing"};
}

function calculateMarketScenario(finance, {date, price, shares}) {
  if (finance.share_classes) throw Error("クラス別株式の評価が必要");
  return calculateWithAnnualPeriod(finance.currency, compareAnnual(finance).at(-1), {date, price, shares});
}

function calculateWithAnnualPeriod(currency, last, {date, price, shares}) {
  if (!isMarketDate(date) || date < last.end ||
      !Number.isFinite(price) || price <= 0 || !Number.isSafeInteger(shares) || shares <= 0) {
    throw Error("決算期末以降の基準日、正の株価と株数を入力して");
  }
  const cap = price * shares;
  if (!Number.isFinite(cap) || cap > Number.MAX_SAFE_INTEGER) throw Error("時価総額の計算範囲を超えている");
  return {
    cap, per: last.net_income > 0 ? cap / last.net_income : null,
    pbr: last.parent_equity > 0 ? cap / last.parent_equity : null,
    currency, periodEnd: last.end,
  };
}

function describeClassQuotes(row, quote, quotes, history) {
  const missing = [];
  const unlisted = [];
  for (const share of row.financials.share_classes.classes) {
    if (!share.symbol) {
      unlisted.push(share.label);
      continue;
    }
    const id = row.market + ":" + share.symbol;
    const observation = history?.get(id + ":" + quote.date) ?? quotes.get(id);
    if (observation?.date !== quote.date || observation.currency !== quote.currency) missing.push(share.symbol);
  }

  const notes = [];
  if (missing.length) notes.push("同日の終値なし " + missing.join("・"));
  if (unlisted.length) notes.push("上場ティッカーなし クラス" + unlisted.join("・クラス"));
  return notes.length ? notes.join("／") : "上場クラスの終値はそろっている。クラス別評価が必要";
}

function matchListedClassValue(row, id, quote) {
  const updated = row.quarterly;
  const annual = row.financials;
  const observations = [
    {cover: updated?.share_classes, source: updated?.source},
    {cover: annual.share_classes, source: annual.filing_url},
  ];
  const exact = observations.flatMap(({cover, source}) => {
    if (cover?.as_of !== quote.date || cover.rounded !== false || !source) return [];
    const share = cover.classes.find(item => item.symbol && row.market + ":" + item.symbol === id);
    return share && Number.isSafeInteger(share.value) && share.value > 0 ?
      [{shares: share.value, shareSource: source}] : [];
  });
  if (new Set(exact.map(item => item.shares)).size > 1) return {note: "クラス別開示株数が不一致"};
  if (!exact.length) return {note: "同日の正確なクラス別開示株数なし"};
  const match = exact[0];
  const classValue = quote.price * match.shares;
  if (!Number.isFinite(classValue) || classValue <= 0 || classValue > Number.MAX_SAFE_INTEGER) {
    return {note: "クラス別参考時価の計算範囲外"};
  }
  return {...match, classValue};
}

function evaluatePersonalQuotes(rows, quotes, shares, shareReview, history) {
  const issuers = new Map(rows.map(row => [row.id, row]));
  for (const row of rows) {
    for (const share of row.financials?.share_classes?.classes || []) {
      const classId = row.market + ":" + share.symbol;
      if (share.symbol && !issuers.has(classId)) issuers.set(classId, row);
    }
  }
  return Array.from(quotes, ([id, quote]) => {
    const row = issuers.get(id);
    const entry = {id, label: row?.label || id, quote};
    if (!row) return {...entry, state: "unknown"};
    const finance = row.financials;
    let latest;
    try {
      latest = finance ? compareAnnual(finance).at(-1) : sgxValuationFinance(row);
    } catch {
      return {...entry, state: "invalid"};
    }
    const metrics = finance ? latest : latest && row.sgxAnnual;
    if (metrics) {
      entry.financialPeriodEnd = latest.end;
      entry.salesGrowth = metrics.salesGrowth;
      entry.equityRatio = metrics.equityRatio;
      entry.financeSource = finance?.filing_url || finance?.source || latest.source;
    }
    if (finance?.share_classes) {
      if (quote.currency !== finance.currency || !isMarketDate(quote.date) ||
          !Number.isFinite(quote.price) || quote.price <= 0) return {...entry, state: "incompatible"};
      const {note, ...listedClass} = matchListedClassValue(row, id, quote);
      const detail = [describeClassQuotes(row, quote, quotes, history), note].filter(Boolean).join("／");
      return {...entry, state: "shareClasses", detail, ...listedClass};
    }
    if (!latest) return {...entry, state: "noFinance"};
    const currency = finance?.currency || latest.currency;
    const periodEnd = latest.end;
    if (quote.currency !== currency || quote.date < periodEnd) {
      return {...entry, state: "incompatible"};
    }
    const match = matchScenarioShares(id, quote.date, filingSharesOn(row, quote.date, shareReview), shares);
    if (match.value === null) return {...entry, state: match.state};
    try {
      const inputs = {...quote, shares: match.value};
      const result = calculateWithAnnualPeriod(currency, latest, inputs);
      return {...entry, state: match.state, shares: match.value, shareSource: match.source,
        result};
    } catch {
      return {...entry, state: "invalid"};
    }
  });
}

function screenPersonalBatch(rows, {market, limits, minimums = {}, order}) {
  const visible = rows.filter(row => {
    if (market && !row.id.startsWith(market + ":")) return false;
    return Object.entries(limits).every(([metric, max]) => {
      const value = row.result?.[metric];
      return max === null || (Number.isFinite(value) && value <= max);
    }) && Object.entries(minimums).every(([metric, min]) =>
      min === null || (Number.isFinite(row[metric]) && row[metric] >= min));
  });
  if (order) visible.sort((a, b) => {
    const left = a.result?.[order];
    const right = b.result?.[order];
    if (!Number.isFinite(left)) return Number.isFinite(right) ? 1 : 0;
    return Number.isFinite(right) ? left - right : -1;
  });
  return visible;
}

const annualScreenMetrics = ["salesGrowth", "operatingMargin", "equityRatio"];

function annualScreenRows(rows) {
  const results = [];
  for (const row of rows) {
    let financial = row.sgxAnnual;
    if (row.financials) {
      try {
        financial = {...compareAnnual(row.financials).at(-1), source: row.financials.filing_url || row.financials.source,
          sourceLabel: "年次財務資料"};
      } catch {
        continue;
      }
    }
    if (financial) results.push({...financial, id: row.id, label: row.label, market: row.market});
  }
  return results;
}

function screenAnnualFinancials(rows, {market, minimums, order}) {
  const visible = rows.filter(row => (!market || row.market === market) &&
    annualScreenMetrics.every(metric => minimums[metric] == null ||
      (Number.isFinite(row[metric]) && row[metric] >= minimums[metric] / 100)));
  if (annualScreenMetrics.includes(order)) {
    visible.sort((a, b) => (b[order] ?? -Infinity) - (a[order] ?? -Infinity));
  }
  return visible;
}

function csvCell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "";
  let text = String(value);
  if (/^[\s\uFEFF]*[=+@-]|^[\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}

function annualScreenCsv(rows) {
  const header = "market_id,company,fiscal_period,annual_sales_growth_pct,annual_operating_margin_pct,annual_parent_equity_ratio_pct,financial_source,source_label";
  const lines = rows.map(row => [row.id, row.label, row.end,
    ...annualScreenMetrics.map(metric => Number.isFinite(row[metric]) ? row[metric] * 100 : null),
    row.source, row.sourceLabel].map(csvCell).join(","));
  return "\uFEFF" + [header, ...lines].join("\r\n") + "\r\n";
}

function saveResearchCsv(content, filename) {
  const url = URL.createObjectURL(new Blob([content], {type: "text/csv;charset=utf-8"}));
  const anchor = Object.assign(document.createElement("a"), {href: url, download: filename});
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function personalBatchCsv(results) {
  const headers = ["market_id", "company", "date", "currency", "close", "shares_excluding_treasury",
    "estimated_market_cap", "estimated_per", "estimated_pbr", "financial_period_end",
    "match_status", "financial_source", "share_source", "match_detail", "estimated_listed_class_value", "annual_sales_growth_pct", "annual_parent_equity_ratio_pct"];
  const lines = results.map(row => [row.id, row.label, row.quote.date, row.quote.currency, row.quote.price,
    row.shares, row.result?.cap, row.result?.per, row.result?.pbr, row.financialPeriodEnd,
    row.state, row.financeSource, row.shareSource, row.detail, row.classValue,
    Number.isFinite(row.salesGrowth) ? row.salesGrowth * 100 : null,
    Number.isFinite(row.equityRatio) ? row.equityRatio * 100 : null].map(csvCell).join(","));
  return "\uFEFF" + [headers.join(","), ...lines].join("\r\n") + "\r\n";
}

async function initMarketResearch() {
  const byId = id => document.getElementById(id);
  const filter = byId("marketFilter"), query = byId("marketQuery");
  const status = byId("marketCount"), body = byId("marketRows");
  const panel = byId("marketDetails");
  const scenario = byId("marketScenario");
  const scenarioResult = byId("marketScenarioResult");
  const selected = new Map();
  let selectedFinance;
  let marketRows = [];
  let batchResults = [];
  let shareReview;
  let activeRow;
  let personalQuotes = new Map();
  let personalQuoteHistory = new Map();
  let personalShares = new Map();
  let importedClose = false;
  let importedShares = false;
  const dateInput = byId("scenarioDate");
  const priceInput = byId("scenarioPrice");
  const sharesInput = byId("scenarioShares");
  const clearImportedShares = () => {
    if (importedShares) sharesInput.value = "";
    importedShares = false;
  };
  const clearImportedClose = () => {
    if (importedClose) priceInput.value = "";
    importedClose = false;
  };
  const element = (tag, value) => Object.assign(document.createElement(tag), {textContent: value});
  const link = (url, label) => {
    if (!url.startsWith("https://") && !["./sgx-32-research.html", "./index.html"].includes(url) && !/^\.\/index\.html#issuer=[A-Z0-9]{1,8}$/.test(url)) throw Error("出典URLが不明");
    return Object.assign(element("a", label), {href: url});
  };
  const pct = value => value === null ? "—" : percent.format(value);
  const compareInput = (row, labelText) => {
    const input = Object.assign(element("input", ""), {type: "checkbox", checked: selected.has(row.id)});
    input.dataset.marketId = row.id;
    input.setAttribute("aria-label", row.label + labelText);
    input.addEventListener("change", () => {
      if (input.checked) selected.set(row.id, row);
      else selected.delete(row.id);
      paintComparison();
    });
    return input;
  };
  const paintComparison = () => {
    for (const input of document.querySelectorAll("input[data-market-id]")) {
      input.checked = selected.has(input.dataset.marketId);
    }
    byId("marketCompareEmpty").hidden = selected.size > 0;
    byId("marketCompareTable").hidden = selected.size === 0;
    byId("marketCompareRows").replaceChildren(...[...selected.values()].map(row => {
      const finance = row.financials;
      const p = row.sgxAnnual || {...compareAnnual(finance).at(-1), currency: finance.currency,
        source: finance.source, sourceLabel: "財務出典"};
      const tr = document.createElement("tr");
      const values = [row.label + "（" + row.symbol + "）", p.end, p.currency, money.format(p.revenue),
        pct(p.salesGrowth), pct(p.operatingMargin), pct(p.equityRatio)];
      const remove = Object.assign(element("button", "外す"), {type: "button", className: "secondary-button"});
      remove.setAttribute("aria-label", row.label + "を比較から外す");
      remove.addEventListener("click", () => {
        selected.delete(row.id);
        paintComparison();
      });
      const action = element("td", "");
      action.append(remove);
      const source = element("td", "");
      source.append(link(p.source, p.sourceLabel));
      tr.append(...values.map(v => element("td", v)), source, action);
      return tr;
    }));
  };
  const shareLabels = {
    filing: "同日の株数あり（掲載資料）",
    csv: "同日の株数あり（株数CSV）",
    conflict: "株数資料間で不一致。原資料を照合してから入力",
    missing: "同日の株数が未取得",
  };
  const multiple = value => value === null ? "—" : value.toFixed(2) + "倍";
  const batchLabels = {...shareLabels, shareClasses: "株式クラスごとの評価が必要", unknown: "銘柄が調査一覧に未登録", noFinance: "一括試算用の年次財務が未接続",
    incompatible: "株価の日付・通貨が年次財務と不整合", invalid: "計算範囲または財務データを要確認"};
  const batchMarket = byId("personalBatchMarket"), maxPer = byId("personalBatchMaxPer");
  const maxPbr = byId("personalBatchMaxPbr"), batchOrder = byId("personalBatchOrder");
  const minSales = byId("personalBatchMinSales"), minEquity = byId("personalBatchMinEquity");
  const paintBatch = () => {
    const batchDate = byId("personalBatchDate");
    batchDate.disabled = !personalQuoteHistory.size;
    const quotes = batchDate.value ? selectQuoteDate(personalQuoteHistory, batchDate.value) : personalQuotes;
    const results = evaluatePersonalQuotes(marketRows, quotes, personalShares, shareReview, personalQuoteHistory);
    const statusFilter = byId("personalBatchFilter");
    statusFilter.disabled = results.length === 0;
    const hasClassValue = row => row.classValue !== undefined;
    const matches = {
      all: () => true,
      company: row => Boolean(row.result),
      class: hasClassValue,
      unresolved: row => !row.result && !hasClassValue(row),
    };
    for (const control of [batchMarket, maxPer, maxPbr, batchOrder, minSales, minEquity]) control.disabled = !results.length;
    const invalidLimit = results.length && (!maxPer.validity.valid || !maxPbr.validity.valid);
    const limits = {per: maxPer.value ? maxPer.valueAsNumber : null, pbr: maxPbr.value ? maxPbr.valueAsNumber : null};
    const invalidMinimum = results.length && (!minSales.validity.valid || !minEquity.validity.valid);
    const minimums = {salesGrowth: minSales.value ? minSales.valueAsNumber / 100 : null,
      equityRatio: minEquity.value ? minEquity.valueAsNumber / 100 : null};
    batchResults = invalidLimit || invalidMinimum ? [] : screenPersonalBatch(results.filter(matches[statusFilter.value]),
      {market: batchMarket.value, limits, minimums, order: batchOrder.value});
    byId("personalBatchDownload").disabled = batchResults.length === 0;
    byId("personalBatchTable").hidden = batchResults.length === 0;
    byId("personalBatchStatus").textContent = results.length ? results.filter(row => row.result).length +
      " / " + results.length + "件を試算" : batchDate.value && personalQuoteHistory.size ? "指定日の終値がCSVにない" : "";
    const classCount = results.filter(hasClassValue).length;
    if (classCount) byId("personalBatchStatus").append("・上場クラス別の参考時価 " + classCount + "件");
    if (invalidLimit) byId("personalBatchStatus").append("・PERとPBRの上限は0以上の数値を入力");
    if (invalidMinimum) byId("personalBatchStatus").append("・下限には数値を入力");
    if (results.length && (minSales.value || minEquity.value || invalidMinimum || statusFilter.value !== "all" || batchMarket.value || maxPer.value || maxPbr.value || invalidLimit)) {
      byId("personalBatchStatus").append("・表示 " + batchResults.length + "件");
    }
    byId("personalBatchRows").replaceChildren(...batchResults.map(row => {
      const {result, quote} = row;
      const values = [row.id === row.label ? row.id : row.label + "（" + row.id + "）",
        quote.date, quote.currency, money.format(quote.price), row.shares ? money.format(row.shares) : "—",
        result ? money.format(result.cap) : "—", result ? multiple(result.per) : "—",
        result ? multiple(result.pbr) : "—", row.financialPeriodEnd || "—", row.detail || batchLabels[row.state],
        row.classValue === undefined ? "—" : money.format(row.classValue),
        pct(row.salesGrowth ?? null), pct(row.equityRatio ?? null)];
      const tr = document.createElement("tr");
      tr.append(...values.map(value => element("td", value)));
      const sourceCell = element("td", "");
      if (row.financeSource?.startsWith("https://")) sourceCell.append(link(row.financeSource, "財務資料"));
      if (row.shareSource?.startsWith("https://")) sourceCell.append(" ", link(row.shareSource, "株数資料"));
      tr.append(sourceCell);
      return tr;
    }));
  };
  byId("personalBatchDate").addEventListener("input", paintBatch);
  byId("personalBatchFilter").addEventListener("change", paintBatch);
  batchMarket.addEventListener("change", paintBatch);
  batchOrder.addEventListener("change", paintBatch);
  maxPer.addEventListener("input", paintBatch);
  maxPbr.addEventListener("input", paintBatch);
  minSales.addEventListener("input", paintBatch);
  minEquity.addEventListener("input", paintBatch);
  byId("personalBatchDownload").addEventListener("click", () => {
    if (!batchResults.length) return;
    saveResearchCsv(personalBatchCsv(batchResults), "value-hunter-trial-valuations.csv");
  });
  const applyPersonalQuote = () => {
    const quote = personalQuotes.get(activeRow.id);
    const lastEnd = byId("scenarioDate").min;
    const eligible = !selectedFinance.share_classes && quote && quote.currency === selectedFinance.currency && quote.date >= lastEnd;
    byId("activatePersonalQuote").disabled = !eligible;
    const match = eligible && matchScenarioShares(activeRow.id, quote.date, filingSharesOn(activeRow, quote.date), personalShares);
    byId("personalQuoteMatch").textContent = eligible ? "CSV終値 " + money.format(quote.price) +
      " " + quote.currency + "（" + quote.date + "）。" + shareLabels[match.state] : "";
  };
  byId("activatePersonalQuote").addEventListener("click", () => {
    const {date, price} = personalQuotes.get(activeRow.id);
    const shares = matchScenarioShares(activeRow.id, date, filingSharesOn(activeRow, date), personalShares);
    dateInput.value = date;
    priceInput.value = price;
    sharesInput.value = shares.value ?? "";
    importedClose = true;
    importedShares = shares.value !== null;
    scenarioResult.textContent = "";
  });
  const bindCsv = (fileId, statusId, read, save, label, clear) => {
    let sequence = 0;
    byId(fileId).addEventListener("change", async event => {
      const readId = ++sequence;
      const file = event.target.files[0];
      const message = byId(statusId);
      save(new Map());
      paintBatch();
      clear();
      scenarioResult.textContent = "";
      message.textContent = "";
      if (activeRow) applyPersonalQuote();
      try {
        if (!file) return;
        if (file.size > 1000000) throw Error("CSVは1 MB以下で読み込んで");
        const csv = await file.text();
        if (readId !== sequence) return;
        const rows = read(csv);
        save(rows);
        paintBatch();
        message.textContent = label + rows.size + "件読み込んだ";
        if (activeRow) applyPersonalQuote();
      } catch (error) {
        if (readId === sequence) message.textContent = error.message;
      }
    });
  };
  bindCsv("personalQuoteFile", "personalQuoteStatus", readQuoteHistory, rows => {
    personalQuoteHistory = rows;
    personalQuotes = selectQuoteDate(rows);
  }, "終値を ", clearImportedClose);
  bindCsv("personalShareFile", "personalShareStatus", readPersonalShares, rows => { personalShares = rows; }, "株数を ", clearImportedShares);
  const formatShareClasses = cover => "普通株式数（" + cover.as_of + "時点） " + cover.classes.map(item =>
        "クラス" + item.label + (item.symbol ? "（" + item.symbol + "）" : "") + " " +
        (cover.rounded ? "約" : "") + money.format(item.value) + "株").join(" / ");
  const show = row => {
    const finance = row.financials;
    const periods = compareAnnual(finance);
    byId("marketDetailTitle").textContent = row.label + "（" + row.symbol + "）";
    byId("marketDetailCurrency").textContent = [finance.currency, finance.basis, "連結年次", finance.document_label]
      .filter(Boolean).join("・");
    byId("marketFinancialRows").replaceChildren(...periods.map(p => {
      const tr = document.createElement("tr");
      const values = [p.end, money.format(p.revenue), p.operating_income === null ? "—" : money.format(p.operating_income), money.format(p.net_income),
        pct(p.salesGrowth), pct(p.operatingGrowth), pct(p.operatingMargin), pct(p.equityRatio)];
      tr.append(...values.map(value => element("td", value)));
      return tr;
    }));
    const shareClasses = finance.share_classes;
    byId("marketShareCount").textContent = shareClasses
      ? formatShareClasses(shareClasses)
      : "発行済普通株式（自己株式控除後） " + (finance.shares.rounded ? "約" : "") +
        money.format(finance.shares.value) + " 株（" + finance.shares.as_of + "時点）";
    scenario.hidden = Boolean(shareClasses);
    byId("marketScenarioHelp").hidden = Boolean(shareClasses);
    byId("marketClassValuation").hidden = !shareClasses;
    const sources = byId("marketFinancialSources");
    sources.replaceChildren(link(finance.source, "財務データの出典"));
    if (finance.filing_url) sources.append(" · ", link(finance.filing_url, "SEC提出書類"));
    const quarter = row.quarterly;
    const quarterSection = byId("marketQuarterly");
    quarterSection.hidden = true;
    if (quarter) {
      const [prior, current] = quarter.periods;
      const cumulative = quarter.scope === "cumulative";
      byId("marketQuarterlyTitle").textContent = cumulative ? "直近の累計決算（年初から）" : "直近に確認した四半期実績";
      const quarterRows = [prior, current].map((period, index) => {
        const tr = document.createElement("tr");
        const values = [cumulative ? period.start + "〜" + period.end : period.end, money.format(period.revenue), period.operating_income === null ? "—" : money.format(period.operating_income),
          money.format(period.net_income), pct(index ? annualGrowth(prior.revenue, current.revenue) : null),
          pct(index ? annualGrowth(prior.operating_income, current.operating_income) : null)];
        tr.append(...values.map(value => element("td", value)));
        return tr;
      });
      byId("marketQuarterlyRows").replaceChildren(...quarterRows);
      byId("marketQuarterlySource").replaceChildren(quarter.currency + "・提出日 " + quarter.filed + "・",
        link(quarter.source, cumulative ? quarter.form : "SEC Form " + quarter.form));
      const interimShares = byId("marketInterimShareCount");
      interimShares.hidden = !(quarter.shares || quarter.share_classes);
      if (quarter.share_classes) interimShares.textContent = formatShareClasses(quarter.share_classes);
      else if (quarter.shares) interimShares.textContent = "開示時点の普通株式数（自己株式控除後） " + (quarter.shares.rounded ? "約" : "") +
        money.format(quarter.shares.value) + " 株（" + quarter.shares.as_of + "時点）";
      quarterSection.hidden = false;
    }
    selectedFinance = finance;
    activeRow = row;
    scenario.reset();
    importedClose = false;
    importedShares = false;
    scenarioResult.textContent = "";
    byId("scenarioCurrency").textContent = finance.currency;
    byId("scenarioDate").min = periods.at(-1).end;
    applyPersonalQuote();
    panel.hidden = false;
  };
  dateInput.addEventListener("input", () => {
    clearImportedClose();
    clearImportedShares();
  });
  priceInput.addEventListener("input", () => { importedClose = false; });
  sharesInput.addEventListener("input", () => { importedShares = false; });
  scenario.addEventListener("input", () => { scenarioResult.textContent = ""; });
  scenario.addEventListener("submit", event => {
    event.preventDefault();
    try {
      const result = calculateMarketScenario(selectedFinance, {
        date: byId("scenarioDate").value,
        price: byId("scenarioPrice").valueAsNumber,
        shares: byId("scenarioShares").valueAsNumber,
      });
      scenarioResult.textContent = "参考時価総額 " + money.format(result.cap) + " " + result.currency +
        "、PER " + multiple(result.per) + "、PBR " + multiple(result.pbr) +
        "。財務基準日 " + result.periodEnd + "。";
    } catch (error) {
      scenarioResult.textContent = error.message;
    }
  });
  try {
    const load = async file => {
      const response = await fetch("./data/" + file, {cache: "no-store"});
      if (!response.ok) throw Error("資料取得 HTTP " + response.status);
      return response.json();
    };
    const [research, sgx, g13, s63, s63ShareReview] = await Promise.all([
      load("market-research-v315.json"), load("latest.json"),
      load("sgx-g13-2026q3-v121.json").catch(() => null),
      load("sgx-s63-9m2026-v125.json").catch(() => null),
      load("sgx-s63-two-website-close-v129.json").catch(() => null),
    ]);
    const updateRows = [];
    const genting = g13?.record;
    if (genting?.status === "SGX_PRIMARY_2026Q3_UNAUDITED_BUSINESS_UPDATE" &&
        Number.isFinite(genting.revenue_2026q3_sgd_thousands) &&
        Number.isFinite(genting.net_profit_after_tax_2026q3_sgd_thousands)) {
      updateRows.push(["Genting Singapore（G13）", "3か月・" + genting.quarter_end_date,
        money.format(genting.revenue_2026q3_sgd_thousands * 1000), pct(genting.revenue_yoy_pct / 100),
        money.format(genting.net_profit_after_tax_2026q3_sgd_thousands * 1000), genting.source_url, "業績速報（未監査）"]);
    }
    const st = s63?.record;
    if (st?.status === "SGX_S63_OFFICIAL_NINE_MONTH_2026_PRESENTATION" &&
        Number.isFinite(st.nine_month_revenue_sgd_billion_rounded)) {
      updateRows.push(["ST Engineering（S63）", "9か月累計・" + st.period_end_date,
        "約" + money.format(st.nine_month_revenue_sgd_billion_rounded * 1e9), pct(st.nine_month_reported_revenue_yoy_pct / 100),
        "—", st.source_url, "事業更新資料"]);
    }
    byId("sgxBusinessRows").replaceChildren(...updateRows.map(row => {
      const tr = document.createElement("tr");
      const source = element("td", "");
      source.append(link(row[5], row[6]));
      tr.append(...row.slice(0, 5).map(value => element("td", value)), source);
      return tr;
    }));
    byId("sgxBusinessUpdates").hidden = updateRows.length === 0;
    const rows = buildMarketRows(research, sgx);
    const annualRows = annualScreenRows(rows);
    const marketRowsById = new Map(rows.map(row => [row.id, row]));
    const annualForm = byId("annualScreenForm");
    const annualFields = ["market", ...annualScreenMetrics, "order"];
    const annualLink = byId("annualScreenLink");
    const applyAnnualLink = () => {
      const params = new URLSearchParams(window.location.hash.slice(1));
      for (const key of annualFields) {
        const field = annualForm.elements.namedItem(key);
        const value = params.get(key) || "";
        if (field instanceof HTMLSelectElement) {
          field.value = [...field.options].some(option => option.value === value) ? value : "";
        } else {
          field.value = /^-?(?:\d+(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value) && Number.isFinite(Number(value)) ? value : "";
        }
      }
    };
    applyAnnualLink();
    const annualButton = byId("annualScreenDownload");
    let visibleAnnual = [];
    const paintAnnual = () => {
      const minimums = Object.fromEntries(annualScreenMetrics.map(metric => {
        const field = annualForm.elements.namedItem(metric);
        return [metric, field.value === "" ? null : field.valueAsNumber];
      }));
      const params = new URLSearchParams();
      for (const key of annualFields) {
        const field = annualForm.elements.namedItem(key);
        if (field.value && field.validity.valid) params.set(key, field.value);
      }
      annualLink.href = "#" + params.toString();
      const valid = annualForm.checkValidity();
      visibleAnnual = valid ? screenAnnualFinancials(annualRows, {
        market: annualForm.elements.namedItem("market").value, minimums,
        order: annualForm.elements.namedItem("order").value,
      }) : [];
      byId("annualScreenStatus").textContent = valid ?
        visibleAnnual.length + " / " + annualRows.length + "件" : "下限に数値を入力して";
      annualButton.disabled = visibleAnnual.length === 0;
      byId("annualScreenTable").hidden = !visibleAnnual.length;
      byId("annualScreenRows").replaceChildren(...visibleAnnual.map(row => {
        const tr = document.createElement("tr");
        const source = element("td", "");
        source.append(link(row.source, row.sourceLabel));
        const selection = element("td", "");
        selection.append(compareInput(marketRowsById.get(row.id), "を年次財務の表から比較"));
        tr.append(...[row.label + "（" + row.id + "）", row.end,
          ...annualScreenMetrics.map(metric => pct(row[metric] ?? null))].map(value => element("td", value)), source, selection);
        return tr;
      }));
    };
    window.addEventListener("hashchange", () => {
      applyAnnualLink();
      paintAnnual();
    });
    annualForm.addEventListener("input", paintAnnual);
    annualForm.addEventListener("reset", () => setTimeout(paintAnnual, 0));
    annualForm.addEventListener("submit", event => event.preventDefault());
    annualLink.addEventListener("click", event => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      window.location.hash = annualLink.hash;
      const address = byId("annualScreenAddress");
      address.value = window.location.href;
      address.hidden = false;
      address.focus();
      address.select();
    });
    annualForm.addEventListener("input", () => { byId("annualScreenAddress").hidden = true; });
    annualForm.addEventListener("reset", () => {
      byId("annualScreenAddress").hidden = true;
      if (window.location.hash) window.location.hash = "";
    });
    annualButton.addEventListener("click", () => {
      if (visibleAnnual.length) saveResearchCsv(annualScreenCsv(visibleAnnual), "value-hunter-annual-screen.csv");
    });
    paintAnnual();
    marketRows = rows;
    shareReview = s63ShareReview;
    const shareDates = byId("publishedShareDate");
    const shareItems = byId("publishedShareItems");
    const sessions = publishedShareSessions(rows, shareReview);
    shareDates.append(...[...sessions].map(([date, records]) =>
      Object.assign(element("option", date + "（" + records.length + "銘柄）"), {value: date})));
    shareDates.disabled = !sessions.size;
    shareDates.addEventListener("change", () => {
      const records = sessions.get(shareDates.value) || [];
      shareItems.replaceChildren(...records.map(row => {
        const item = element("li", row.id + " " + money.format(row.value) + "株 ");
        item.append(link(row.source, "株数資料"));
        return item;
      }));
    });
    const shareExport = byId("publishedShareExport");
    const refreshShareExport = () => { shareExport.disabled = !(sessions.get(shareDates.value) || []).length; };
    shareDates.addEventListener("change", refreshShareExport);
    shareExport.addEventListener("click", () => {
      const records = sessions.get(shareDates.value) || [];
      if (!records.length) return;

      const csv = ["market_id,date,shares_excluding_treasury,filing_source_url",
        ...records.map(record => [record.id, shareDates.value, String(record.value), record.source].map(csvCell).join(","))].join("\r\n");
      saveResearchCsv(csv, "value-hunter-published-shares-" + shareDates.value + ".csv");
    });
    paintBatch();
    byId("marketCoverageRows").replaceChildren(...summarizeMarketCoverage(rows).map(row => {
      const tr = document.createElement("tr");
      const name = element("th", row.label);
      name.scope = "row";
      tr.append(name, ...[row.listed, row.comparable, row.quarterly, row.rankable].map(value => element("td", value)));
      return tr;
    }));
    const paint = () => {
      panel.hidden = true;
      const visible = filterMarketRows(rows, filter.value, query.value, byId("financialFilter").value);
      status.textContent = visible.length + " / " + rows.length + "件。日本・米国は選定銘柄。正式順位の対象条件は銘柄ごとに表示。";
      body.replaceChildren(...visible.map(row => {
        const tr = document.createElement("tr");
        tr.append(...[marketLabels[row.market], row.symbol, row.label].map(v => element("td", v)));
        const finance = element("td", "");
        if (row.financials) {
          const button = Object.assign(element("button", "財務を見る"), {type: "button", className: "secondary-button"});
          button.addEventListener("click", () => show(row));
          finance.append(button);
        } else if (row.market === "SG") finance.append(link("./index.html", "SGX財務画面"));
        else finance.textContent = "財務取り込み待ち";
        if (row.financials || row.sgxAnnual) {
          const compare = compareInput(row, "を比較");
          const label = element("label", "");
          label.append(compare, " 比較");
          finance.append(" ", label);
        }
        const source = element("td", "");
        source.append(link(row.identity_source, row.market === "SG" ? "SGX調査" : "銘柄資料"));
        const evidence = rankingEvidence(row, s63ShareReview);
        const ranking = element("td", "");
        const detail = element("details", "");
        detail.append(element("summary", row.rankingEligible ? "対象" : "対象外の理由"));
        for (const [label, value, url] of [["株価", evidence.quote, evidence.quoteSource],
          [row.market === "SG" ? "掲載株数の基準日" : "株数", evidence.share, evidence.shareSource]]) {
          const line = element("div", label + " " + value);
          if (url?.startsWith("https://")) line.append(" ", link(url, label + "出典"));
          detail.append(line);
        }
        if (evidence.supplementalShare) {
          const {date, value, source} = evidence.supplementalShare;
          const line = element("div", "別資料の同日株数 " + date + "・" + money.format(value) + "株 ");
          line.append(link(source, "SGX自己株式取得報告"));
          detail.append(line);
        }
        if (evidence.reasons.length) {
          const list = element("ul", "");
          list.append(...evidence.reasons.map(reason => element("li", reason)));
          detail.append(list);
        }
        if (row.market === "SG" && /^[A-Z0-9]{1,8}$/.test(row.symbol)) {
          detail.append(link("./index.html#issuer=" + row.symbol, "SGXの全除外理由"));
        }
        ranking.append(detail);
        tr.append(finance, source, ranking);
        return tr;
      }));
      paintComparison();
    };
    filter.addEventListener("change", paint);
    byId("financialFilter").addEventListener("change", paint);
    query.addEventListener("input", paint);
    paint();
  } catch (error) {
    status.textContent = "銘柄資料を照合できない（" + error.message + "）";
    byId("annualScreenStatus").textContent = "財務資料を読み込めない";
  }
}

if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", initMarketResearch);
if (typeof module !== "undefined") module.exports = {buildMarketRows, filterMarketRows, compareAnnual, calculateMarketScenario, readPersonalQuotes, readPersonalShares, matchScenarioShares, rankingEvidence, summarizeMarketCoverage, evaluatePersonalQuotes, personalBatchCsv, screenPersonalBatch, annualScreenRows, screenAnnualFinancials, annualScreenCsv, publishedShareSessions, readQuoteHistory, selectQuoteDate};
