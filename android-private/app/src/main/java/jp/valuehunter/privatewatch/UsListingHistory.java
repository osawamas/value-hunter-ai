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

    static JSONObject remember(File directory, UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq)
            throws JSONException {
        UsPriceOnlyBudget.ordinary(nyse, nasdaq, nyse.date());
        var file = new AtomicFile(new File(directory, "us-listing-dates.json"));
        JSONObject saved;
        try {
            saved = new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
        } catch (IOException | JSONException unavailable) {
            saved = new JSONObject();
        }
        var newest = nyse.date();
        var keys = saved.keys();
        while (keys.hasNext()) {
            try {
                var day = LocalDate.parse(keys.next());
                if (day.isBefore(newest.minusDays(14))) keys.remove();
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

    static Scope scope(JSONObject dates, LocalDate previous, LocalDate latest,
                       UsMarketCoverage.Directory fallbackNyse, UsMarketCoverage.Directory fallbackNasdaq)
            throws JSONException {
        if (!previous.isBefore(latest)) throw new IllegalArgumentException("US sessions must increase");
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
