package jp.valuehunter.privatewatch;

import android.util.AtomicFile;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.DateTimeException;
import java.util.HashSet;
import java.util.Set;

/** Keeps the dates supplied by the exchange directory, even when prices arrive the next day. */
final class UsListingHistory {
    record Markets(Set<String> nyse, Set<String> nasdaq) {}
    record Scope(Set<String> ordinary, Set<String> nasdaq, boolean exactDates) {}

    private UsListingHistory() {}

    static synchronized JSONObject remember(File directory, UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq)
            throws JSONException {
        UsPriceOnlyBudget.ordinary(nyse, nasdaq, nyse.date());
        preserveIdentities(directory, nyse, nasdaq);
        var file = new AtomicFile(new File(directory, "us-listing-dates.json"));
        var saved = read(file);
        var newest = nyse.date();
        var keys = saved.keys();
        while (keys.hasNext()) {
            try {
                var day = LocalDate.parse(keys.next());
                if (day.isBefore(newest.minusDays(14))) {
                    keys.remove();
                    identityFile(directory, day).delete();
                }
            } catch (DateTimeException invalid) {
                keys.remove();
            }
        }
        var sameDay = markets(saved.optJSONObject(newest.toString()));
        if (sameDay != null && sameDay.nyse().equals(nyse.symbols()) && sameDay.nasdaq().equals(nasdaq.symbols())) {
            return saved;
        }
        saved.put(newest.toString(), new JSONObject().put("nyse", new JSONArray(nyse.symbols()))
                .put("nasdaq", new JSONArray(nasdaq.symbols())));
        try {
            UsDailyWorker.writeSnapshot(file, saved);
        } catch (IOException unavailable) {
            // Current authoritative data can still be used in this run.
        }
        return saved;
    }

    private static AtomicFile identityFile(File directory, LocalDate day) {
        return new AtomicFile(new File(directory, "us-listing-identity-" + day + ".json"));
    }

    static synchronized boolean hasIdentity(File directory, LocalDate day) {
        return hasSessionEvidence(read(identityFile(directory, day)), day);
    }

    static synchronized boolean capture(File directory, LocalDate day, java.time.LocalTime now,
                                        UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq)
            throws JSONException {
        if (!day.equals(nyse.date()) || !day.equals(nasdaq.date())
                || !sessionSnapshot(nyse.timestamp()) || !sessionSnapshot(nasdaq.timestamp())
                || nyse.timestamp().isAfter(now) || nasdaq.timestamp().isAfter(now)) return false;
        remember(directory, nyse, nasdaq);
        return hasIdentity(directory, day);
    }

    private static boolean sessionSnapshot(java.time.LocalTime time) {
        // The evening distribution describes the upcoming session.
        return time != null && !time.isBefore(java.time.LocalTime.of(9, 30))
                && time.isBefore(java.time.LocalTime.of(20, 45));
    }

    private static void preserveIdentities(File directory, UsMarketCoverage.Directory nyse,
                                           UsMarketCoverage.Directory nasdaq) {
        if (!sessionSnapshot(nyse.timestamp()) || !sessionSnapshot(nasdaq.timestamp())
                || !UsDailyCloses.tradingDay(nyse.date())
                || !nyse.ordinaryNames().keySet().equals(nyse.symbols())
                || !nasdaq.ordinaryNames().keySet().equals(nasdaq.symbols())) return;
        var file = identityFile(directory, nyse.date());
        try {
            var timestamp = nyse.timestamp().isBefore(nasdaq.timestamp()) ? nyse.timestamp() : nasdaq.timestamp();
            String latest = read(file).optString("time");
            if (!latest.isEmpty() && timestamp.isBefore(java.time.LocalTime.parse(latest))) return;
            var snapshot = new JSONObject().put("day", nyse.date().toString()).put("time", timestamp.toString())
                    .put("nyse", new JSONObject(nyse.ordinaryNames())).put("nasdaq", new JSONObject(nasdaq.ordinaryNames()));
            UsDailyWorker.writeSnapshot(file, snapshot);
        } catch (IOException | JSONException | DateTimeException unavailable) {
            // The general coverage counts still use the verified listing sets.
        }
    }

    static synchronized Set<String> verifiedSupplementSymbols(File directory, LocalDate day) {
        var previous = UsPriceOnlyBudget.previousSession(day);
        return verifiedSupplementSymbols(read(identityFile(directory, previous)), read(identityFile(directory, day)),
                previous, day);
    }

    private static boolean hasSessionEvidence(JSONObject snapshot, LocalDate day) {
        if (!day.toString().equals(snapshot.optString("day"))) return false;
        try {
            return sessionSnapshot(java.time.LocalTime.parse(snapshot.optString("time")));
        } catch (DateTimeException invalid) {
            return false;
        }
    }

