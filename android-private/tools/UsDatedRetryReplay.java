package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Replays the audited missing-close cohort with dated listing and private reference inputs. */
public final class UsDatedRetryReplay {
    private static final String LISTING_HOLD = "exact_dated_listing_pair_unavailable";
    private record ListingPair(UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq) {
        JSONObject snapshot(LocalDate day) {
            if (!day.equals(nyse.date()) || !day.equals(nasdaq.date())
                    || !UsMarketCoverage.sessionSnapshot(nyse.timestamp())
                    || !UsMarketCoverage.sessionSnapshot(nasdaq.timestamp())) return new JSONObject();
            return new JSONObject().put("day", day.toString()).put("time", nyse.timestamp().toString())
                    .put("nyse", new JSONObject(nyse.ordinaryNames()))
                    .put("nasdaq", new JSONObject(nasdaq.ordinaryNames()));
        }

        String exchange(String symbol) {
            if (nyse.symbols().contains(symbol)) return "NYSE";
            if (nasdaq.symbols().contains(symbol)) return "Nasdaq";
            return "";
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 1 || args.length > 2) {
            throw new IllegalArgumentException("Usage: UsDatedRetryReplay AUDIT_JSON [PRIVATE_INPUT_DIR]");
        }
        var audit = new JSONObject(Files.readString(Path.of(args[0])));
        System.out.println(run(audit, args.length == 2 ? Path.of(args[1]) : null).toString(2));
    }

    static JSONObject run(JSONObject audit, Path input) throws IOException {
        var day = LocalDate.parse(audit.getString("trading_date_et"));
        var prior = LocalDate.parse(audit.getString("comparison_date_et"));
        if (!UsDailyCloses.tradingDay(day)
                || !prior.equals(UsDailyCloses.onOrBeforeTradingDay(day.minusDays(1)))) {
            throw new IllegalArgumentException("Expected consecutive US trading dates");
        }
        var cohort = new TreeMap<String, JSONObject>();
        var auditRows = audit.getJSONArray("rows");
        for (int i = 0; i < auditRows.length(); i++) {
            var row = auditRows.getJSONObject(i);
            String symbol = row.getString("symbol");
            if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || cohort.put(symbol, row) != null) {
                throw new IllegalArgumentException("Invalid or duplicate audited symbol");
            }
        }

