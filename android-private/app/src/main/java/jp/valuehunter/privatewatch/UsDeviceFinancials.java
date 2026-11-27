package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

final class UsDeviceFinancials {
    static final String SEC_DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json";
    private static final BigDecimal BUDGET = new BigDecimal("100000");

    private record Registration(int cik, String exchange) {}

    static Map<String, BigDecimal> prices(JSONArray rows) throws JSONException {
        var prices = new HashMap<String, BigDecimal>();
        for (int index = 0; index < rows.length(); index++) {
            var row = rows.getJSONObject(index);
            String symbol = row.getString("symbol");
            double price = row.getDouble("close_usd");
            if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || !Double.isFinite(price) || price <= 0
                    || prices.put(symbol, BigDecimal.valueOf(price)) != null) {
                throw new JSONException("Invalid US close");
            }
        }
        if (prices.isEmpty()) throw new JSONException("Missing US closes");
        return prices;
    }

    static JSONArray targets(UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq,
                             JSONObject directory, Set<String> priced) throws JSONException {
        if (!nyse.date().equals(nasdaq.date()) || !java.util.Collections.disjoint(nyse.listed(), nasdaq.listed())) {
            throw new JSONException("Listing directories disagree");
        }
        var fields = directory.getJSONArray("fields");
        if (fields.length() != 4 || !"cik".equals(fields.getString(0)) || !"name".equals(fields.getString(1))
                || !"ticker".equals(fields.getString(2)) || !"exchange".equals(fields.getString(3))) {
            throw new JSONException("Unexpected SEC listing format");
        }
        var listed = new HashSet<>(nyse.listed());
        listed.addAll(nasdaq.listed());
        var other = new HashSet<>(nyse.other());
        other.addAll(nasdaq.other());
        var registrations = new HashMap<String, Set<Registration>>();
        var issuerSymbols = new HashMap<Integer, Set<String>>();
        var rows = directory.getJSONArray("data");
        if (rows.length() == 0 || rows.length() > 50_000) throw new JSONException("Invalid SEC listing count");
        for (int index = 0; index < rows.length(); index++) {
            var row = rows.getJSONArray(index);
            if (row.length() != 4) throw new JSONException("Invalid SEC listing row");
            int cik = row.getInt(0);
            String symbol = row.getString(2);
            if (cik <= 0 || !symbol.matches("[A-Z0-9.$+^=/_-]{1,24}")) throw new JSONException("Invalid SEC listing");
            if (!listed.contains(symbol) && symbol.matches("[A-Z]+-[A-Z]")) {
                String dotted = symbol.replace('-', '.');
                if (listed.contains(dotted)) symbol = dotted;
            }
            if (!other.contains(symbol)) issuerSymbols.computeIfAbsent(cik, unused -> new HashSet<>()).add(symbol);
            registrations.computeIfAbsent(symbol, unused -> new HashSet<>())
                    .add(new Registration(cik, row.optString(3, "")));
        }
        var symbols = new TreeSet<>(nyse.symbols());
        symbols.addAll(nasdaq.symbols());
        symbols.retainAll(priced);
        var result = new JSONArray();
        for (String symbol : symbols) {
            String exchange = nyse.symbols().contains(symbol) ? "NYSE" : "Nasdaq";
            var candidates = new HashSet<Integer>();
            for (var entry : registrations.getOrDefault(symbol, Set.of())) {
                if (exchange.equals(entry.exchange())) candidates.add(entry.cik());
            }
            if (candidates.size() != 1) continue;
            int cik = candidates.iterator().next();
            if (issuerSymbols.getOrDefault(cik, Set.of()).size() != 1) continue;
            result.put(new JSONObject().put("cik", cik).put("exchange", exchange).put("symbol", symbol));
        }
        if (result.length() > 12_000) throw new JSONException("Too many eligible SEC issuers");
        return result;
    }

    static final int FULL_REFRESH_DAYS = 7;
    static final int METER_EVIDENCE_VERSION = 5;

    static JSONObject startScan(String hash, LocalDate day, JSONArray targets, JSONObject previous,
                                Set<Integer> changed) throws JSONException {
        var matching = new HashMap<String, JSONObject>();
        var fullRefresh = day;
        if (changed != null) {
            fullRefresh = LocalDate.parse(previous.getString("full_refresh_day"));
            var oldResults = previous.getJSONArray("results");
            for (int index = 0; index < oldResults.length(); index++) {
                var item = oldResults.getJSONObject(index);
                if (reusable(item, day) && item.has("meter_balance")
                        && item.optInt("meter_evidence_version", 0) == METER_EVIDENCE_VERSION
                        && !changed.contains(item.getInt("cik"))) {
                    matching.put(item.getString("symbol"), item);
                }
            }
        }
        var refresh = new JSONArray();
        var reused = new JSONArray();
        for (int index = 0; index < targets.length(); index++) {
            var target = targets.getJSONObject(index);
            var cached = matching.get(target.getString("symbol"));
            if (cached != null && cached.getInt("cik") == target.getInt("cik")
                    && cached.getString("exchange").equals(target.getString("exchange"))) {
                reused.put(cached);
            } else {
                refresh.put(target);
            }
        }
        return new JSONObject().put("hash", hash).put("day", day.toString())
                .put("full_refresh_day", fullRefresh.toString()).put("cursor", 0)
                .put("reused", reused.length()).put("results", reused).put("targets", refresh);
    }

    static LocalDate reuseFrom(JSONObject previous, LocalDate day) {
        if (previous == null) return null;
        var targets = previous.optJSONArray("targets");
        var results = previous.optJSONArray("results");
        int cursor = previous.optInt("cursor", -1);
        int reused = previous.optInt("reused", 0);
        if (targets == null || results == null || cursor < 0 || cursor > targets.length() || reused < 0
                || reused > results.length() || results.length() > cursor + reused) return null;
        try {
            var old = LocalDate.parse(previous.getString("day"));
            var full = LocalDate.parse(previous.getString("full_refresh_day"));
            return old.isAfter(day) || full.isAfter(old) || !day.isBefore(full.plusDays(FULL_REFRESH_DAYS))
                    ? null : old;
        } catch (JSONException | DateTimeParseException invalid) {
            return null;
        }
    }

    private static boolean reusable(JSONObject row, LocalDate day) {
        try {
            var period = LocalDate.parse(row.getString("equity_date"));
            var filed = LocalDate.parse(row.getString("filed"));
            var earliest = row.optBoolean("partial_value") ? day.minusMonths(16) : day.minusDays(150);
            return !period.isBefore(earliest) && !period.isAfter(filed) && filed.isBefore(day);
        } catch (JSONException | DateTimeParseException invalid) {
            return false;
        }
    }

    record FetchAssessment(JSONObject row, String hold) {}

    static JSONObject financialRow(JSONObject target, JSONObject payload, LocalDate day) throws JSONException {
        return assessFetch(target, payload, day).row();
    }

    static FetchAssessment assessFetch(JSONObject target, JSONObject payload, LocalDate day) throws JSONException {
        int cik = target.getInt("cik");
        var assessed = UsFinancialFacts.assess(payload, cik, day);
        var figures = assessed.facts();
        if (figures == null) {
            // Preserve a separate alternative evidence row; never invent missing aggregate figures.
            var partial = UsFinancialFacts.partialValue(payload,cik,day);
            if (partial == null || !List.of("parent_equity_missing","shares_for_filing_missing",
                    "annual_profit_unconfirmed","previous_annual_profit_unconfirmed","parent_equity_stale",
                    "current_ytd_profit_unconfirmed","prior_ytd_profit_unconfirmed").contains(assessed.hold()))
                return new FetchAssessment(null,assessed.hold());
            var eps = new JSONArray();
            for (var value : partial.eps()) eps.put(value.toPlainString());
            var row = new JSONObject().put("partial_value",true)
                .put("meter_evidence_version",METER_EVIDENCE_VERSION)
                .put("symbol",target.getString("symbol")).put("exchange",target.getString("exchange"))
                .put("cik",cik).put("share_date",partial.end().toString()).put("equity_date",partial.end().toString())
                .put("filed",partial.filed().toString()).put("accession",partial.accession())
                .put("meter_eps",eps).put("meter_cash",partial.cash()==null?JSONObject.NULL:partial.cash())
                .put("meter_balance",partial.balance()==null?JSONObject.NULL:partial.balance())
                .put("strict_hold",assessed.hold());
            return new FetchAssessment(row,assessed.hold());
        }
        var history = UsFinancialFacts.meterHistory(payload, day);
        var eps = new JSONArray();
        for (var value : history.annualEps()) eps.put(value.toPlainString());
        var row = new JSONObject().put("meter_evidence_version", METER_EVIDENCE_VERSION)
                .put("meter_eps", eps).put("meter_cash", history.cash())
                .put("meter_balance", history.balance() == null ? JSONObject.NULL : history.balance())
                .put("symbol", target.getString("symbol")).put("exchange", target.getString("exchange"))
                .put("cik", cik).put("share_date", figures.shareDate().toString())
                .put("equity_date", figures.equityDate().toString()).put("filed", figures.filed().toString())
                .put("profit_basis", figures.profitBasis())
                .put("shares", figures.shares().toPlainString()).put("profit", figures.profit().toPlainString())
                .put("equity", figures.equity().toPlainString());
        return new FetchAssessment(row, "");
    }

    static void recordFetchOutcome(JSONObject scan, String symbol, FetchAssessment result) throws JSONException {
        var holds = scan.optJSONObject("fetch_holds");
        if (holds == null) { holds = new JSONObject(); scan.put("fetch_holds", holds); }
        if (result.row() != null && !result.row().optBoolean("partial_value")) holds.remove(symbol);
        else holds.put(symbol, result.hold() == null || result.hold().isEmpty() ? "unknown" : result.hold());
    }

    static Map<String, Integer> fetchHoldCounts(JSONObject scan) {
        var counts = new java.util.TreeMap<String, Integer>();
        var holds = scan.optJSONObject("fetch_holds");
        if (holds != null) {
            var keys = holds.keys();
            while (keys.hasNext()) counts.merge(holds.optString(keys.next(), "unknown"), 1, Integer::sum);
        }
        return counts;
    }

    static boolean currentScreenVersion(JSONObject ledger) {
        var screen = ledger == null ? null : ledger.optJSONObject("reference_screen");
        var diagnostics = screen == null ? null : screen.optJSONObject("diagnostics");
        return screen != null && screen.has("meter_rows") && diagnostics != null
                && diagnostics.optInt("budget_count_version", 0) == 2
                && diagnostics.optInt("assessment_count_version", 0) == 2;
    }

    static boolean nonPositiveFinancials(JSONObject row) {
        try {
            return new BigDecimal(row.optString("profit")).signum() <= 0
                    || new BigDecimal(row.optString("equity")).signum() <= 0;
        } catch (NumberFormatException incomplete) {
            return false;
        }
    }

    static JSONObject screen(LocalDate day, String provider, String hash, JSONArray records,
                             Map<String, BigDecimal> prices, UsScreen.Fx fx, Map<String, LocalDate> splits)
            throws JSONException {
        int nyse = 0;
        int nasdaq = 0;
        var observations = new JSONArray();
        var splitHolds = new JSONArray();
        var meter = new JSONObject();
        int missingClose = 0, splitHoldCount = 0, unusableFinancials = 0;
        int outsideBudget = 0, outsideValuation = 0, referenceCount = 0, priorityCount = 0;
        int affordable100 = 0, singleShare = 0;
        int partialInsufficient = 0, partialWithinBudget = 0;
        int partialAssessed = 0, partialEligible = 0, strictAssessed = 0, strictEligible = 0;
        int[] flexibleTiers = new int[4], strictTiers = new int[4];
        var seen = new HashSet<String>();
        int nonPositiveProfit = 0, nonPositiveEquity = 0, nonPositiveBoth = 0, otherFinancialHold = 0;
        var rate = BigDecimal.valueOf(fx.yenPerDollar());
        for (int index = 0; index < records.length(); index++) {
            var row = records.getJSONObject(index);
            String symbol = row.getString("symbol");
            String exchange = row.getString("exchange");
            if (!seen.add(symbol)) throw new JSONException("Duplicate financial assessment symbol");
            var close = prices.get(symbol);
            if (close == null) { missingClose++; continue; }
            if (!row.optBoolean("partial_value")) {
                if ("NYSE".equals(exchange)) nyse++;
                else nasdaq++;
            }
            var split = splits.get(symbol);
            if (split != null && !split.isBefore(LocalDate.parse(row.getString("share_date")))) {
                splitHolds.put(symbol);
                splitHoldCount++;
                continue;
            }
            if (row.optBoolean("partial_value")) {
                var score=FlexibleValueMeter.assess(close,meterEps(row),meterCash(row),meterBalance(row));
                score=UsDisclosureEvidence.adjust(score,row,day);
                var yen=close.multiply(rate);
                int quantity=yen.movePointRight(2).compareTo(BUDGET)<=0?100:yen.compareTo(BUDGET)<=0?1:0;
                if(quantity==100) affordable100++; else if(quantity==1) singleShare++;
                if (score.confirmed() < 2) {
                    partialInsufficient++;
                    continue;
                }
                partialAssessed++;
                if(quantity>0 && score.level(ValueAlertMeter.DEFAULT)>0) {
                    partialEligible++; flexibleTiers[score.level(ValueAlertMeter.DEFAULT)]++;
                }
                if (quantity == 0) outsideBudget++;
                else partialWithinBudget++;
                observations.put(new JSONObject().put("symbol",symbol).put("exchange",exchange)
                    .put("cik",row.getInt("cik")).put("status","partial_assessed").put("quantity",quantity==0?1:quantity));
                meter.put(UsReferenceAlerts.meterKey(exchange,row.getInt("cik"),symbol),
                    new JSONArray().put(score.points()).put(score.ceiling()).put(score.confirmed()).put(quantity));
                continue;
            }
            var cap = close.multiply(new BigDecimal(row.getString("shares")));
            var profit = new BigDecimal(row.getString("profit"));
            var equity = new BigDecimal(row.getString("equity"));
            var level = ValueCandidateScreen.assess(cap, profit, equity);
            if (level == ValueCandidateScreen.Level.HELD) {
                unusableFinancials++;
                if (profit.signum() <= 0 && equity.signum() <= 0) nonPositiveBoth++;
                else if (profit.signum() <= 0) nonPositiveProfit++;
                else if (equity.signum() <= 0) nonPositiveEquity++;
                else otherFinancialHold++;
                continue;
            }
            strictAssessed++;
            var yen = close.multiply(rate);
            int quantity = yen.movePointRight(2).compareTo(BUDGET) <= 0 ? 100 : 1;
            if (quantity == 100) affordable100++;
            else if (yen.compareTo(BUDGET) <= 0) singleShare++;
            String status = yen.compareTo(BUDGET) > 0 ? "outside_budget" : switch (level) {
                case PRIORITY -> "priority";
                case REFERENCE -> "reference";
                default -> "outside_valuation";
            };
            switch (status) {
                case "outside_budget" -> outsideBudget++;
                case "outside_valuation" -> outsideValuation++;
                case "reference" -> referenceCount++;
                case "priority" -> priorityCount++;
                default -> throw new JSONException("Unknown financial screen state");
            }
            observations.put(new JSONObject().put("symbol", symbol).put("exchange", exchange)
                    .put("cik", row.getInt("cik")).put("status", status).put("quantity", quantity));
            var score = ValueAlertMeter.assessUs(cap, profit, equity, meterEps(row), meterCash(row), null, meterBalance(row));
            score = UsDisclosureEvidence.adjust(score, row, day);
            if (!"outside_budget".equals(status) && score.level(ValueAlertMeter.DEFAULT)>0) {
                strictEligible++; strictTiers[score.level(ValueAlertMeter.DEFAULT)]++;
            }
            meter.put(UsReferenceAlerts.meterKey(exchange, row.getInt("cik"), symbol),
                    new JSONArray().put(score.points()).put(score.ceiling()).put(score.confirmed())
                            .put("outside_budget".equals(status) ? 0 : quantity));
        }
        var diagnostics = new JSONObject()
                .put("financial_records", records.length())
                .put("missing_close", missingClose)
                .put("split_hold", splitHoldCount)
                .put("unusable_financials", unusableFinancials)
                .put("non_positive_profit_only", nonPositiveProfit)
                .put("non_positive_equity_only", nonPositiveEquity)
                .put("non_positive_both", nonPositiveBoth)
                .put("other_financial_hold", otherFinancialHold)
                .put("assessment_count_version", 2)
                .put("partial_insufficient", partialInsufficient)
                .put("partial_within_budget", partialWithinBudget)
                .put("strict_assessed",strictAssessed).put("strict_eligible_default",strictEligible)
                .put("partial_assessed",partialAssessed).put("partial_eligible_default",partialEligible)
                .put("total_assessed",strictAssessed+partialAssessed)
                .put("total_eligible_default",strictEligible+partialEligible)
                .put("strict_tiers",new JSONArray().put(strictTiers[1]).put(strictTiers[2]).put(strictTiers[3]))
                .put("flexible_tiers",new JSONArray().put(flexibleTiers[1]).put(flexibleTiers[2]).put(flexibleTiers[3]))
                .put("budget_count_version", 2)
                .put("outside_budget", outsideBudget)
                .put("outside_valuation", outsideValuation)
                .put("reference", referenceCount)
                .put("priority", priorityCount)
                .put("affordable_100", affordable100)
                .put("single_share", singleShare);
        var coverage = new JSONObject().put("NYSE", coverage(nyse)).put("Nasdaq", coverage(nasdaq));
        return new JSONObject().put("trading_date_et", day.toString()).put("close_provider", provider)
                .put("close_sha256", hash).put("coverage", coverage).put("split_holds", splitHolds)
                .put("reference_screen", new JSONObject().put("provider", provider).put("close_sha256", hash)
                        .put("fx_date", fx.date().toString()).put("observations", observations)
                        .put("diagnostics", diagnostics).put("meter_rows", meter));
    }

    static JSONObject scopedAssessment(LocalDate day, String source, String hash, JSONObject checkpoint,
                                       Map<String, BigDecimal> allPrices, UsScreen.Fx fx,
                                       Map<String, LocalDate> splits) throws JSONException {
        var listingDay = LocalDate.parse(checkpoint.getString("coverage_listing_date"));
        if (!listingDay.equals(day)) throw new JSONException("Expected a same-session listing scope");
        var symbols = checkpoint.getJSONArray("coverage_symbols");
        var scope = new java.util.HashSet<String>();
        for (int i = 0; i < symbols.length(); i++) {
            if (!scope.add(symbols.getString(i))) throw new JSONException("Duplicate listing symbol");
        }
        if (scope.isEmpty()) throw new JSONException("Listing scope is empty");
        var prices = new HashMap<>(allPrices);
        prices.keySet().retainAll(scope);
        var raw = checkpoint.getJSONArray("results");
        var records = new JSONArray();
        var recordsBySymbol = new HashMap<String, JSONObject>();
        for (int i = 0; i < raw.length(); i++) {
            var row = raw.getJSONObject(i);
            String symbol = row.getString("symbol");
            if (scope.contains(symbol)) {
                records.put(row);
                recordsBySymbol.put(symbol, row);
            }
        }
        var ledger = screen(day, source, hash, records, prices, fx, splits);
        var assessed = UsReferenceAlerts.read(ledger).rows();
        var diagnostics = ledger.getJSONObject("reference_screen").getJSONObject("diagnostics");
        int budget = 0, budgetAssessed = 0;
        var reasonCounts = new java.util.TreeMap<String, Integer>();
        var holds = checkpoint.optJSONObject("fetch_holds");
        var splitHolds = new java.util.HashSet<String>();
        var heldSplits = ledger.getJSONArray("split_holds");
        for (int i = 0; i < heldSplits.length(); i++) splitHolds.add(heldSplits.getString(i));
        for (String symbol : scope) {
            var price = prices.get(symbol);
            var financial = recordsBySymbol.get(symbol);
            if (price != null && price.multiply(BigDecimal.valueOf(fx.yenPerDollar())).compareTo(BUDGET) <= 0) {
                budget++;
                if (assessed.containsKey(symbol)) budgetAssessed++;
            }
            if (assessed.containsKey(symbol)) continue;
            String reason;
            if (price == null) reason = "missing_close";
            else if (splitHolds.contains(symbol)) reason = "split_hold";
            else if (financial != null && nonPositiveFinancials(financial)) reason = "non_positive_financials";
            else if (financial != null) reason = "insufficient_valuation_evidence";
            else reason = holds == null ? "financial_or_identity_unavailable"
                    : holds.optString(symbol, "financial_or_identity_unavailable");
            reasonCounts.merge(reason, 1, Integer::sum);
        }
        return diagnostics.put("trading_date", day.toString()).put("listing_date", listingDay.toString())
                .put("close_provider", source).put("close_sha256", hash)
                .put("scope", scope.size()).put("closes", prices.size())
                .put("unassessed", scope.size() - assessed.size())
                .put("full_scope_assessed_percent", 100.0 * assessed.size() / scope.size())
                .put("budget", budget).put("budget_assessed", budgetAssessed)
                .put("budget_assessed_percent", budget == 0 ? JSONObject.NULL : 100.0 * budgetAssessed / budget)
                .put("unassessed_reasons", new JSONObject(reasonCounts));
    }

    private static List<BigDecimal> meterEps(JSONObject row) {
        var history = row.optJSONArray("meter_eps");
        if (history == null || history.length() > 3) return List.of();
        var eps = new ArrayList<BigDecimal>();
        for (int index = 0; index < history.length(); index++) {
            var value = history.optString(index, "");
            try {
                eps.add(new BigDecimal(value));
            } catch (NumberFormatException invalid) {
                return List.of();
            }
        }
        return eps;
    }

    private static Integer meterCash(JSONObject row) {
        int cash = row.optInt("meter_cash", -1);
        return cash == 0 || cash == 50 || cash == 100 ? cash : null;
    }

    private static Integer meterBalance(JSONObject row) {
        int value = row.optInt("meter_balance", -1);
        return value == 0 || value == 50 || value == 70 || value == 100 ? value : null;
    }

    private static JSONObject coverage(int count) throws JSONException {
        return new JSONObject().put("with_close_and_reference_financials", count);
    }

    private UsDeviceFinancials() {}
}
