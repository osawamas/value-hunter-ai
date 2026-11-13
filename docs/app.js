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
  FINANCIAL_SOURCE_REGISTERED_NOT_PARSED: "公式財務資料は登録済み・数値は未解析",
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
  VERIFIED_PBR_LABEL_UNSUPPORTED: "PBRの検証済み表記を保留",
  TREASURY_SHARE_ARITHMETIC_OR_BASIS_MISMATCH: "発行済株式数と自己株式控除の計算が不一致",
  SHARE_SOURCE_PDF_SHA256_INVALID: "株式数のPDF識別子が不正",
  PBR_DENOMINATOR_MISSING_OR_ARITHMETIC_MISMATCH: "親会社株主持分を使ったPBR計算が不一致",
  VALUATIONS_SUPPRESSED_STALE_OR_UNDATED_SOURCE: "株価または株式数の日時が古い／不明のため評価値を非表示"
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
    if (r.bank_financial_state?.status === "AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED")
      id.append(el("div", "issuer", "銀行連結財務解析済・市場データ未検証"));
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
      r.ranking_eligible ? "対象" :
      r.bank_financial_state?.status === "AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED" ? "財務解析済・ランキング除外" : "検証不足・除外"));
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
  const bankParsed = r.bank_financial_state?.status === "AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED";
  title.append(el("h3", "", r.symbol + " / " + (r.issuer || names[r.symbol] || "")),
    el("p", "", bankParsed ? "銀行連結財務：2025年12月期の監査済み資料から解析済み（百万SGD）。株価・株式数・投資評価は未検証。" :
      "決算年度 " + (r.fiscal_year || "不明") + " / 金額単位：千SGD（財務）・SGD（株価）"));
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
      ["株式数（控除状態は下記）", fmt(r.shares_outstanding, 0)],
      ["発行済株式数（自己株式を含む）", fmt(r.gross_issued_shares, 0)],
      ["自己株式数", fmt(r.treasury_shares, 0)],
      ["発行済−自己株式の一致", hasNum(r.gross_issued_shares) && hasNum(r.treasury_shares) && hasNum(r.shares_outstanding) ?
        (r.gross_issued_shares - r.treasury_shares === r.shares_outstanding ? "一致" : "不一致") : "未照合"],
      ["株式数基準日", r.shares_as_of_date || "未取得"],
      ["株式数の鮮度", ({RECENT:"180日以内",STALE:"180日超または日付不正",MISSING:"不明"})[freshnessState(r.shares_as_of_date, 180)] || "未検証"],
      ["株式数の検証状態", r.shares_verification_status || "未検証"],
      ["自己株式の扱い", r.shares_count_basis || "未確認"],
      ["株式数出典", r.shares_source_url, true],
      ["株式数のPDF識別子（SHA256）", r.shares_pdf_sha256 || "未取得"],
    ]),
    field("評価", "バリュエーション（参考）", [
      ["時価総額（SGD）", fmt(r.market_cap_sgd, 0)],
      ["PER", fmt(r.per_reference) + (hasNum(r.per_reference) ? " 倍" : "")],
      ["PBR（未検証）", fmt(r.pbr_reference_unverified) + (hasNum(r.pbr_reference_unverified) ? " 倍" : "")],
      ["PBR分母：親会社株主持分（千SGD）", fmt(r.parent_equity_sgd_thousands, 0)],
      ["親会社株主持分の検証状態", r.parent_equity_status || "未検証"],
      ["親会社株主持分の独立検証", "未完了（企業の監査済み資料による内訳照合とは別）"],
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
  // Bank income is separate from industrial revenue / operating margin.
  // The nested record is audited issuer evidence, not a current quote or ranking.
  const bank = r.banking_evidence;
  if (bank && bank.status === "BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED" &&
      bank.scope === "GROUP_BANKING_NOT_INDUSTRIAL_FINANCIALS") {
    const inc = bank.income?.["2025"] || {};
    const bal = bank.balance?.["2025"] || {};
    const previous = bank.income?.["2024"] || {};
    grid.append(field("銀行", "銀行専用の連結決算（2025年・2024年比較）", [
      ["銀行の財務年度", "2025年12月期"],
      ["総収益（2025年・百万SGD）", fmt(inc.total_income, 0)],
      ["総収益（2024年・百万SGD）", fmt(previous.total_income, 0)],
      ["純金利収益（2025年・百万SGD）", fmt(inc.net_interest_income, 0)],
      ["非金利収益（2025年・百万SGD）", fmt(inc.non_interest_income, 0)],
      ["貸倒・その他損失引当（百万SGD）", fmt(inc.allowances_for_credit_losses, 0)],
      ["親会社株主帰属利益（百万SGD）", fmt(inc.profit_attributable_to_parent, 0)],
      ["総資産（百万SGD）", fmt(bal.total_assets, 0)],
      ["負債合計（百万SGD）", fmt(bal.total_liabilities, 0)],
      ["親会社株主持分（百万SGD）", fmt(bal.parent_shareholders_funds, 0)],
      ["非支配持分（百万SGD）", fmt(bal.non_controlling_interests, 0)],
      ["株式数基準日（過去時点）", bank.historical_shareholding?.as_of_date || "未登録"],
      ["自己株式控除後（過去時点・株）", fmt(bank.historical_shareholding?.shares_outstanding, 0)],
      ["自己株式数（過去時点・株）", fmt(bank.historical_shareholding?.treasury_shares, 0)],
      ["PDFのSHA256", bank.pdf_sha256 || "未登録"],
      ["公式年次報告書", bank.source_url, true],
      ["検証区分", "発行会社の監査済み連結資料内で照合。第三者との数値突合は未実施"],
      ["ランキング・時価総額", "未採用（株価と最新株式数の検証待ち）"],
    ]));
  }
  const primaryRecent = r.bank_primary_recent_share_event;
  if (primaryRecent && primaryRecent.status === "ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED") {
    grid.append(field("SGX原本", "UOB公式SGX通知・2026年11月12日（現在値ではない）", [
      ["公式開示日", primaryRecent.as_of_date || "未取得"],
      ["SGXNet開示番号", primaryRecent.sgxnet_reference || "未登録"],
      ["自己株式控除後", fmt(primaryRecent.issued_excluding_treasury,0) + " 株"],
      ["自己株式残高", fmt(primaryRecent.treasury_shares,0) + " 株"],
      ["控除前発行済株数（計算値）", fmt(primaryRecent.gross_issued_derived,0) + " 株"],
      ["SGX公式原本", primaryRecent.primary_source_url, true],
      ["原本SHA256", primaryRecent.primary_html_sha256 || "未登録"],
      ["11月13日の通知", "転載は確認済み、SGX原本との照合は未完了"],
      ["現在株数・時価総額・PER・PBR", "未採用。後続の開示と取引時刻付き株価の検証が必要"],
    ]));
  }
  const primarySnapshot = r.bank_primary_share_history;
  if (primarySnapshot && primarySnapshot.status === "ORIGINAL_SGX_DAILY_BUYBACK_2026_09_07_RECONCILED") {
    grid.append(field("SGX原本", "公式SGX通知で照合済みの過去株式数（現在値ではない）", [
      ["SGX原本の基準日", primarySnapshot.as_of_date || "未登録"],
      ["SGXNet開示番号", primarySnapshot.sgxnet_reference || "未登録"],
      ["自己株式控除後の株数", fmt(primarySnapshot.issued_excluding_treasury,0) + " 株"],
      ["自己株式の保有数", fmt(primarySnapshot.treasury_shares,0) + " 株"],
      ["控除前発行済株数（計算値）", fmt(primarySnapshot.gross_issued_derived,0) + " 株"],
      ["SGX公式原本", primarySnapshot.primary_source_url, true],
      ["原本SHA256", primarySnapshot.primary_html_sha256 || "未登録"],
      ["現在の株式数", "未確定。9月7日より後の株式数変動通知との突合が必要"],
      ["時価総額・PER・PBR・ランキング", "採用しない"],
    ]));
  }
  const shareLead = r.bank_share_discovery;
  if (shareLead && shareLead.status === "SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED") {
    grid.append(field("株式調査", "新しい株式数開示の候補（SGX原本の数値照合は未完）", [
      ["対象の開示日", shareLead.event_date || "未取得"],
      ["開示の種類", shareLead.event_type || "未登録"],
      ["SGXNetの開示番号", shareLead.sgx_announcement_reference || "未登録"],
      ["控除後株式数（未検証の転載値）",
        hasNum(shareLead.candidate_shares_excluding_treasury) ?
          fmt(shareLead.candidate_shares_excluding_treasury, 0) + " 株（未検証）" : "未取得"],
      ["自己株式数（未検証の転載値）",
        hasNum(shareLead.candidate_treasury_shares) ?
          fmt(shareLead.candidate_treasury_shares, 0) + " 株（未検証）" : "未取得"],
      ["以前見つけた転載の基準日", r.bank_share_discovery_history?.[0]?.event_date || "該当なし"],
      ["以前の転載の自己株式控除後株数",
        hasNum(r.bank_share_discovery_history?.[0]?.candidate_shares_excluding_treasury)
          ? fmt(r.bank_share_discovery_history[0].candidate_shares_excluding_treasury,0) + " 株（未検証）"
          : "未取得"],
      ["情報の性質", "SGXNet開示の転載。公式原本と照合できるまで未検証"],
      ["原本のURL", "未特定"],
      ["転載ページ", shareLead.secondary_source_url, true],
      ["最新株式数としての利用", "不可。調査した開示が最新とも限らない"],
      ["株価・時価総額・PER・PBR", "未採用。独立した価格・株数の公式照合が必要"],
    ]));
  }
  const historicShares = r.bank_historical_shares;
  if (historicShares && historicShares.status === "HISTORICAL_ISSUER_PDF_TREASURY_RECONCILED_NOT_CURRENT") {
    grid.append(field("過去株数", "公式年次報告書の過去時点の株数（現在の時価総額には使用しない）", [
      ["基準日", historicShares.as_of_date || "未登録"],
      ["控除前発行済株式数（株）", fmt(historicShares.gross_issued_shares, 0)],
      ["自己株式数（株）", fmt(historicShares.treasury_shares, 0)],
      ["自己株式控除後株式数（株）", fmt(historicShares.issued_excluding_treasury, 0)],
      ["控除の一致", hasNum(historicShares.gross_issued_shares) &&
        hasNum(historicShares.treasury_shares) && hasNum(historicShares.issued_excluding_treasury) &&
        historicShares.gross_issued_shares - historicShares.treasury_shares === historicShares.issued_excluding_treasury
        ? "一致" : "未照合"],
      ["現在の株数としての扱い", "過去資料のため不採用。最新の公式開示と照合待ち"],
      ["時価総額・PER・PBR", "未計算（株価・最新株数が未検証）"],
      ["公式年次報告書", historicShares.source_url, true],
      ["PDF識別子（SHA256）", historicShares.source_pdf_sha256 || "未登録"],
      ["出典PDFのページ", historicShares.source_pdf_page || "未登録"],
    ]));
  }
  const bankSummary = r.banking_summary;
  if (bankSummary && bankSummary.status === "ISSUER_ANNUAL_GROUP_HIGHLIGHTS_2025_2024") {
    const bankVals = bankSummary.values || {};
    const val = (key, year = "2025") => fmt(bankVals[key]?.[year], 0);
    const uob = r.symbol === "U11";
    grid.append(field("銀行概要", "銀行の公式年次報告書・連結財務サマリー", [
      ["決算期間", "2025年12月期（比較対象：2024年）"],
      ["総収益 2025年（百万SGD）", val("total_income")],
      ["総収益 2024年（百万SGD）", val("total_income", "2024")],
      ["純金利収益 2025年（百万SGD）", uob ? "未抽出" : val("net_interest_income")],
      ["親会社株主帰属利益 2025年（百万SGD）",
        val(uob ? "parent_net_profit" : "parent_attributable_profit")],
      ["親会社株主帰属利益 2024年（百万SGD）",
        val(uob ? "parent_net_profit" : "parent_attributable_profit", "2024")],
      ["総資産 2025年", uob ? val("total_assets_rounded_billions") + " 十億SGD（丸め値）" :
        val("total_assets") + " 百万SGD"],
      ["親会社株主持分 2025年", uob ? val("parent_equity_rounded_billions") + " 十億SGD（丸め値）" :
        val("parent_equity") + " 百万SGD"],
      ["資産・株主持分の精度", uob ? "概数・PBR計算には使用しない" : "年次報告書の財務サマリー"],
      ["公式年次報告書", bankSummary.source_url, true],
      ["PDF識別子（SHA256）", bankSummary.pdf_sha256 || "未登録"],
      ["資料の検証段階", "発行体の財務ハイライト。監査済み諸表との行ごとの照合は未実施"],
      ["評価指標", "株価・最新株式数を未取得。PER・PBR・ランキングへの使用なし"],
    ]));
  }
  const auditedBank = r.banking_audited;
  if (auditedBank && auditedBank.status === "ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS") {
    const inc = auditedBank.income || {};
    const bal = auditedBank.balance || {};
    const exact = (metrics, key, year = "2025") => fmt(metrics[key]?.[year], 0);
    grid.append(field("銀行監査", "監査済み連結決算の数値照合（単位：百万SGD）", [
      ["決算期間", auditedBank.period_end || "未取得"],
      ["連結総収益 2025年", exact(inc, "total_income")],
      ["連結総収益 2024年", exact(inc, "total_income", "2024")],
      ["親会社株主帰属利益 2025年", exact(inc, "parent_profit")],
      ["親会社株主帰属利益 2024年", exact(inc, "parent_profit", "2024")],
      ["総資産 2025年（正確な百万SGD）", exact(bal, "total_assets")],
      ["総資産 2024年（正確な百万SGD）", exact(bal, "total_assets", "2024")],
      ["負債合計 2025年", exact(bal, "total_liabilities")],
      ["親会社株主持分 2025年", exact(bal, "parent_equity")],
      ["親会社株主持分 2024年", exact(bal, "parent_equity", "2024")],
      ["非支配持分 2025年", exact(bal, "non_controlling_equity")],
      ["連結損益PDFページ", auditedBank.source_pages?.income ?? "未取得"],
      ["連結貸借PDFページ", auditedBank.source_pages?.balance ?? "未取得"],
      ["公式年次報告書", auditedBank.source_url, true],
      ["PDFのSHA256", auditedBank.pdf_sha256 || "未取得"],
      ["検証内容", "連結財務諸表の算術と同一発行体の財務ハイライト一致。第三者の独立検証は未実施"],
      ["株価・PER・PBR", "別途検証が済むまで未取得・未採用"],
    ]));
  }
  const bankInterim = r.banking_interim_2026;
  if (bankInterim && bankInterim.status === "ISSUER_3Q_AND_NINE_MONTH_TRADING_UPDATE_REGRESSION_MATCHED") {
    const q = bankInterim.Q3?.metrics || {};
    const m = bankInterim.nine_months?.metrics || {};
    const netKey = r.symbol === "O39" ? "group_net_profit" : "net_profit";
    grid.append(field("銀行速報", "2026年第3四半期（7〜9月の3か月、百万SGD）", [
      ["対象期間", "2026年7月1日〜9月30日"],
      ["連結総収益", fmt(q.total_income, 0)],
      ["連結純金利収益", fmt(q.net_interest_income, 0)],
      ["連結最終利益", fmt(q[netKey], 0)],
      ["営業費用（符号は報告書準拠）", fmt(q.operating_expenses, 0)],
      ["資料中のPDFページ", bankInterim.Q3?.source_pdf_page || "未登録"],
    ]));
    grid.append(field("銀行累計", "2026年1〜9月の9か月累計（百万SGD）", [
      ["対象期間", "2026年1月1日〜9月30日"],
      ["連結総収益", fmt(m.total_income, 0)],
      ["連結純金利収益", fmt(m.net_interest_income, 0)],
      ["連結最終利益", fmt(m[netKey], 0)],
      ["営業費用（符号は報告書準拠）", fmt(m.operating_expenses, 0)],
      ["資料中のPDFページ", bankInterim.nine_months?.source_pdf_page || "未登録"],
      ["公式発表日", bankInterim.issuer_release_date || "未登録"],
      ["出典PDF", bankInterim.source_url, true],
      ["ファイル識別子 SHA256", bankInterim.pdf_sha256 || "未登録"],
      ["検証範囲", "発行体の四半期開示との数値照合。監査済み年次決算・第三者独立検証とは別"],
      ["投資評価", "2025年通期やPER・PBRの計算に自動流用しない"],
    ]));
  }
  const bankYoY = r.banking_yoy_2026;
  if (bankYoY && bankYoY.status === "BANK_GROUP_LIKE_FOR_LIKE_Q3_AND_9M_PDF_VERIFIED") {
    const q = bankYoY.Q3 || {};
    const y = bankYoY.nine_months || {};
    const netKey = r.symbol === "O39" ? "group_net_profit" : "net_profit";
    const pct = value => hasNum(value) ? fmt(value, 2) + "％" : "未取得";
    grid.append(field("銀行前年比", "2026年第3四半期の前年同期比（7〜9月の3か月）", [
      ["2025年7〜9月の総収益（百万SGD）", fmt(q.prior_year?.total_income,0)],
      ["2026年7〜9月の総収益（百万SGD）", fmt(q.current_year?.total_income,0)],
      ["総収益の前年同期比", pct(q.growth_pct?.total_income)],
      ["2025年7〜9月の連結最終利益（百万SGD）", fmt(q.prior_year?.[netKey],0)],
      ["2026年7〜9月の連結最終利益（百万SGD）", fmt(q.current_year?.[netKey],0)],
      ["連結最終利益の前年同期比", pct(q.growth_pct?.[netKey])],
    ]));
    grid.append(field("銀行累計前年比", "2026年1〜9月累計の前年同期比（9か月同士）", [
      ["2025年1〜9月の総収益（百万SGD）", fmt(y.prior_year?.total_income,0)],
      ["2026年1〜9月の総収益（百万SGD）", fmt(y.current_year?.total_income,0)],
      ["総収益の前年同期比", pct(y.growth_pct?.total_income)],
      ["2025年1〜9月の連結最終利益（百万SGD）", fmt(y.prior_year?.[netKey],0)],
      ["2026年1〜9月の連結最終利益（百万SGD）", fmt(y.current_year?.[netKey],0)],
      ["連結最終利益の前年同期比", pct(y.growth_pct?.[netKey])],
      ["比較の定義", "同じ期間の前年と比較。2025年の年間決算とは比較しない"],
      ["公式資料", bankYoY.source_url, true],
      ["PDF識別子（SHA256）", bankYoY.pdf_sha256 || "未登録"],
      ["データ検証区分", "同一発行体の四半期開示PDF内で照合。第三者独立検証は未完了"],
      ["投資評価", "PER・PBR・ランキングには使用しない"],
    ]));
  }
  const bankingIndicators = r.banking_indicators;
  if (bankingIndicators &&
      bankingIndicators.status === "HISTORICAL_DERIVED_FROM_AUDITED_ISSUER_GROUP_FY2025") {
    const derived = bankingIndicators.values || {};
    grid.append(field("銀行指標", "2025年の参考指標（監査済み連結数字から独自計算）", [
      ["簡易ROE（参考・％）", hasNum(derived.simple_roe_percent) ? fmt(derived.simple_roe_percent,2) + "％" : "未取得"],
      ["経費率（参考・％）", hasNum(derived.cost_to_income_proxy_percent) ? fmt(derived.cost_to_income_proxy_percent,2) + "％" : "未取得"],
      ["親会社帰属利益の前年比", hasNum(derived.parent_profit_growth_percent) ? fmt(derived.parent_profit_growth_percent,2) + "％" : "未取得"],
      ["親会社株主持分の前年比", hasNum(derived.parent_equity_growth_percent) ? fmt(derived.parent_equity_growth_percent,2) + "％" : "未取得"],
      ["簡易ROEの計算式", "2025年親会社帰属利益 ÷ 2024・2025年末親会社株主持分平均"],
      ["経費率の計算式", "連結営業費用の絶対値 ÷ 連結総収益"],
      ["正式な銀行公表ROE", "別定義のため、この簡易ROEと一致しない場合あり"],
      ["PDF識別子", bankingIndicators.source_pdf_sha256 || "未登録"],
      ["投資ランキング", "未採用。株価・最新株式数・独立検証が不足"],
    ]));
  }
  if (bankParsed) {
    grid.append(field("銀行状況", "銀行の財務解析と市場検証は別の工程", [
      ["銀行連結財務", "2025年12月期・監査済み資料の解析と資料内突合を完了"],
      ["一般事業会社の売上高・営業利益", "銀行に適用しない（共通欄は未取得表示）"],
      ["第三者による数値の独立照合", "未完了"],
      ["最新の株価・自己株式控除後株式数", "未検証"],
      ["PER・PBR・投資ランキング", "必要な市場データと独立検証が不足のため対象外"],
    ]));
  }
  parent.append(grid, el("div", "eyebrow", bankParsed ? "投資ランキング対象外の理由（一般事業会社用の指標は銀行では非適用）" : "ランキング除外理由・品質チェック"));
  const list = el("ul", "reasons");
  for (const reason of r.exclusion_reasons || []) {
    const bankGenericMissing = bankParsed && (
      reason.startsWith("FINANCIAL_MISSING_") || reason === "FISCAL_YEAR_UNKNOWN" ||
      reason === "BALANCE_UNVERIFIED_OR_MISMATCH" ||
      reason.startsWith("SECOND_ISSUER_DOCUMENT_NOT_MATCHED_") ||
      reason === "FINANCIAL_SOURCE_REGISTERED_NOT_PARSED" ||
      reason === "PARENT_EQUITY_NOT_INDEPENDENTLY_VERIFIED");
    const label = bankGenericMissing ? "銀行専用の財務解析とは別：一般事業会社用スキーマの未取得・非適用" :
      (reasons[reason] || reason);
    const li = el("li", "", label);
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
