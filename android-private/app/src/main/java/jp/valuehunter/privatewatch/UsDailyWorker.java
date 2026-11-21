package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.AtomicFile;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.concurrent.TimeUnit;


public final class UsDailyWorker extends Worker {
    private static final String WORK = "us-daily-closes";
    private static final String KEY_FILE = "massive-key.txt";
    private static final String VALUATION_DATE = "us_pilot_valuation_day";
    private static final String VALUATION_SOURCE = "us_pilot_valuation_source";
    private static final String VALUATION_TEXT = "us_pilot_valuation_text";
    private static final String VALUATION_RETRY = "us_pilot_valuation_retry";
    private static final String HISTORY_MONTH = "us_pilot_history_month";
    private static final String HISTORY_TEXT = "us_pilot_history_text";
    private static final String HISTORY_CURSOR = "us_pilot_history_cursor";
    private static final String MARKET_DATE = "us_market_coverage_date";
    private static final String MARKET_SOURCE = "us_market_coverage_source";
    private static final String MARKET_TEXT = "us_market_coverage_text";
    private static final String STATUS = "us_massive_daily_status";
    private static final String PROVIDER = "us_daily_close_provider";
    private static final String MASSIVE = UsDailyCloses.MASSIVE_SOURCE;
    private static final Object CHECK_LOCK = new Object();
    static final String ON_WIFI = "us-daily-closes-wifi-resume";
    static final Object QUOTE_LOCK = new Object();
    static final String PRIVATE_STATUS = "us_private_sec_status";
    private static final String PRIVATE_BASELINE = "us_private_sec_baseline";
    private static final String PRIVATE_PENDING = "us_private_sec_pending";
    private static final int US_NOTIFICATION_ID = 6;
    static final String PREVIOUS_QUOTE_FILE = "us-previous-daily-closes.json";
    static final String PRICE_ONLY_STATUS = "us_price_only_status";
    static final String PRICE_ONLY_DAY = "us_price_only_day";
    private static final String DATE = "us_massive_daily_close_date";
    private static final String COUNT = "us_massive_daily_close_count";
    private static final String ENDPOINT =
            "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/";

    public UsDailyWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    static void schedule(Context context) {
        if (!MarketNetwork.requested()) return;
        var workManager = WorkManager.getInstance(context);
        var request = new PeriodicWorkRequest.Builder(UsDailyWorker.class, 6, TimeUnit.HOURS)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .build();
        workManager.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
    }

