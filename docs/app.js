/* VALUE HUNTER AI static, dependency-free SGX comparator.
 * Financial values always come from the JSON feed, never demo fixtures.
 * Render all external feed strings with textContent, not HTML.
 */
"use strict";
const names = {
  S68: "Singapore Exchange Limited",
  G13: "Genting Singapore Limited",
  S20: "The Straits Trading Company Limited"
};
const reasons = {
  FINANCIAL_MISSING_REVENUE: "売上高が未取得",
  FINANCIAL_MISSING_ATTRIBUTABLE_PROFIT: "親会社株主帰属損益が未取得",
  FINANCIAL_MISSING_ASSETS: "総資産が未取得",
  FINANCIAL_MISSING_LIABILITIES: "負債合計が未取得",
  FINANCIAL_MISSING_EQUITY: "純資産が未取得",
  FISCAL_YEAR_UNKNOWN: "決算年度が不明",
  HISTORICAL_FIXED_FINANCIALS: "過去に固定登録した財務データ",
  BALANCE_UNVERIFIED_OR_MISMATCH: "貸借対照表の検証不足または不一致",
  SECOND_ISSUER_DOCUMENT_NOT_MATCHED_REVENUE: "売上高が別の公式資料と未照合",
  SECOND_ISSUER_DOCUMENT_NOT_MATCHED_ATTRIBUTABLE_PROFIT: "帰属損益が別の公式資料と未照合",
  INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE: "第三者による独立検証が未完了",
  PRICE_MISSING: "株価が未取得",
  QUOTE_OLD_OR_UNDATED: "株価が古い・取得日不明",
  SHARES_MISSING: "発行済株式数が未取得",
  SHARES_OLD_OR_UNDATED: "発行済株式数が古い・基準日不明",
  SHARES_SOURCE_MISSING: "株式数の出典が未登録",
  TREASURY_SHARE_BASIS_UNCONFIRMED: "自己株式控除後の株式数か未確認",
  NEGATIVE_EARNINGS_PER_NOT_APPLICABLE: "赤字のためPER算出対象外",
  PARENT_EQUITY_NOT_INDEPENDENTLY_VERIFIED: "親会社株主持分が未検証",
  QUOTE_NOT_AVAILABLE: "株価データなし",
  QUOTE_TIMESTAMP_MISSING: "株価の基準時刻が不明",
  QUOTE_STALE: "株価が7日より古い",
  QUOTE_DATE_IN_FUTURE: "株価の時刻が未来",
  SHARES_NOT_AVAILABLE: "株式数データなし",
  SHARES_DATE_MISSING: "株式数の基準日が不明",
  SHARES_STALE: "株式数が180日より古い",
  SHARES_DATE_IN_FUTURE: "株式数の基準日が未来",
  MARKET_CAP_ARITHMETIC_MISMATCH: "時価総額の計算が一致しないため非表示",
  PER_ARITHMETIC_MISMATCH_OR_INVALID: "PERの計算が不一致のため非表示",
  PBR_REFERENCE_INVALID_OR_CAP_MISMATCH: "PBRの根拠不足・計算不一致のため非表示",
  VERIFIED_PBR_LABEL_UNSUPPORTED: "PBRの検証済み表記を保留"
};
const $ = id => document.getElementById(id);
const state = { feed: null, selected: null, visible: [] };

