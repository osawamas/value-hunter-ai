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

    static JSONObject startScan(String hash, LocalDate day, JSONArray targets, JSONObject previous,
                                Set<Integer> changed) throws JSONException {
        var matching = new HashMap<String, JSONObject>();
        var fullRefresh = day;
        if (changed != null) {
            fullRefresh = LocalDate.parse(previous.getString("full_refresh_day"));
            var oldResults = previous.getJSONArray("results");
            for (int index = 0; index < oldResults.length(); index++) {
                var item = oldResults.getJSONObject(index);
                if (reusable(item, day) && !changed.contains(item.getInt("cik"))) {
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
            return !period.isBefore(day.minusDays(150)) && filed.isBefore(day);
        } catch (JSONException | DateTimeParseException invalid) {
            return false;
        }
    }

    static JSONObject financialRow(JSONObject target, JSONObject payload, LocalDate day) throws JSONException {
        int cik = target.getInt("cik");
        var figures = UsFinancialFacts.read(payload, cik, day);
        if (figures == null) return null;
        var history = UsFinancialFacts.meterHistory(payload, day);
        var eps = new JSONArray();
        for (var value : history.annualEps()) eps.put(value.toPlainString());
        return new JSONObject().put("meter_eps", eps).put("meter_cash", history.cash())
                .put("meter_balance", history.balance())
                .put("symbol", target.getString("symbol")).put("exchange", target.getString("exchange"))
                .put("cik", cik).put("share_date", figures.shareDate().toString())
                .put("equity_date", figures.equityDate().toString()).put("filed", figures.filed().toString())
                .put("profit_basis", figures.profitBasis())
                .put("shares", figures.shares().toPlainString()).put("profit", figures.profit().toPlainString())
                .put("equity", figures.equity().toPlainString());
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
        var rate = BigDecimal.valueOf(fx.yenPerDollar());
        for (int index = 0; index < records.length(); index++) {
            var row = records.getJSONObject(index);
            String symbol = row.getString("symbol");
            String exchange = row.getString("exchange");
            var close = prices.get(symbol);
            if (close == null) { missingClose++; continue; }
            if ("NYSE".equals(exchange)) nyse++;
            else nasdaq++;
            var split = splits.get(symbol);
            if (split != null && !split.isBefore(LocalDate.parse(row.getString("share_date")))) {
                splitHolds.put(symbol);
                splitHoldCount++;
                continue;
            }
            var cap = close.multiply(new BigDecimal(row.getString("shares")));
            var profit = new BigDecimal(row.getString("profit"));
            var equity = new BigDecimal(row.getString("equity"));
            var level = ValueCandidateScreen.assess(cap, profit, equity);
            if (level == ValueCandidateScreen.Level.HELD) { unusableFinancials++; continue; }
            var yen = close.multiply(rate);
            int quantity = yen.movePointRight(2).compareTo(BUDGET) <= 0 ? 100 : 1;
            if (quantity == 100) affordable100++; else singleShare++;
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
            var score = ValueAlertMeter.assess(cap, profit, equity, meterEps(row), meterCash(row), null, meterBalance(row));
            meter.put(UsReferenceAlerts.meterKey(exchange, row.getInt("cik"), symbol),
                    new JSONArray().put(score.points()).put(score.ceiling()).put(score.confirmed())
                            .put("outside_budget".equals(status) ? 0 : quantity));
        }
        var diagnostics = new JSONObject()
                .put("financial_records", records.length())
                .put("missing_close", missingClose)
                .put("split_hold", splitHoldCount)
                .put("unusable_financials", unusableFinancials)
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