        var current = input == null ? null : listings(input, day);
        var comparison = input == null ? null : listings(input, prior);
        var exact = input == null ? Set.<String>of() : UsMarketCoverage.verifiedSupplementSymbols(
                comparison.snapshot(prior), current.snapshot(day), prior, day);
        var holds = new TreeMap<String, String>();
        var excluded = new TreeMap<String, String>();
        var eligible = new HashSet<String>();
        for (var entry : cohort.entrySet()) {
            String symbol = entry.getKey();
            var row = entry.getValue();
            String reason = row.getString("primary_reason");
            String disposition = row.getString("disposition");
            if ("excluded".equals(disposition)) excluded.put(symbol, reason);
            else if (!"held".equals(disposition)) throw new IllegalArgumentException("Unknown audit disposition");
            else if (!LISTING_HOLD.equals(reason)) holds.put(symbol, reason);
            else if (!exact.contains(symbol)) holds.put(symbol, LISTING_HOLD);
            else if (!current.exchange(symbol).equals(row.optString("exchange"))) {
                holds.put(symbol, "audited_exchange_mismatch");
            } else {
                eligible.add(symbol);
            }
        }
        var report = new JSONObject().put("trading_date_et", day.toString())
                .put("comparison_date_et", prior.toString()).put("audited_symbols", cohort.size())
                .put("recorded_provider_closes", cohort.values().stream()
                        .filter(row -> row.optBoolean("provider_close_on_trading_date")).count())
                .put("dated_listing_pairs_supplied", input != null)
                .put("eligible_for_replay", eligible.size()).put("excluded", new JSONObject(excluded));
        if (eligible.isEmpty()) {
            var empty = counts(0, 0, 0);
            report.put("before", empty).put("after", empty).put("increase", empty)
                    .put("additional_alert_candidates", new JSONArray()).put("repeated_alert_candidates", 0);
        } else {
            compare(input, report, current, cohort, eligible, holds, prior, day);
        }
        return report.put("held", new JSONObject(holds));
    }

    private static void compare(Path input, JSONObject report, ListingPair current, Map<String, JSONObject> cohort,
                                Set<String> eligible, Map<String, String> holds, LocalDate prior, LocalDate day)
            throws IOException {
        var bars = UsRetryReplay.response(input, "closes.json").getJSONArray("rows");
        var priorQuotes = cohortQuotes(bars, prior, eligible);
        var quotes = cohortQuotes(bars, day, eligible);
        var targets = new HashMap<String, JSONObject>();
        var registrations = UsDeviceFinancials.targets(current.nyse(), current.nasdaq(),
                UsRetryReplay.json(input, "sec.json"), eligible);
        for (int i = 0; i < registrations.length(); i++) {
            var row = registrations.getJSONObject(i);
            String symbol = row.getString("symbol");
            if (row.getInt("cik") == cohort.get(symbol).optInt("cik")) targets.put(symbol, row);
        }

        var rates = new JSONArray(Files.readString(input.resolve("fx.json")));
        var priorSplits = new HashMap<String, LocalDate>();
        var splits = new HashMap<String, LocalDate>();
        var splitRows = UsRetryReplay.response(input, "splits.json").getJSONArray("rows");
        for (int i = 0; i < splitRows.length(); i++) {
            var row = splitRows.getJSONObject(i);
            var effective = LocalDate.parse(row.getString("split_date"));
            String symbol = row.getString("symbol");
            if (!effective.isAfter(prior)) priorSplits.merge(symbol, effective, UsDatedRetryReplay::latest);
            if (!effective.isAfter(day)) splits.merge(symbol, effective, UsDatedRetryReplay::latest);
        }
        var priorStage = UsRetryReplay.screen(prior, priorQuotes, facts(input, targets, prior, priorQuotes.keySet()), rates, priorSplits);
        var before = UsRetryReplay.screen(day, quotes, facts(input, targets, day, quotes.keySet()), rates, splits);

        var bySymbol = new HashMap<String, JSONArray>();
        var supplement = UsRetryReplay.response(input, "supplement.json").getJSONArray("rows");
        for (int i = 0; i < supplement.length(); i++) {
            var row = supplement.getJSONObject(i);
            String symbol = row.getString("symbol");
            if (eligible.contains(symbol) && !quotes.containsKey(symbol)) {
                bySymbol.computeIfAbsent(symbol, unused -> new JSONArray()).put(row);
            }
        }
        for (var entry : bySymbol.entrySet()) {
            var reply = new JSONObject().put("query_execution_status", "Success").put("rows", entry.getValue());
            var validated = UsDoltCloses.supplement(day, Set.of(entry.getKey()), unused -> reply);
            quotes.putAll(UsDeviceFinancials.prices(validated));
        }

        var afterFacts = facts(input, targets, day, quotes.keySet());
        var after = UsRetryReplay.screen(day, quotes, afterFacts, rates, splits);
        var financials = new HashMap<String, JSONObject>();
        for (int i = 0; i < afterFacts.length(); i++) {
            var row = afterFacts.getJSONObject(i);
            financials.put(row.getString("symbol"), row);
        }
        for (var symbol : eligible) {
            if (!quotes.containsKey(symbol)) holds.put(symbol, "trade_date_close_unavailable");
            else if (!targets.containsKey(symbol)) holds.put(symbol, "sec_issuer_not_verified");
            else if (!financials.containsKey(symbol)) holds.put(symbol, "financials_or_shares_unavailable");
            else if (UsDeviceFinancials.nonPositiveFinancials(financials.get(symbol))) {
                holds.put(symbol, "nonpositive_financials");
            } else if (!after.screen().rows().containsKey(symbol)) holds.put(symbol, "split_basis_pending");
        }

        var initial = UsReferenceAlerts.entrantRows(priorStage.screen(), before.screen(), Set.of());
        var added = UsReferenceAlerts.entrantRows(priorStage.screen(), after.screen(), initial.keySet());
        var seen = new HashSet<>(initial.keySet());
        seen.addAll(added.keySet());
        var repeated = UsReferenceAlerts.entrantRows(priorStage.screen(), after.screen(), seen);
        report.put("before", counts(before.closes(), before.screen().rows().size(), initial.size()))
                .put("after", counts(after.closes(), after.screen().rows().size(), seen.size()))
                .put("increase", counts(after.closes() - before.closes(),
                        after.screen().rows().size() - before.screen().rows().size(), added.size()))
                .put("additional_alert_candidates", new JSONArray(new java.util.TreeSet<>(added.keySet())))
                .put("repeated_alert_candidates", repeated.size());
    }

    private static LocalDate latest(LocalDate left, LocalDate right) {
        return left.isAfter(right) ? left : right;
    }

    private static JSONObject counts(int closes, int screened, int candidates) {
        return new JSONObject().put("closes", closes).put("screened", screened).put("alert_candidates", candidates);
    }

    private static ListingPair listings(Path input, LocalDate day) throws IOException {
        return new ListingPair(UsMarketCoverage.directory(Files.readString(input.resolve(day + "-nyse.txt")), false),
                UsMarketCoverage.directory(Files.readString(input.resolve(day + "-nasdaq.txt")), true));
    }

    private static Map<String, BigDecimal> cohortQuotes(JSONArray bars, LocalDate date, Set<String> eligible) {
        var selected = new JSONArray();
        for (int i = 0; i < bars.length(); i++) {
            var row = bars.getJSONObject(i);
            if (date.toString().equals(row.getString("trading_date")) && eligible.contains(row.getString("symbol"))) {
                selected.put(row);
            }
        }
        return selected.isEmpty() ? new HashMap<>() : UsRetryReplay.closes(selected, date);
    }

    private static JSONArray facts(Path input, Map<String, JSONObject> targets, LocalDate date, Set<String> priced)
            throws IOException {
        var results = new JSONArray();
        for (var symbol : priced) {
            var target = targets.get(symbol);
            if (target == null) continue;
            var path = input.resolve("CIK%010d.json".formatted(target.getInt("cik")));
            if (!Files.isRegularFile(path)) continue;
            var row = UsDeviceFinancials.financialRow(target, new JSONObject(Files.readString(path)), date);
            if (row != null) results.put(row);
        }
        return results;
    }
}
