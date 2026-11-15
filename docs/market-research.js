"use strict";

const marketLabels = {JP: "日本", US: "米国", SG: "シンガポール"};
const money = new Intl.NumberFormat("ja-JP");
const percent = new Intl.NumberFormat("ja-JP", {style: "percent", maximumFractionDigits: 1});

function annualGrowth(previous, current) {
  return previous > 0 ? (current - previous) / previous : null;
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

function rankingEvidence(row) {
  const sgx = row.sgxEvidence;
  const finance = row.financials;
  const shares = row.quarterly?.shares || finance?.shares;
  if (!sgx) {
    return {
      quote: "未接続",
      share: shares ? shares.as_of + (shares.rounded ? "（概数）" : "（開示資料）") : "未取得",
      shareSource: row.quarterly?.shares ? row.quarterly.source : finance?.filing_url || finance?.source,
      reasons: [finance ? "正式順位の財務審査が未実装" : "年次財務が未取得",
        "公開用の株価データが未接続", "株価と株数の同日照合が未完了"],
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
  if (shareDate && quoteDate && shareDate !== quoteDate) reasons.push("株価と株数の基準日が異なる");
  return {
    quote: observed ? quoteDate + (sgx.quote_source_type === "YAHOO_FINANCE_UNOFFICIAL_CHART" ? "（参考）" : "（掲載資料）") : "未取得",
    quoteSource: observed ? sgx.quote_url : null,
    share: shareDate || "未取得",
    shareSource: shareDate ? sgx.shares_source_url : null,
    reasons,
  };
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
      rankable: listed.filter(row => row.rankingEligible === true).length,
    };
  });
}

function filterMarketRows(rows, market, query) {
  const term = query.trim().normalize("NFKC").toUpperCase();
  return rows.filter(row => (!market || row.market === market) &&
    [row.id, row.symbol, row.label, row.name].some(value =>
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
      [row.revenue, row.operating_income, row.net_income, row.assets, row.parent_equity].every(Number.isSafeInteger) &&
      row.revenue > 0 && row.assets > 0;
  }) || days(prior.end, latest.start) !== 2) throw Error("連続した年間決算を照合できない");
  return finance.periods.map((row, i) => ({
    ...row,
    salesGrowth: i ? annualGrowth(prior.revenue, latest.revenue) : null,
    operatingGrowth: i ? annualGrowth(prior.operating_income, latest.operating_income) : null,
    operatingMargin: row.operating_income / row.revenue,
    equityRatio: row.parent_equity / row.assets,
  }));
}

function isMarketDate(date) {
  const parsed = new Date(date + "T00:00:00Z");
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === date;
}

function readPersonalQuotes(csv) {
  const lines = csv.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.shift() !== "market_id,date,currency,close") {
    throw Error("CSVの見出しは market_id,date,currency,close");
  }
  const currencies = {JP: "JPY", US: "USD", SG: "SGD"};
  const quotes = new Map();
  const seen = new Set();
  for (const [index, line] of lines.entries()) {
    const [id, date, currency, close, extra] = line.split(",").map(value => value.trim());
    const price = Number(close);
    const key = id + ":" + date;
    if (extra !== undefined || !/^(JP|US|SG):[A-Z0-9.-]{1,12}$/.test(id) || !isMarketDate(date) ||
        currency !== currencies[id.slice(0, 2)] || !/^\d+(\.\d+)?$/.test(close) ||
        !Number.isFinite(price) || price <= 0 || seen.has(key)) {
      throw Error("CSVの " + (index + 2) + " 行目を確認して。銘柄、日付、通貨、終値、重複の有無が合っているか見て");
    }
    seen.add(key);
    if (!quotes.has(id) || date > quotes.get(id).date) quotes.set(id, {date, currency, price});
  }
  if (quotes.size === 0) throw Error("CSVに株価の行がない");
  return quotes;
}

