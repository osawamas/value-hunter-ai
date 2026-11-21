package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.AtomicFile;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/** Keeps single-session reference checks separate from the close cache and notification state. */
final class UsSingleSessionBudgetCheck {
    private static final String STATE = "us_single_session_budget";
    private static final int BATCH = 100;

    static void run(Context context, LocalDate day, BooleanSupplier stopped, UsDoltCloses.Download download)
            throws IOException, JSONException {
        var latest = UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(Instant.now()));
        if (!day.equals(latest)) return;
        var state = ScanWorker.prefs(context);
        if (!day.equals(MarketCoverage.US.day(state))) return;
        var directory = context.getNoBackupFilesDir();
        var file = new AtomicFile(new File(directory, "us-daily-closes.json"));
        var close = new JSONObject(new String(UsDailyWorker.readQuote(file), StandardCharsets.UTF_8));
        if (!day.toString().equals(close.optString("trading_date_et"))
                || !UsDoltCloses.SOURCE.equals(close.optString("source"))) return;
        var groups = MarketCoverage.US.groups(state);
        var pending = new HashSet<>(groups.getOrDefault(MarketCoverage.Reason.CLOSE, List.of()));
        pending.addAll(groups.getOrDefault(MarketCoverage.Reason.DATED_LISTING, List.of()));
        var sameDay = UsListingHistory.sessionExchanges(directory, day);
        var paired = UsListingHistory.verifiedSupplementSymbols(directory, day);
        var eligible = UsSingleSessionBudget.targets(pending, sameDay, paired);
        var prices = UsDeviceFinancials.prices(close.getJSONArray("closes"));
        eligible.removeAll(prices.keySet());
        var prior = priorPrices(directory, day);
        // Price-only comparison may lack its older close even when today's close is already saved.
        for (var reason : List.of(MarketCoverage.Reason.FINANCIALS, MarketCoverage.Reason.IDENTIFICATION,
                MarketCoverage.Reason.DOWNLOAD, MarketCoverage.Reason.VALUATION)) {
            UsSingleSessionBudget.addUnpairedCurrentOnly(eligible,
                    new HashSet<>(groups.getOrDefault(reason, List.of())), sameDay,
                    paired, prices.keySet(), prior);
        }
        var saved = read(state, day.toString());
        var results = saved.optJSONObject("results");
        if (results == null) results = new JSONObject();
        // An official close or a completed paired check supersedes the reference result.
        var recorded = results.keys();
        while (recorded.hasNext()) {
            if (!eligible.contains(recorded.next())) recorded.remove();
        }
        saved.put("eligible", eligible.size());
        long now = System.currentTimeMillis();
        if (eligible.isEmpty() || saved.optLong("after") > now) {
            if (!stopped.getAsBoolean()) save(state, day, saved, results);
            return;
        }

        var remaining = new ArrayList<String>();
        for (var symbol : eligible) {
            if (!results.has(symbol)) remaining.add(symbol);
        }
        if (stopped.getAsBoolean()) return;
        if (remaining.isEmpty()) {
            save(state, day, saved, results);
            return;
        }
        String cursor = saved.optString("cursor");
        remaining.sort(java.util.Comparator.comparing((String code) -> code.compareTo(cursor) <= 0)
                .thenComparing(java.util.Comparator.naturalOrder()));
        var batch = remaining.subList(0, Math.min(BATCH, remaining.size()));
        var missing = new HashSet<>(batch);
        missing.removeAll(prices.keySet());
        if (!missing.isEmpty()) {
            if (stopped.getAsBoolean()) return;
            var response = UsDoltCloses.supplement(day, missing, download);
            if (response.length() > 0) prices.putAll(UsDeviceFinancials.prices(response));
        }
        if (stopped.getAsBoolean()) return;
        if (batch.stream().anyMatch(prices::containsKey)) {
            var fx = UsSecFinanceWorker.tradeDateFx(new JSONArray(UsDailyWorker.fetchText(
                    UsSecFinanceWorker.FX + "&from=" + day + "&to=" + day, "")), day);
            if (stopped.getAsBoolean()) return;
            for (var symbol : batch) {
                var verdict = UsSingleSessionBudget.check(day, fx, prices.get(symbol));
                if (verdict != UsSingleSessionBudget.Verdict.HELD) results.put(symbol, verdict.name());
            }
        }
        saved.put("after", now + TimeUnit.HOURS.toMillis(1)).put("cursor", batch.get(batch.size() - 1));
        if (stopped.getAsBoolean()) return;
        if (!sameDay.equals(UsListingHistory.sessionExchanges(directory, day))
                || !paired.equals(UsListingHistory.verifiedSupplementSymbols(directory, day))
                || !groups.equals(MarketCoverage.US.groups(state))) {
            throw new IOException("Reference budget evidence changed during acquisition");
        }
        save(state, day, saved, results);
    }

    static boolean hasPublishedResult(SharedPreferences state, LocalDate day) {
        return read(state, day.toString()).optInt("eligible") > 0;
    }

    private static Set<String> priorPrices(File directory, LocalDate day) throws IOException, JSONException {
        var file = new AtomicFile(new File(directory, UsDailyWorker.PREVIOUS_QUOTE_FILE));
        try {
            var quote = new JSONObject(new String(UsDailyWorker.readQuote(file), StandardCharsets.UTF_8));
            if (UsDoltCloses.SOURCE.equals(quote.optString("source"))
                    && UsPriceOnlyBudget.previousSession(day).toString().equals(quote.optString("trading_date_et"))) {
                return UsDeviceFinancials.prices(quote.getJSONArray("closes")).keySet();
            }
        } catch (FileNotFoundException absent) {
            // Today's budget can be checked during the first run.
        }
        return Set.of();
    }

    private static void save(SharedPreferences state, LocalDate day, JSONObject saved, JSONObject results)
            throws JSONException {
        state.edit().putString(STATE, saved.put("day", day.toString()).put("results", results).toString()).apply();
    }

    private static JSONObject read(SharedPreferences state, String day) {
        try {
            var saved = new JSONObject(state.getString(STATE, "{}"));
            if (day.equals(saved.optString("day"))) return saved;
        } catch (JSONException invalid) {
            // Resume with an empty state if the old result cannot be read.
        }
        return new JSONObject();
    }

    static String display(SharedPreferences state, String day, String provider) {
        if (!UsDoltCloses.SOURCE.equals(provider)) return "";
        var saved = read(state, day);
        var results = saved.optJSONObject("results");
        int eligible = saved.optInt("eligible");
        if (results == null || eligible == 0) return "";
        int within = 0;
        int outside = 0;
        var symbols = results.keys();
        while (symbols.hasNext()) {
            String verdict = results.optString(symbols.next());
            if ("WITHIN".equals(verdict)) within++;
            else if ("OUTSIDE".equals(verdict)) outside++;
        }
        return day + " 当日の予算チェック（DoltHub参考終値・100株10万円）\n"
                + "予算内 " + within + "銘柄 · 予算外 " + outside + "銘柄 · 終値確認待ち "
                + Math.max(0, eligible - within - outside) + "銘柄";
    }
}