function el(tag, cls = "", text = null) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== null) node.textContent = String(text);
  return node;
}
function hasNum(n) { return typeof n === "number" && Number.isFinite(n); }
function fmt(n, digits = 2) {
  return hasNum(n) ? new Intl.NumberFormat("ja-JP", {
    minimumFractionDigits: digits, maximumFractionDigits: digits
  }).format(n) : "—";
}
function dateJst(value) {
  if (!value || Number.isNaN(Date.parse(value))) return "—";
  return new Date(value).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit" }) + " JST";
}
function addTextCell(tr, value, cls = "") { const td = el("td", cls, value); tr.append(td); return td; }
function safeLink(url, label) {
  if (typeof url !== "string" || !/^https:\/\//.test(url)) return el("span", "", "未登録");
  const node = el("a", "", label);
  node.href = url; node.target = "_blank"; node.rel = "noopener noreferrer";
  return node;
}
function warn(message, error = false) {
  $("statusMessage").textContent = message;
  $("statusMessage").classList.toggle("error", error);
}
function validFeed(json) {
  if (!json || json.schema_version !== "value_hunter_web_v29" ||
      !Array.isArray(json.records) || !json.records.length ||
      json.ranking_enabled !== false || !json.coverage ||
      json.coverage.all_sgx_listed !== false) return false;
  const seen = new Set();
  for (const r of json.records) {
    if (!r || typeof r.symbol !== "string" || !/^[A-Z0-9]{1,8}$/.test(r.symbol) ||
        seen.has(r.symbol) || r.ranking_eligible !== false ||
        !Array.isArray(r.exclusion_reasons) || !r.exclusion_reasons.length) return false;
    seen.add(r.symbol);
  }
  return true;
}
function freshnessState(value, maxDays, nowMs = Date.now()) {
  if (typeof value !== "string" || !value.length) return "MISSING";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return "MISSING";
  const days = (nowMs - parsed) / 86400000;
  return days > maxDays || days < -1 ? "STALE" : "RECENT";
}
function liveQuality(feed, nowMs = Date.now()) {
  const rows = feed.records || [];
  return {
    feed: freshnessState(feed.updated_at_utc, 4, nowMs),
    staleQuotes: rows.filter(r => freshnessState(r.quote_timestamp_utc, 7, nowMs) === "STALE").length,
    missingQuotes: rows.filter(r => !hasNum(r.price_sgd) ||
      freshnessState(r.quote_timestamp_utc, 7, nowMs) === "MISSING").length,
    staleShares: rows.filter(r => freshnessState(r.shares_as_of_date, 180, nowMs) === "STALE").length,
    arithmeticIssues: rows.filter(r => (r.quality_flags || []).some(flag =>
      typeof flag === "string" && flag.includes("MISMATCH"))).length
  };
}
function setFeed(json, label) {
  if (!validFeed(json)) throw new Error("対応していないJSON形式、またはランキング状態の不整合");
  state.feed = json;
  populateHistorySymbols();
  renderHistory();
  $("dataState").textContent = label;
  $("updatedAt").textContent = "生成日時：" + dateJst(json.updated_at_utc);
  $("totalCount").textContent = json.records.length;
  $("eligibleCount").textContent = json.records.filter(r => r.ranking_eligible).length;
  $("excludedCount").textContent = json.records.filter(r => !r.ranking_eligible).length;
  $("pricedCount").textContent = json.records.filter(r => hasNum(r.price_sgd)).length;
  const quality = liveQuality(json);
  const issueCount = quality.staleQuotes + quality.missingQuotes + quality.arithmeticIssues;
  const notes = [];
  if (quality.feed !== "RECENT") notes.push("公開データの最終更新が4日より古い／不明");
  if (issueCount) notes.push("株価の鮮度・計算に問題：" + issueCount + "件");
  if (quality.staleShares) notes.push("株式数の基準日が180日より古い：" + quality.staleShares + "件");
  warn(notes.length ? "データ品質警告：" + notes.join("。") + "。銘柄詳細を参照。" :
    "株価・財務は参考値。第三者独立検証が完了するまでランキング対象外。");
  render();
}
function sortRows(items, key) {
  if (key === "symbol") return items.sort((a, b) => a.symbol.localeCompare(b.symbol));
  const ascending = key === "per_reference" || key === "pbr_reference_unverified";
  return items.sort((a, b) => {
    const x = hasNum(a[key]) ? a[key] : null;
    const y = hasNum(b[key]) ? b[key] : null;
    if (x === null) return y === null ? a.symbol.localeCompare(b.symbol) : 1;
    if (y === null) return -1;
    return ascending ? x - y : y - x;
  });
}
function render() {
  const feed = state.feed;
  if (!feed) return;
  const term = $("search").value.trim().toLowerCase();
  const flag = $("statusFilter").value;
  const visible = sortRows(feed.records.filter(r => {
    const text = [r.symbol, r.issuer || names[r.symbol] || ""].join(" ").toLowerCase();
    return text.includes(term) &&
      (flag === "all" || (flag === "eligible" ? r.ranking_eligible : !r.ranking_eligible));
  }), $("sortBy").value);
  state.visible = visible;
  const tbody = $("stockRows");
  tbody.replaceChildren();
  if (!visible.length) {
    const row = el("tr"); const td = addTextCell(row, "該当する銘柄がない。検索条件を変えてみて。", "empty");
    td.colSpan = 10; tbody.append(row);
  }
  for (const r of visible) {
    const tr = el("tr");
    const id = el("td");
    id.append(el("div", "ticker", r.symbol),
      el("div", "issuer", r.issuer || names[r.symbol] || ""));
    tr.append(id);
    addTextCell(tr, fmt(r.price_sgd), "num");
    addTextCell(tr, fmt(hasNum(r.market_cap_sgd) ? r.market_cap_sgd / 1e8 : null), "num");
    addTextCell(tr, fmt(r.per_reference), "num");
    addTextCell(tr, fmt(r.pbr_verified ?? r.pbr_reference_unverified), "num caution");
    for (const value of [r.revenue_growth_pct, r.operating_margin_pct, r.equity_ratio_pct]) {
      const cls = hasNum(value) && value < 0 ? "num negative" : "num";
      addTextCell(tr, hasNum(value) ? fmt(value) + "%" : "—", cls);
    }
    const statusTd = el("td");
    statusTd.append(el("span", r.ranking_eligible ? "status good" : "status",
      r.ranking_eligible ? "対象" : "検証不足・除外"));
    tr.append(statusTd);
    const btnTd = el("td");
    const button = el("button", "detail-button", "詳細");
    button.type = "button";
    button.addEventListener("click", () => {
      state.selected = r.symbol;
      const select = $("historySymbol");
      if ([...select.options].some(option=>option.value===r.symbol)){
        select.value=r.symbol;
        renderHistory();
      }
      showDetail(r);
      $("detailTitle").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    btnTd.append(button); tr.append(btnTd); tbody.append(tr);
  }
  $("tableCount").textContent = visible.length + "件を表示";
  if (state.selected) {
    const selected = feed.records.find(r => r.symbol === state.selected);
    if (selected) showDetail(selected);
  }
}
function field(box, title, rows) {
  const section = el("section", "detailbox");
  section.append(el("h4", "", title));
  const dl = el("dl");
  for (const [name, value, url] of rows) {
    const entry = el("div");
    entry.append(el("dt", "", name));
    const dd = el("dd");
    dd.append(url === true ? safeLink(value, value ? "出典を開く ↗" : "未登録") : el("span", "", value));
    entry.append(dd); dl.append(entry);
  }
  section.append(dl); return section;
}
function showDetail(r) {
  const parent = $("detailContent");
  parent.replaceChildren();
  const top = el("div", "detailtop");
  const title = el("div");
  title.append(el("h3", "", r.symbol + " / " + (r.issuer || names[r.symbol] || "")),
    el("p", "", "決算年度 " + (r.fiscal_year || "不明") + " / 金額単位：千SGD（財務）・SGD（株価）"));
  top.append(title, el("span", r.ranking_eligible ? "status good" : "status",
    r.ranking_eligible ? "ランキング対象" : "ランキングから除外"));
  parent.append(top);
  const grid = el("div", "detailgrid");
  grid.append(
    field("財務", "財務資料と指標", [
      ["売上高（千SGD）", fmt(r.revenue_sgd_thousands, 0)],
      ["親会社株主帰属損益（千SGD）", fmt(r.attributable_profit_sgd_thousands, 0)],
      ["連結総資産（千SGD）", fmt(r.assets_sgd_thousands, 0)],
      ["連結総負債（千SGD）", fmt(r.liabilities_sgd_thousands, 0)],
      ["連結純資産（千SGD）", fmt(r.equity_sgd_thousands, 0)],
      ["貸借差額（千SGD）", fmt(r.balance_difference_sgd_thousands, 0)],
      ["連結貸借の取得状態", r.balance_source_status || "未検証"],
      ["連結貸借の根拠ページ", r.balance_source_page || "未登録"],
      ["資料の種類", r.financial_source_kind || "未取得"],
      ["公式財務資料", r.financial_source_url, true],
      ["資料のファイル識別子", r.financial_pdf_sha256 || "未登録"],
    ]),
    field("市場", "株価と株式数", [
      ["株価（SGD）", fmt(r.price_sgd)],
      ["株価基準時刻", dateJst(r.quote_timestamp_utc)],
      ["株価の鮮度", ({RECENT:"7日以内",STALE:"7日超または日付不正",MISSING:"不明"})[freshnessState(r.quote_timestamp_utc, 7)] || "未検証"],
      ["株価出典", r.quote_url, true],
      ["発行済株式数（自己株式控除後）", fmt(r.shares_outstanding, 0)],
      ["株式数基準日", r.shares_as_of_date || "未取得"],
      ["株式数の鮮度", ({RECENT:"180日以内",STALE:"180日超または日付不正",MISSING:"不明"})[freshnessState(r.shares_as_of_date, 180)] || "未検証"],
      ["株式数の検証状態", r.shares_verification_status || "未検証"],
      ["自己株式の扱い", r.shares_count_basis || "未確認"],
      ["株式数出典", r.shares_source_url, true],
    ]),
    field("評価", "バリュエーション（参考）", [
      ["時価総額（SGD）", fmt(r.market_cap_sgd, 0)],
      ["PER", fmt(r.per_reference) + (hasNum(r.per_reference) ? " 倍" : "")],
      ["PBR（未検証）", fmt(r.pbr_reference_unverified) + (hasNum(r.pbr_reference_unverified) ? " 倍" : "")],
      ["PBR分母：親会社株主持分（千SGD）", fmt(r.parent_equity_sgd_thousands, 0)],
      ["親会社株主持分の検証状態", r.parent_equity_status || "未検証"],
      ["親会社株主持分の出典", r.parent_equity_source_url, true],
      ["検証済みPBR", fmt(r.pbr_verified)],
    ]),
    field("照合", "公式資料間の照合状況", [
      ["売上高", (r.audit_states || {}).revenue || "未検証"],
      ["営業利益", (r.audit_states || {}).operating_profit || "未検証"],
      ["帰属損益", (r.audit_states || {}).attributable_profit || "未検証"],
      ["照合先の公式PDF", r.audit_source_url, true],
      ["売上高の根拠ページ", ((r.audit_pages_by_metric || {}).revenue || []).join(", ") || "未取得"],
      ["営業利益の根拠ページ", ((r.audit_pages_by_metric || {}).operating_profit || []).join(", ") || "未取得"],
      ["帰属損益の根拠ページ", ((r.audit_pages_by_metric || {}).attributable_profit || []).join(", ") || "未取得"],
      ["照合の性質", "同一企業の別資料との一致（第三者独立監査ではない）"],
      ["更新情報", dateJst(state.feed.updated_at_utc)],
    ])
  );
  parent.append(grid, el("div", "eyebrow", "ランキング除外理由・品質チェック"));
  const list = el("ul", "reasons");
  for (const reason of r.exclusion_reasons || []) {
    const li = el("li", "", reasons[reason] || reason);
    li.title = reason;
    list.append(li);
  }
  if (!list.children.length) list.append(el("li", "", "理由なし"));
  parent.append(list);
}
function exportCsv() {
  if (!state.feed) return;
  const keys = ["symbol", "issuer", "fiscal_year", "price_sgd", "market_cap_sgd",
    "per_reference", "pbr_reference_unverified", "revenue_growth_pct", "operating_margin_pct",
    "equity_ratio_pct", "ranking_eligible", "exclusion_reasons"];
  const quote = value => {
    const raw = String(value ?? "");
    // Prevent spreadsheet formula execution when exporting imported JSON.
    const safe = typeof value === "string" && /^[=+@-]/.test(raw.trimStart()) ? "'" + raw : raw;
    return '"' + safe.replace(/"/g, '""') + '"';
  };
  const lines = [keys.map(quote).join(",")];
  for (const r of state.visible) lines.push(keys.map(k => quote(k === "exclusion_reasons" ?
    (r[k] || []).join(";") : r[k])).join(","));
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "value-hunter-sgx-comparison.csv"; a.click();
  URL.revokeObjectURL(url);
}
async function start() {
  const link = document.createElement("button");
  link.type = "button"; link.textContent = "JSONを読み込む";
  link.className = "secondary-button";
  link.addEventListener("click", () => $("fileInput").click());
  document.querySelector(".toolbar").append(link);
  $("search").addEventListener("input", render);
  $("statusFilter").addEventListener("change", render);
  $("sortBy").addEventListener("change", render);
  $("exportCsv").addEventListener("click", exportCsv);
  $("fileInput").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;
    try { setFeed(JSON.parse(await file.text()), "手動読み込み：" + file.name); }
    catch (error) { warn("JSONを読み込めなかった：" + error.message, true); }
  });
  try {
    const response = await fetch("./data/latest.json", { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    setFeed(await response.json(), "GitHub上の公開データ");
  } catch (error) {
    $("stockRows").replaceChildren();
    $("totalCount").textContent = "0"; $("eligibleCount").textContent = "0";
    $("excludedCount").textContent = "0"; $("pricedCount").textContent = "0";
    warn("公開データを取得できなかった。GitHub Actionsの実行を待つか、「JSONを読み込む」を利用して。" +
      "（" + error.message + "）", true);
  }
}

const HISTORY_NS = "http://www.w3.org/2000/svg";
const historyState = {data: null};
function histSvg(name, attributes = {}) {
  const node = document.createElementNS(HISTORY_NS, name);
  for (const [key, val] of Object.entries(attributes)) node.setAttribute(key, String(val));
  return node;
}
function populateHistorySymbols() {
  const select = $("historySymbol");
  if (!select) return;
  const current = select.value;
  const currentRecords = state.feed?.records || [];
  const historicRecords = historyState.data?.entries?.flatMap(e => e.records || []) || [];
  const symbols = [...new Set([...currentRecords, ...historicRecords]
    .map(r => r.symbol).filter(s => typeof s === "string" && /^[A-Z0-9]{1,8}$/.test(s)))];
  select.replaceChildren();
  for (const symbol of symbols) {
    const item = document.createElement("option");
    item.value = symbol;
    item.textContent = symbol + " / " +
      (currentRecords.find(r => r.symbol === symbol)?.issuer || names[symbol] || "");
    select.append(item);
  }
  if (symbols.includes(current)) select.value = current;
  else if (symbols.includes(state.selected)) select.value = state.selected;
  else if (symbols.length) select.value = symbols[0];
}
function historicalObservations(entries, symbol, metric) {
  const observations = [];
  for (const entry of entries) {
    if (typeof entry.date_utc !== "string") continue;
    const found = (entry.records || []).find(r => r.symbol === symbol);
    const value = found ? found[metric] : null;
    const timestamp = found?.quote_timestamp_utc;
    // Do not plot an undated market quote or pretend repeated stale quotes
    // are new trading-day observations.
    if (!hasNum(value) || value < 0 || typeof timestamp !== "string" ||
        Number.isNaN(Date.parse(timestamp))) continue;
    const previous = observations[observations.length - 1];
    if (previous && previous.actualQuoteDate === timestamp && previous.value === value) continue;
    observations.push({date: entry.date_utc, value: value, actualQuoteDate: timestamp});
  }
  return observations;
}
function renderHistory() {
  const chart = $("historyChart");
  if (!chart) return;
  chart.replaceChildren();
  const index = historyState.data;
  if (!index || !Array.isArray(index.entries) || !index.entries.length) {
    $("historyStatus").textContent = "更新履歴はまだない。初回の正常なデータ更新から記録される。";
    chart.append(el("div", "empty-history", "記録データなし"));
    return;
  }
  const symbol = $("historySymbol").value;
  const metric = $("historyMetric").value;
  const values = historicalObservations(index.entries, symbol, metric);
  $("historyStatus").textContent = symbol + " / " +
    $("historyMetric").selectedOptions[0].textContent +
    " — " + values.length + "回の市場時刻付き観測値。重複・欠損は補完しない。";
  if (!values.length) {
    chart.append(el("div", "empty-history", "この指標はまだ記録されてない。"));
    return;
  }
  const W=840, H=236, L=66, R=24, T=20, B=38, plotW=W-L-R, plotH=H-T-B;
  const numbers=values.map(v=>v.value);
  const low=Math.min(...numbers), high=Math.max(...numbers);
  const range=high-low || Math.max(Math.abs(high)*0.08, 0.01);
  const ymin=Math.max(0, low-range*0.2), ymax=high+range*0.2;
  const span=Math.max(ymax-ymin,0.01);
  const svg=histSvg("svg", {viewBox:"0 0 "+W+" "+H,role:"img",
    "aria-label":symbol+"："+values.length+"回の記録値の推移"});
  for (let i=0;i<4;i++) {
    const y=T+plotH*i/3;
    svg.append(histSvg("line",{x1:L,y1:y,x2:W-R,y2:y,class:"gridline"}));
    const tick=histSvg("text",{x:L-10,y:y+4,"text-anchor":"end",class:"tick-label"});
    tick.textContent=fmt(ymax-span*i/3,2);
    svg.append(tick);
  }
  const coords=values.map((v,i)=>Object.assign({
    x:L+(values.length===1?plotW/2:i*plotW/(values.length-1)),
    y:T+(ymax-v.value)/span*plotH
  },v));
  if (coords.length>=2) {
    svg.append(histSvg("polyline",{points:coords.map(c=>c.x+","+c.y).join(" "),class:"price-line"}));
  }
  for (const p of coords) {
    const circle=histSvg("circle",{cx:p.x,cy:p.y,r:5,class:"price-point"});
    const title=histSvg("title");
    title.textContent=p.date+" / "+fmt(p.value)+"（元の株価時刻："+(p.actualQuoteDate||"不明")+"）";
    circle.append(title);svg.append(circle);
  }
  for (const i of [...new Set([0,Math.floor((coords.length-1)/2),coords.length-1])]) {
    const p=coords[i];
    const txt=histSvg("text",{x:p.x,y:H-12,class:"axis",
      "text-anchor":i===0?"start":i===coords.length-1?"end":"middle"});
    txt.textContent=p.date.slice(5);svg.append(txt);
  }
  chart.append(svg);
}
async function loadHistory() {
  try {
    const response=await fetch("./data/history/index.json",{cache:"no-store"});
    if (!response.ok) throw new Error("HTTP "+response.status);
    const data=await response.json();
    if (data.schema_version!=="value_hunter_history_v34"||!Array.isArray(data.entries)) {
      throw new Error("Unknown history version");
    }
    historyState.data=data;
  } catch (error) {historyState.data=null;}
  populateHistorySymbols();renderHistory();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {historicalObservations, freshnessState, liveQuality};
}
if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded",()=>{
  $("historySymbol").addEventListener("change",renderHistory);
  $("historyMetric").addEventListener("change",renderHistory);
  start();
  loadHistory();
});