function readPersonalShares(csv) {
  const lines = csv.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  if (lines.shift() !== "market_id,date,shares_excluding_treasury") {
    throw Error("CSVの見出しは market_id,date,shares_excluding_treasury");
  }
  const shares = new Map();
  for (const [index, line] of lines.entries()) {
    const [id, date, count, extra] = line.split(",").map(value => value.trim());
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

function matchScenarioShares(id, date, published, personalShares) {
  const csv = personalShares.get(id + ":" + date);
  const exact = published.as_of === date && !published.rounded ? published.value : undefined;
  if (exact !== undefined && csv !== undefined && exact !== csv) return {value: null, state: "conflict"};
  if (exact !== undefined) return {value: exact, state: "filing"};
  if (csv !== undefined) return {value: csv, state: "csv"};
  return {value: null, state: "missing"};
}

function calculateMarketScenario(finance, {date, price, shares}) {
  const last = compareAnnual(finance).at(-1);
  if (!isMarketDate(date) || date < last.end ||
      !Number.isFinite(price) || price <= 0 || !Number.isSafeInteger(shares) || shares <= 0) {
    throw Error("決算期末以降の基準日、正の株価と株数を入力して");
  }
  const cap = price * shares;
  if (!Number.isFinite(cap) || cap > Number.MAX_SAFE_INTEGER) throw Error("時価総額の計算範囲を超えている");
  return {
    cap, per: last.net_income > 0 ? cap / last.net_income : null,
    pbr: last.parent_equity > 0 ? cap / last.parent_equity : null,
    currency: finance.currency, periodEnd: last.end,
  };
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
  let activeRow;
  let personalQuotes = new Map();
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
  const paintComparison = () => {
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
        const checkbox = [...body.querySelectorAll("input[type=checkbox]")].find(x => x.dataset.marketId === row.id);
        if (checkbox) checkbox.checked = false;
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
    conflict: "株数CSVと掲載資料が不一致。原資料を照合してから入力",
    missing: "同日の株数が未取得",
  };
  const filingShares = date => {
    const interim = activeRow.quarterly?.shares;
    return interim?.as_of === date ? interim : selectedFinance.shares;
  };
  const applyPersonalQuote = () => {
    const quote = personalQuotes.get(activeRow.id);
    const lastEnd = byId("scenarioDate").min;
    const eligible = quote && quote.currency === selectedFinance.currency && quote.date >= lastEnd;
    byId("activatePersonalQuote").disabled = !eligible;
    const match = eligible && matchScenarioShares(activeRow.id, quote.date, filingShares(quote.date), personalShares);
    byId("personalQuoteMatch").textContent = eligible ? "CSV終値 " + money.format(quote.price) +
      " " + quote.currency + "（" + quote.date + "）。" + shareLabels[match.state] : "";
  };
  byId("activatePersonalQuote").addEventListener("click", () => {
    const {date, price} = personalQuotes.get(activeRow.id);
    const shares = matchScenarioShares(activeRow.id, date, filingShares(date), personalShares);
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
        message.textContent = label + rows.size + "件読み込んだ";
        if (activeRow) applyPersonalQuote();
      } catch (error) {
        if (readId === sequence) message.textContent = error.message;
      }
    });
  };
  bindCsv("personalQuoteFile", "personalQuoteStatus", readPersonalQuotes, rows => { personalQuotes = rows; }, "終値を ", clearImportedClose);
  bindCsv("personalShareFile", "personalShareStatus", readPersonalShares, rows => { personalShares = rows; }, "株数を ", clearImportedShares);
  const show = row => {
    const finance = row.financials;
    const periods = compareAnnual(finance);
    byId("marketDetailTitle").textContent = row.label + "（" + row.symbol + "）";
    byId("marketDetailCurrency").textContent = [finance.currency, finance.basis, "連結年次", finance.document_label]
      .filter(Boolean).join("・");
    byId("marketFinancialRows").replaceChildren(...periods.map(p => {
      const tr = document.createElement("tr");
      const values = [p.end, money.format(p.revenue), money.format(p.operating_income), money.format(p.net_income),
        pct(p.salesGrowth), pct(p.operatingGrowth), pct(p.operatingMargin), pct(p.equityRatio)];
      tr.append(...values.map(value => element("td", value)));
      return tr;
    }));
    byId("marketShareCount").textContent = "発行済普通株式（自己株式控除後） " + (finance.shares.rounded ? "約" : "") +
      money.format(finance.shares.value) + " 株（" + finance.shares.as_of + "時点）";
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
        const values = [cumulative ? period.start + "〜" + period.end : period.end, money.format(period.revenue), money.format(period.operating_income),
          money.format(period.net_income), pct(index ? annualGrowth(prior.revenue, current.revenue) : null),
          pct(index ? annualGrowth(prior.operating_income, current.operating_income) : null)];
        tr.append(...values.map(value => element("td", value)));
        return tr;
      });
      byId("marketQuarterlyRows").replaceChildren(...quarterRows);
      byId("marketQuarterlySource").replaceChildren(quarter.currency + "・提出日 " + quarter.filed + "・",
        link(quarter.source, cumulative ? quarter.form : "SEC Form " + quarter.form));
      const interimShares = byId("marketInterimShareCount");
      interimShares.hidden = !quarter.shares;
      if (quarter.shares) interimShares.textContent = "期末の普通株式数（自己株式控除後） " +
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
      const multiple = value => value === null ? "—" : value.toFixed(2) + "倍";
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
    const [research, sgx, g13, s63] = await Promise.all([
      load("market-research-v315.json"), load("latest.json"),
      load("sgx-g13-2026q3-v121.json").catch(() => null),
      load("sgx-s63-9m2026-v125.json").catch(() => null),
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
    byId("marketCoverageRows").replaceChildren(...summarizeMarketCoverage(rows).map(row => {
      const tr = document.createElement("tr");
      const name = element("th", row.label);
      name.scope = "row";
      tr.append(name, ...[row.listed, row.comparable, row.rankable].map(value => element("td", value)));
      return tr;
    }));
    const paint = () => {
      panel.hidden = true;
      const visible = filterMarketRows(rows, filter.value, query.value);
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
          const compare = Object.assign(element("input", ""), {type: "checkbox", checked: selected.has(row.id)});
          const label = element("label", "");
          compare.setAttribute("aria-label", row.label + "を比較");
          compare.dataset.marketId = row.id;
          compare.addEventListener("change", () => {
            if (compare.checked) selected.set(row.id, row);
            else selected.delete(row.id);
            paintComparison();
          });
          label.append(compare, " 比較");
          finance.append(" ", label);
        }
        const source = element("td", "");
        source.append(link(row.identity_source, row.market === "SG" ? "SGX調査" : "銘柄資料"));
        const evidence = rankingEvidence(row);
        const ranking = element("td", "");
        const detail = element("details", "");
        detail.append(element("summary", row.rankingEligible ? "対象" : "対象外の理由"));
        for (const [label, value, url] of [["株価", evidence.quote, evidence.quoteSource],
          ["株数", evidence.share, evidence.shareSource]]) {
          const line = element("div", label + " " + value);
          if (url?.startsWith("https://")) line.append(" ", link(url, label + "出典"));
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
    query.addEventListener("input", paint);
    paint();
  } catch (error) {
    status.textContent = "銘柄資料を照合できない（" + error.message + "）";
  }
}

if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", initMarketResearch);
if (typeof module !== "undefined") module.exports = {buildMarketRows, filterMarketRows, compareAnnual, calculateMarketScenario, readPersonalQuotes, readPersonalShares, matchScenarioShares, rankingEvidence, summarizeMarketCoverage};