    static Set<String> verifiedSupplementSymbols(JSONObject before, JSONObject after, LocalDate previous, LocalDate day) {
        if (!hasSessionEvidence(before, previous) || !hasSessionEvidence(after, day)) {
            return Set.of();
        }
        var result = new HashSet<String>();
        for (String exchange : java.util.List.of("nyse", "nasdaq")) {
            String other = "nyse".equals(exchange) ? "nasdaq" : "nyse";
            var old = before.optJSONObject(exchange);
            var current = after.optJSONObject(exchange);
            var oldOther = before.optJSONObject(other);
            var currentOther = after.optJSONObject(other);
            if (old == null || current == null || oldOther == null || currentOther == null) return Set.of();
            var tickers = current.keys();
            while (tickers.hasNext()) {
                String ticker = tickers.next();
                var identity = current.opt(ticker);
                if (identity instanceof String name && !name.isEmpty() && ticker.matches("[A-Z0-9.$+^=/_-]{1,24}")
                        && !oldOther.has(ticker) && !currentOther.has(ticker) && name.equals(old.opt(ticker))) {
                    result.add(ticker);
                }
            }
        }
        return Set.copyOf(result);
    }

    static Scope scope(JSONObject dates, LocalDate previous, LocalDate latest,
                       UsMarketCoverage.Directory fallbackNyse, UsMarketCoverage.Directory fallbackNasdaq)
            throws JSONException {
        var before = markets(dates.optJSONObject(previous.toString()));
        var after = markets(dates.optJSONObject(latest.toString()));
        if (before == null || after == null) {
            if (after == null) return new Scope(UsPriceOnlyBudget.ordinary(fallbackNyse, fallbackNasdaq, latest),
                    fallbackNasdaq.symbols(), false);
            return new Scope(union(after.nyse(), after.nasdaq()), after.nasdaq(), false);
        }
        var nyse = new HashSet<>(after.nyse());
        nyse.retainAll(before.nyse());
        var nasdaq = new HashSet<>(after.nasdaq());
        nasdaq.retainAll(before.nasdaq());
        return new Scope(union(nyse, nasdaq), Set.copyOf(nasdaq), true);
    }

    record DatedScope(LocalDate day, Set<String> symbols) {}

    static DatedScope coverageScope(JSONObject dates, LocalDate tradeDay, UsMarketCoverage.Directory nyse,
                                    UsMarketCoverage.Directory nasdaq) throws JSONException {
        var exact = markets(dates.optJSONObject(tradeDay.toString()));
        if (exact != null) return new DatedScope(tradeDay, union(exact.nyse(), exact.nasdaq()));
        return new DatedScope(nyse.date(), UsPriceOnlyBudget.ordinary(nyse, nasdaq, tradeDay));
    }

    static DatedScope retainedScope(File directory, LocalDate tradeDay) {
        var saved = read(new AtomicFile(new File(directory, "us-listing-dates.json")));
        for (int offset = 0; offset <= 4; offset++) {
            var date = tradeDay.plusDays(offset);
            var entries = markets(saved.optJSONObject(date.toString()));
            if (entries != null) return new DatedScope(date, union(entries.nyse(), entries.nasdaq()));
        }
        return null;
    }

    private static JSONObject read(AtomicFile file) {
        try {
            return new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
        } catch (IOException | JSONException unavailable) {
            return new JSONObject();
        }
    }

    private static Markets markets(JSONObject saved) {
        if (saved == null) return null;
        try {
            var nyse = symbols(saved.getJSONArray("nyse"));
            var nasdaq = symbols(saved.getJSONArray("nasdaq"));
            if (!java.util.Collections.disjoint(nyse, nasdaq)) return null;
            return new Markets(nyse, nasdaq);
        } catch (JSONException invalid) {
            return null;
        }
    }

    private static Set<String> symbols(JSONArray array) throws JSONException {
        if (array.length() == 0 || array.length() > 30_000) throw new JSONException("Invalid US listing count");
        var result = new HashSet<String>();
        for (int i = 0; i < array.length(); i++) {
            String ticker = array.getString(i);
            if (!ticker.matches("[A-Z0-9.$+^=/_-]{1,24}") || !result.add(ticker))
                throw new JSONException("Invalid US listing symbol");
        }
        return Set.copyOf(result);
    }

    private static Set<String> union(Set<String> nyse, Set<String> nasdaq) {
        var symbols = new HashSet<>(nyse);
        symbols.addAll(nasdaq);
        return Set.copyOf(symbols);
    }
}
