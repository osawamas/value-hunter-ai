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

async function initMarketResearch() {
  const byId = id => document.getElementById(id);
  const filter = byId("marketFilter"), query = byId("marketQuery");
  const status = byId("marketCount"), body = byId("marketRows");
  const panel = byId("marketDetails");
  const element = (tag, value) => Object.assign(document.createElement(tag), {textContent: value});
  const link = (url, label) => {
    if (!url.startsWith("https://") && !["./sgx-32-research.html", "./index.html"].includes(url)) throw Error("出典URLが不明");
    return Object.assign(element("a", label), {href: url});
  };
  const pct = value => value === null ? "—" : percent.format(value);
  const show = row => {
    const finance = row.financials;
    const periods = compareAnnual(finance);
    byId("marketDetailTitle").textContent = row.label + "（" + row.symbol + "）";
    byId("marketDetailCurrency").textContent = finance.currency + "・" + finance.basis + "・連結年次";
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
    panel.hidden = false;
  };
  try {
    const [research, sgx] = await Promise.all(["./data/market-research-v315.json", "./data/latest.json"].map(async path => {
      const response = await fetch(path, {cache: "no-store"});
      if (!response.ok) throw Error("資料取得 HTTP " + response.status);
      return response.json();
    }));
    const rows = buildMarketRows(research, sgx);
    const paint = () => {
      panel.hidden = true;
      const visible = filterMarketRows(rows, filter.value, query.value);
      status.textContent = visible.length + " / " + rows.length + "件。日本・米国は選定銘柄。株価・正式順位は未接続。";
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
        const source = element("td", "");
        source.append(link(row.identity_source, row.market === "SG" ? "SGX調査" : "銘柄資料"));
        tr.append(finance, source);
        return tr;
      }));
    };
    filter.addEventListener("change", paint);
    query.addEventListener("input", paint);
    paint();
  } catch (error) {
    status.textContent = "銘柄資料を照合できない（" + error.message + "）";
  }
}

if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", initMarketResearch);
if (typeof module !== "undefined") module.exports = {buildMarketRows, filterMarketRows, compareAnnual};
