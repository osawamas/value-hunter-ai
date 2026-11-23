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
        byte[] quoteBytes = UsDailyWorker.readQuote(file);
        var close = new JSONObject(new String(quoteBytes, StandardCharsets.UTF_8));
        String quoteHash = UsReferenceAlerts.sha256(quoteBytes);
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
        String listingHash = listingEvidenceHash(sameDay, paired, groups, prior);
        var saved = matchingEvidenceCheckpoint(read(state, day.toString()), quoteHash, listingHash);
        var results = saved.optJSONObject("results");
        if (results == null) results = new JSONObject();
        // Recompute damaged checkpoint values rather than treating their mere
        // presence as an already-completed screening verdict.
        discardInvalidVerdicts(results, eligible);
        saved.put("eligible", eligible.size());
        long now = System.currentTimeMillis();
        if (eligible.isEmpty() || saved.optLong("after") > now) {
            if (!stopped.getAsBoolean()) saveIfEvidenceUnchanged(state, day, saved, results, file, quoteHash, directory, listingHash);
            return;
        }

        var remaining = new ArrayList<String>();
        for (var symbol : eligible) {
            if (!results.has(symbol)) remaining.add(symbol);
        }
        if (stopped.getAsBoolean()) return;
        if (remaining.isEmpty()) {
            saveIfEvidenceUnchanged(state, day, saved, results, file, quoteHash, directory, listingHash);
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
        saveIfEvidenceUnchanged(state, day, saved, results, file, quoteHash, directory, listingHash);
    }

    static void discardInvalidVerdicts(JSONObject results, Set<String> eligible) {
        var recorded = results.keys();
        while (recorded.hasNext()) {
            String symbol = recorded.next();
            Object verdict = results.opt(symbol);
            if (!eligible.contains(symbol) || !(verdict instanceof String)
                    || (!"WITHIN".equals(verdict) && !"OUTSIDE".equals(verdict))) {
                recorded.remove();
            }
        }
    }

    // A corrected same-session close changes the evidence used by the budget
    // comparison. Never reuse an old cursor, cooldown or verdict after it changes.
    static JSONObject matchingQuoteCheckpoint(JSONObject saved, String quoteHash) throws JSONException {
        if (quoteHash.isEmpty() || !quoteHash.equals(saved.optString("quote_sha256"))) {
            return new JSONObject().put("quote_sha256", quoteHash);
        }
        return saved;
    }

    // Listing identity and the available prior-session symbols can change
    // without changing today's quote bytes. Invalidate their old verdicts too.
    static JSONObject matchingEvidenceCheckpoint(JSONObject saved, String quoteHash, String listingHash)
            throws JSONException {
        var current = matchingQuoteCheckpoint(saved, quoteHash);
        if (listingHash.isEmpty() || !listingHash.equals(current.optString("listing_sha256"))) {
            return new JSONObject().put("quote_sha256", quoteHash)
                    .put("listing_sha256", listingHash);
        }
        return current;
    }

    static String listingEvidenceHash(java.util.Map<String, String> exchanges, Set<String> paired,
                                      java.util.Map<MarketCoverage.Reason, List<String>> groups,
                                      Set<String> prior) {
        var canonical = new StringBuilder();
        new java.util.TreeMap<>(exchanges).forEach((symbol, venue) ->
                canonical.append("venue:").append(symbol.length()).append(':').append(symbol)
                        .append(venue.length()).append(':').append(venue).append(';'));
        new java.util.TreeSet<>(paired).forEach(symbol ->
                canonical.append("paired:").append(symbol.length()).append(':').append(symbol).append(';'));
        for (var reason : MarketCoverage.Reason.values()) {
            var symbols = groups.getOrDefault(reason, List.of());
            for (String symbol : new java.util.TreeSet<>(symbols)) {
                canonical.append("group:").append(reason.name()).append(':')
                        .append(symbol.length()).append(':').append(symbol).append(';');
            }
        }
        new java.util.TreeSet<>(prior).forEach(symbol ->
                canonical.append("prior:").append(symbol.length()).append(':').append(symbol).append(';'));
        return UsReferenceAlerts.sha256(canonical.toString().getBytes(StandardCharsets.UTF_8));
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

    // Corrections can arrive while the supplemental prices or FX data are fetched.
    // Serialize this final evidence check with UsDailyWorker's atomic quote writes.
    private static void saveIfEvidenceUnchanged(SharedPreferences state, LocalDate day,
                                                JSONObject saved, JSONObject results,
                                                AtomicFile quoteFile, String quoteHash,
                                                File directory, String listingHash)
            throws IOException, JSONException {
        synchronized (UsDailyWorker.QUOTE_LOCK) {
            if (!matchesSavedQuote(quoteHash, UsDailyWorker.readQuote(quoteFile))) {
                throw new IOException("Daily close changed during single-session budget screening");
            }
            // The listing and prior-session evidence is separate from the close
            // file and can change while supplemental quotes / FX are downloaded.
            String currentListingHash = listingEvidenceHash(
                    UsListingHistory.sessionExchanges(directory, day),
                    UsListingHistory.verifiedSupplementSymbols(directory, day),
                    MarketCoverage.US.groups(state), priorPrices(directory, day));
            if (!matchesEvidenceHash(listingHash, currentListingHash)) {
                throw new IOException("Listing or prior-session evidence changed during budget screening");
            }
            if (!state.edit().putString(STATE, saved.put("day", day.toString())
                    .put("results", results).toString()).commit()) {
                throw new IOException("Could not persist single-session budget checkpoint");
            }
        }
    }

    static boolean matchesEvidenceHash(String originalHash, String currentHash) {
        return !originalHash.isEmpty() && originalHash.equals(currentHash);
    }

    static boolean matchesSavedQuote(String originalHash, byte[] currentBytes) {
        return !originalHash.isEmpty()
                && originalHash.equals(UsReferenceAlerts.sha256(currentBytes));
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

    static boolean displayEvidenceMatches(JSONObject saved, byte[] quote, String listingHash) {
        return matchesSavedQuote(saved.optString("quote_sha256"), quote)
                && matchesEvidenceHash(saved.optString("listing_sha256"), listingHash);
    }

    static String display(Context context, SharedPreferences state, String day, String provider) {
        if (!UsDoltCloses.SOURCE.equals(provider)) return "";
        var saved = read(state, day);
        // Display is a separate entry point from the worker. It must not show
        // verdicts from a checkpoint invalidated since the last worker run.
        if (saved.optInt("eligible") > 0) {
            try {
                File directory = context.getNoBackupFilesDir();
                var quoteFile = new AtomicFile(new File(directory, "us-daily-closes.json"));
                byte[] quote = UsDailyWorker.readQuote(quoteFile);
                String listingHash = listingEvidenceHash(
                        UsListingHistory.sessionExchanges(directory, LocalDate.parse(day)),
                        UsListingHistory.verifiedSupplementSymbols(directory, LocalDate.parse(day)),
                        MarketCoverage.US.groups(state), priorPrices(directory, LocalDate.parse(day)));
                if (!displayEvidenceMatches(saved, quote, listingHash)) {
                    return day + " 当日の予算チェック · 根拠データ更新のため再検証待ち";
                }
            } catch (IOException | JSONException | java.time.format.DateTimeParseException unavailable) {
                return day + " 当日の予算チェック · 保存データの再検証待ち";
            }
        }
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