    static void checkNow(Context context) {
        if (!MarketNetwork.allowed()) return;
        var request = new OneTimeWorkRequest.Builder(UsDailyWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED)).build();
        WorkManager.getInstance(context).enqueueUniqueWork(ON_WIFI, ExistingWorkPolicy.KEEP, request);
    }

    static String displayStatus(SharedPreferences state) {
        String status = state.getString(STATUS, "初回の自動更新待ち");
        String day = state.getString(DATE, "");
        if (day.isEmpty()) return status;
        String source = MASSIVE.equals(state.getString(PROVIDER, "")) ? "Massive" : "DoltHub参考値";
        String result = status + "\n取得済み " + day + "（米東部） · " + source + " "
                + state.getInt(COUNT, 0) + "件";
        if (day.equals(state.getString(MARKET_DATE, ""))
                && state.getString(PROVIDER, "").equals(state.getString(MARKET_SOURCE, ""))) {
            result += "\n\n" + state.getString(MARKET_TEXT, "");
        }
        if (day.equals(state.getString(VALUATION_DATE, ""))
                && state.getString(PROVIDER, "").equals(state.getString(VALUATION_SOURCE, ""))) {
            result += "\n\n" + state.getString(VALUATION_TEXT, "");
        }
        String privateStatus = state.getString(PRIVATE_STATUS, "米国株の財務取得はWi-Fi接続時に開始");
        if (!privateStatus.isEmpty()) result += "\n\n" + privateStatus;
        if (day.equals(state.getString(PRICE_ONLY_DAY, ""))) {
            result += "\n\n" + state.getString(PRICE_ONLY_STATUS, "");
        }
        if (day.length() >= 7 && day.substring(0, 7).equals(state.getString(HISTORY_MONTH, ""))) {
            result += "\n\n" + state.getString(HISTORY_TEXT, "");
        }
        return result;
    }

    private boolean networkStopped() {
        return isStopped() || !MarketNetwork.allowed();
    }

    @NonNull @Override public Result doWork() {
        synchronized (CHECK_LOCK) {
            if (!MarketNetwork.allowed()) return MarketNetwork.pausedWork();
            return check();
        }
    }

    private Result check() {
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        try {
            String key = readKey(context);
            String provider = key.isEmpty() ? UsDoltCloses.SOURCE : MASSIVE;
            var file = new AtomicFile(new File(context.getNoBackupFilesDir(), "us-daily-closes.json"));
            LocalDate previous = cachedDate(file, state, provider);
            LocalDate target = UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(Instant.now()));
            for (int offset = 0; offset < 7; offset++) {
                if (networkStopped()) return Result.retry();
                LocalDate day = target.minusDays(offset);
                if (previous != null && !day.isAfter(previous)) {
                    boolean assess = needsValuation(state, previous, provider);
                    boolean count = needsCoverage(state, previous, provider);
                    if (assess || count) {
                        var snapshot = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
                        var closes = snapshot.getJSONArray("closes");
                        if (count) updateCoverage(state, closes, previous, provider);
                        if (assess) assess(state, closes, previous, provider);
                    }
                    if (previous.equals(target)) backfillPrevious(context, previous, provider, key);
                    UsSecFinanceWorker.ensureScheduled(context);
                    updateHistory(state, previous);
                    report(state, day.equals(target) ? "終値を取得済み" : "新しい終値の公開待ち");
                    return Result.success();
                }
                if (!UsDailyCloses.tradingDay(day)) continue;

                var closes = fetchCloses(day, key);
                if (closes.length() == 0) continue;
                var snapshot = quoteSnapshot(day, provider, key, closes);
                if (networkStopped()) return Result.retry();
                synchronized (QUOTE_LOCK) {
                    if (UsPriceOnlyBudget.previousSession(day).equals(previous)) {
                        var old = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
                        var priorFile = new AtomicFile(new File(context.getNoBackupFilesDir(), PREVIOUS_QUOTE_FILE));
                        writeSnapshot(priorFile, old);
                    }
                    writeSnapshot(file, snapshot);
                }
                state.edit().putString(DATE, day.toString()).putInt(COUNT, closes.length())
                        .putString(PROVIDER, provider)
                        .putString(STATUS, "終値の自動取得に成功").apply();
                if (day.equals(target)) backfillPrevious(context, day, provider, key);
                UsSecFinanceWorker.ensureScheduled(context);
                updateCoverage(state, closes, day, provider);
                assess(state, closes, day, provider);
                updateHistory(state, day);
                return Result.success();
            }
            report(state, "直近7日間の終値を取得できず");
            return Result.success();
        } catch (HttpStatus e) {
            report(state, "終値を取得できず（HTTP " + e.code + "）");
            return e.code == 429 || e.code >= 500 ? Result.retry() : Result.success();
        } catch (IOException e) {
            if (networkStopped()) return MarketNetwork.pausedWork();
            report(state, "終値を取得できず（通信または保存エラー）");
            return Result.retry();
        } catch (JSONException e) {
            report(state, "終値を取得できず（配信形式を要確認）");
            return Result.success();
        }
    }

    private JSONArray fetchCloses(LocalDate day, String key) throws IOException, JSONException {
        if (!key.isEmpty()) {
            return UsDailyCloses.parse(fetch(ENDPOINT + day + "?adjusted=false&include_otc=false", key), day);
        }
        return UsDoltCloses.fetch(day, address -> {
            if (networkStopped()) throw new IOException("Worker stopped");
            return fetch(address, "");
        });
    }

    private static JSONObject quoteSnapshot(LocalDate day, String provider, String key, JSONArray closes)
            throws JSONException {
        return new JSONObject().put("source", provider)
                .put("adjusted", key.isEmpty() ? JSONObject.NULL : Boolean.FALSE)
                .put("trading_date_et", day.toString()).put("fetched_at_utc", Instant.now().toString())
                .put("closes", closes);
    }

    private void backfillPrevious(Context context, LocalDate day, String provider, String key) {
        if (networkStopped()) return;
        var priorDay = UsPriceOnlyBudget.previousSession(day);
        var priorFile = new AtomicFile(new File(context.getNoBackupFilesDir(), PREVIOUS_QUOTE_FILE));
        try {
            var saved = new JSONObject(new String(readQuote(priorFile), StandardCharsets.UTF_8));
            if (matchesPriorSnapshot(saved, priorDay, provider)) return;
        } catch (IOException | JSONException unavailable) {
            // A missing prior close can be filled independently of the current close.
        }
        try {
            var closes = fetchCloses(priorDay, key);
            if (closes.length() == 0 || networkStopped()) return;
            var snapshot = quoteSnapshot(priorDay, provider, key, closes);
            synchronized (QUOTE_LOCK) {
                writeSnapshot(priorFile, snapshot);
            }
        } catch (IOException | JSONException unavailable) {
            // Keep the current session available for financial screening and retry the prior close next run.
        }
    }

    static boolean matchesPriorSnapshot(JSONObject snapshot, LocalDate expected, String provider) {
        var closes = snapshot.optJSONArray("closes");
        return expected.toString().equals(snapshot.optString("trading_date_et"))
                && provider.equals(snapshot.optString("source")) && closes != null && closes.length() > 0;
    }

    static void applyFinancialScreen(Context context, SharedPreferences state, JSONObject ledger,
                                     LocalDate day, String provider, String closeHash,
                                     java.util.function.BooleanSupplier stopped) {
        if (stopped.getAsBoolean()) return;
        try {
            if (!day.toString().equals(ledger.optString("trading_date_et"))
                    || !provider.equals(ledger.optString("close_provider"))
                    || !closeHash.equals(ledger.optString("close_sha256"))) return;
            var coverage = ledger.getJSONObject("coverage");
            int financials = coverage.getJSONObject("NYSE").getInt("with_close_and_reference_financials")
                    + coverage.getJSONObject("Nasdaq").getInt("with_close_and_reference_financials");
            String status = day + " · SEC財務・株数の自動照合 " + financials + "銘柄";
            if (!ledger.has("reference_screen")) {
                state.edit().putString(PRIVATE_STATUS, status + " · 為替・分割資料待ち").apply();
                return;
            }
            var screen = UsReferenceAlerts.read(ledger);
            if (!provider.equals(screen.provider()) || !closeHash.equals(screen.hash())) {
                throw new JSONException("Reference screen does not match the daily close");
            }
            var previous = readPrivateBaseline(state);
            if (previous != null && day.isBefore(previous.day())) return;
            status += " · 参考判定 " + screen.rows().size() + "銘柄";
            long count = 0;
            for (var observation : screen.rows().values()) if (observation.candidate()) count++;
            status += " · 条件該当 " + count + "銘柄";
            String pending = state.getString(PRIVATE_PENDING, "");
            if (previous == null || day.isAfter(previous.day()) || !provider.equals(previous.provider())) {
                var entrants = UsReferenceAlerts.entrants(previous, screen);
                pending = entrants.isEmpty() ? "" : "米国株の参考条件入り " + entrants.size() + "銘柄"
                        + "\n" + day + "の終値（参考）\n"
                        + String.join("\n", entrants);
            }
            var baseline = new JSONObject().put("trading_date_et", day.toString())
                    .put("reference_screen", ledger.getJSONObject("reference_screen"));
            if (previous != null && day.equals(previous.day()) && !closeHash.equals(previous.hash())) pending = "";
            if (!ScanWorker.notificationsRequested(context) || !pending.contains("\n")) pending = "";
            if (stopped.getAsBoolean() || !state.edit().putString(PRIVATE_BASELINE, baseline.toString())
                    .putString(PRIVATE_PENDING, pending).putString(PRIVATE_STATUS, status).commit()) return;
            if (!pending.isEmpty() && !stopped.getAsBoolean()) {
                int separator = pending.indexOf('\n');
                if (ScanWorker.postNotification(context, US_NOTIFICATION_ID,
                        pending.substring(0, separator), pending.substring(separator + 1))) {
                    state.edit().remove(PRIVATE_PENDING).commit();
                } else if (!ScanWorker.notificationsRequested(context)) {
                    state.edit().remove(PRIVATE_PENDING).apply();
                } else {
                    state.edit().putString(PRIVATE_STATUS, status + "\n無音通知は端末の通知許可待ち").apply();
                }
            }
        } catch (JSONException | DateTimeParseException e) {
            state.edit().putString(PRIVATE_STATUS, "財務自動更新の結果を読み取れず · 次回確認").apply();
        }
    }

    private static UsReferenceAlerts.Screen readPrivateBaseline(SharedPreferences state) {
        String saved = state.getString(PRIVATE_BASELINE, "");
        if (saved.isEmpty()) return null;
        try {
            return UsReferenceAlerts.read(new JSONObject(saved));
        } catch (JSONException invalid) {
            return null;
        }
    }

    private static boolean needsCoverage(SharedPreferences state, LocalDate day, String provider) {
        return !day.toString().equals(state.getString(MARKET_DATE, ""))
                || !provider.equals(state.getString(MARKET_SOURCE, ""));
    }

    private void updateCoverage(SharedPreferences state, JSONArray closes, LocalDate day, String provider) {
        if (networkStopped()) return;
        try {
            var nasdaq = UsMarketCoverage.directory(fetchText(UsMarketCoverage.DIRECTORY + "nasdaqlisted.txt", ""), true);
            var nyse = UsMarketCoverage.directory(fetchText(UsMarketCoverage.DIRECTORY + "otherlisted.txt", ""), false);
            JSONObject ledger = null;
            try (var input = getApplicationContext().getAssets().open(UsMarketCoverage.ASSET)) {
                ledger = new JSONObject(readText(input));
            } catch (FileNotFoundException absent) {
                // Close monitoring uses the live exchange directories even without a private SEC ledger.
            }
            String summary = UsMarketCoverage.summarize(nyse, nasdaq, closes, day, ledger);
            if (!networkStopped()) state.edit().putString(MARKET_DATE, day.toString())
                    .putString(MARKET_SOURCE, provider).putString(MARKET_TEXT, summary).apply();
        } catch (IOException | JSONException unable) {
            // Retry the coverage comparison on the next periodic run, keeping the saved closes.
        }
    }

    private static boolean needsValuation(SharedPreferences state, LocalDate day, String provider) {
        return !day.toString().equals(state.getString(VALUATION_DATE, ""))
                || !provider.equals(state.getString(VALUATION_SOURCE, ""))
                || state.getBoolean(VALUATION_RETRY, false);
    }

    private void assess(SharedPreferences state, JSONArray closes, LocalDate day, String provider) {
        if (networkStopped()) return;
        UsDailyValuation.Report result;
        try {
            result = UsDailyValuation.assess(closes, day,
                    MASSIVE.equals(provider) ? "Massive参考判定" : "DoltHub参考判定", new UsDailyValuation.Fetch() {
                @Override public JSONObject facts(String address) throws IOException, JSONException {
                    if (networkStopped()) throw new IOException("Worker stopped");
                    return fetch(address, "");
                }

                @Override public JSONArray rates(String address) throws IOException, JSONException {
                    return new JSONArray(UsScanWorker.get(address, null));
                }

                @Override public java.util.Map<String, LocalDate> splits(LocalDate since, LocalDate session)
                        throws IOException, JSONException {
                    return UsDoltCloses.pilotSplits(since, session, address -> fetch(address, ""));
                }
            });
        } catch (IOException | JSONException e) {
            result = new UsDailyValuation.Report("参考判定は次の更新で再試行（為替または分割情報を取得できず）", true);
        }
        if (networkStopped()) return;
        state.edit().putString(VALUATION_DATE, day.toString()).putString(VALUATION_SOURCE, provider)
                .putString(VALUATION_TEXT, result.text()).putBoolean(VALUATION_RETRY, result.retry()).apply();
    }

    private void updateHistory(SharedPreferences state, LocalDate session) {
        YearMonth month = YearMonth.from(session);
        if (networkStopped() || month.toString().equals(state.getString(HISTORY_MONTH, ""))) return;
        YearMonth first = month.minusMonths(UsMonthlyHistory.MONTHS);
        if (!month.toString().equals(state.getString(HISTORY_CURSOR, ""))) {
            var reset = state.edit().putString(HISTORY_CURSOR, month.toString());
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                reset.remove(HISTORY_CURSOR + offset);
            }
            reset.apply();
        }
        var batches = new ArrayList<JSONArray>();
        try {
            // Retain completed annual queries for retries within the same refresh month.
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                if (networkStopped()) return;
                String key = HISTORY_CURSOR + offset;
                String cached = state.getString(key, "");
                JSONArray batch = cached.isEmpty()
                        ? UsDoltCloses.monthlyRows(first.plusMonths(offset), address -> fetch(address, ""))
                        : new JSONArray(cached);
                batches.add(batch);
                if (cached.isEmpty()) state.edit().putString(key, batch.toString()).apply();
            }
            var splits = UsDoltCloses.pilotSplits(first.atDay(1), session, address -> fetch(address, ""));
            String text = UsMonthlyHistory.summarize(batches, first, splits, UsDailyValuation.pilotSymbols());
            var update = state.edit().putString(HISTORY_MONTH, month.toString()).putString(HISTORY_TEXT, text);
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                update.remove(HISTORY_CURSOR + offset);
            }
            if (!networkStopped()) update.apply();
        } catch (IOException e) {
            // Resume any completed annual queries on the next periodic update.
        } catch (JSONException e) {
            // Restart after an invalid response or cache, keeping the daily close available.
            state.edit().remove(HISTORY_CURSOR).apply();
        }
    }

    private static LocalDate cachedDate(AtomicFile file, SharedPreferences state, String provider) {
        try {
            var snapshot = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
            var date = LocalDate.parse(snapshot.getString("trading_date_et"));
            String storedProvider = snapshot.getString("source");
            state.edit().putString(DATE, date.toString()).putString(PROVIDER, storedProvider)
                    .putInt(COUNT, snapshot.getJSONArray("closes").length()).apply();
            return provider.equals(storedProvider) ? date : null;
        } catch (IOException | JSONException | DateTimeParseException e) {
            state.edit().remove(DATE).remove(COUNT).remove(PROVIDER).apply();
            return null;
        }
    }

    static byte[] readQuote(AtomicFile file) throws IOException {
        synchronized (QUOTE_LOCK) {
            return file.readFully();
        }
    }

    static void writeSnapshot(AtomicFile file, JSONObject snapshot) throws IOException {
        var stream = file.startWrite();
        try {
            stream.write(snapshot.toString().getBytes(StandardCharsets.UTF_8));
            file.finishWrite(stream);
        } catch (IOException e) {
            file.failWrite(stream);
            throw e;
        }
    }

    static JSONObject fetch(String address, String key) throws IOException, JSONException {
        return new JSONObject(fetchText(address, key));
    }

    static String fetchText(String address, String key) throws IOException, JSONException {
        var url = new URL(address);
        var connection = MarketNetwork.open(url);
        try {
            connection.setConnectTimeout(15_000);
            connection.setReadTimeout(30_000);
            connection.setInstanceFollowRedirects(false);
            if (!key.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + key);
            if (java.util.Set.of("data.sec.gov", "www.sec.gov").contains(url.getHost())) {
                connection.setRequestProperty("User-Agent",
                        "VALUE HUNTER AI https://github.com/osawamas/value-hunter-ai");
                connection.setRequestProperty("Accept", "application/json");
            }
            if ("api.nasdaq.com".equals(url.getHost())) {
                connection.setConnectTimeout(7_000);
                connection.setReadTimeout(7_000);
                connection.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36");
                connection.setRequestProperty("Accept", "application/json, text/plain, */*");
            }
            int code = MarketNetwork.response(connection);
            if (code != 200) throw new HttpStatus(code);
            try (var input = MarketNetwork.input(connection)) {
                return readText(input);
            }
        } finally {
            MarketNetwork.close(connection);
        }
    }

    private static String readText(java.io.InputStream input) throws IOException, JSONException {
        var output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (output.size() + count > UsDailyCloses.MAX_BYTES) {
                throw new JSONException("Daily summary exceeds size limit");
            }
            output.write(buffer, 0, count);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String readKey(Context context) throws IOException {
        try (var input = context.getAssets().open(KEY_FILE)) {
            byte[] bytes = new byte[257];
            int length = 0;
            int count;
            while (length < bytes.length && (count = input.read(bytes, length, bytes.length - length)) > 0) {
                length += count;
            }
            if (length == bytes.length) return "";
            String key = new String(bytes, 0, length, StandardCharsets.UTF_8).trim();
            return key.matches("[A-Za-z0-9_-]+") ? key : "";
        } catch (FileNotFoundException e) {
            return "";
        }
    }

    private static void report(SharedPreferences state, String status) {
        state.edit().putString(STATUS, status).apply();
    }

    static final class HttpStatus extends IOException {
        final int code;

        HttpStatus(int code) {
            this.code = code;
        }
    }
}
