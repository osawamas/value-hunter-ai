package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;
import android.os.SystemClock;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/** Downloads SEC filings on-device and resumes through WorkManager between batches. */
public final class UsSecFinanceWorker extends Worker {
    private static final String WORK = "us-sec-financials-on-device";
    private static final String STATE = "us-sec-financials.json";
    private static final String QUOTES = "us-daily-closes.json";
    private static final String SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json";
    private static final String FX = "https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY";
    private static final int BATCH = 40;
    private static final long BATCH_MILLIS = 45_000;
    private static final long BETWEEN_REQUESTS_MILLIS = 350;

    @FunctionalInterface
    interface Download {
        String get(String address) throws IOException, JSONException;
    }

    private final Download download;

    public UsSecFinanceWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, address -> UsDailyWorker.fetchText(address, ""));
    }

    UsSecFinanceWorker(Context context, WorkerParameters parameters, Download download) {
        super(context, parameters);
        this.download = download;
    }

    static void ensureScheduled(Context context) {
        enqueue(context, ExistingWorkPolicy.KEEP);
    }

    private static void enqueue(Context context, ExistingWorkPolicy policy) {
        var request = new OneTimeWorkRequest.Builder(UsSecFinanceWorker.class)
                .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.UNMETERED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build();
        WorkManager.getInstance(context).enqueueUniqueWork(WORK, policy, request);
    }

    @NonNull @Override public Result doWork() {
        var context = getApplicationContext();
        var preferences = ScanWorker.prefs(context);
        var directory = context.getNoBackupFilesDir();
        var closeFile = new AtomicFile(new File(directory, QUOTES));
        var checkpoint = new AtomicFile(new File(directory, STATE));
        try {
            byte[] bytes = UsDailyWorker.readQuote(closeFile);
            JSONObject quote = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            String hash = UsReferenceAlerts.sha256(bytes);
            var day = LocalDate.parse(quote.getString("trading_date_et"));
            var provider = quote.getString("source");
            var prices = UsDeviceFinancials.prices(quote.getJSONArray("closes"));
            var scan = resume(checkpoint, hash);
            if (scan == null) {
                var nasdaq = listings("nasdaqlisted.txt", true);
                var nyse = listings("otherlisted.txt", false);
                var sec = new JSONObject(download.get(UsDeviceFinancials.SEC_DIRECTORY));
                scan = new JSONObject().put("hash", hash).put("cursor", 0)
                        .put("results", new JSONArray())
                        .put("targets", UsDeviceFinancials.targets(nyse, nasdaq, sec, prices.keySet()));
                UsDailyWorker.writeSnapshot(checkpoint, scan);
            }
            var targets = scan.getJSONArray("targets");
            var results = scan.getJSONArray("results");
            int position = scan.getInt("cursor");
            if (position < 0 || position > targets.length() || results.length() > position) {
                checkpoint.delete();
                return Result.retry();
            }

            if (position < targets.length()) {
                long deadline = SystemClock.elapsedRealtime() + BATCH_MILLIS;
                try {
                    int end = Math.min(targets.length(), position + BATCH);
                    while (position < end && !isStopped() && SystemClock.elapsedRealtime() < deadline) {
                        var target = targets.getJSONObject(position);
                        var row = facts(target, day);
                        if (row != null) results.put(row);
                        scan.put("cursor", ++position);
                        if (position < end) Thread.sleep(BETWEEN_REQUESTS_MILLIS);
                    }
                } finally {
                    UsDailyWorker.writeSnapshot(checkpoint, scan);
                    updateProgress(position, targets.length(), results.length());
                }
                if (isStopped()) return Result.retry();
                if (position < targets.length()) {
                    enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
                    return Result.success();
                }
            }

            var ledger = scan.optJSONObject("ledger");
            if (ledger == null) {
                var rates = new JSONArray(download.get(
                        FX + "&from=" + day.minusDays(UsScreen.FX_LOOKBACK_DAYS) + "&to=" + day));
                var fx = UsScreen.readFx(rates, day);
                var splits = UsDoltCloses.allSplits(day.minusDays(150), day, url -> new JSONObject(download.get(url)));
                ledger = UsDeviceFinancials.screen(day, provider, hash, results, prices, fx, splits);
                scan.put("ledger", ledger);
                UsDailyWorker.writeSnapshot(checkpoint, scan);
            }
            synchronized (UsDailyWorker.QUOTE_LOCK) {
                if (!hash.equals(UsReferenceAlerts.sha256(closeFile.readFully()))) {
                    if (!isStopped()) enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
                    return Result.success();
                }
                UsDailyWorker.applyFinancialScreen(context, preferences, ledger, day, provider, hash, this::isStopped);
            }
            return Result.success();
        } catch (FileNotFoundException absent) {
            return Result.success();
        } catch (InterruptedException cancelled) {
            Thread.currentThread().interrupt();
            return Result.retry();
        } catch (IOException | JSONException | DateTimeParseException unavailable) {
            String progress = preferences.getString(UsDailyWorker.PRIVATE_STATUS, "");
            if (!progress.endsWith(" · 再試行待ち")) {
                preferences.edit().putString(UsDailyWorker.PRIVATE_STATUS,
                        (progress.isEmpty() ? "米国株の財務データ待ち" : progress) + " · 再試行待ち").apply();
            }
            return Result.retry();
        }
    }

    private UsMarketCoverage.Directory listings(String filename, boolean nasdaq)
            throws IOException, JSONException {
        return UsMarketCoverage.directory(download.get(UsMarketCoverage.DIRECTORY + filename), nasdaq);
    }

    private static JSONObject resume(AtomicFile file, String hash) throws IOException {
        try {
            var scan = new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
            if (hash.equals(scan.optString("hash")) && scan.optInt("cursor", -1) >= 0
                    && scan.optJSONArray("targets") != null && scan.optJSONArray("results") != null) return scan;
        } catch (FileNotFoundException | JSONException absent) {
            // A missing or damaged local checkpoint starts a fresh scan.
        }
        return null;
    }

    private JSONObject facts(JSONObject target, LocalDate day) throws IOException, JSONException {
        try {
            int cik = target.getInt("cik");
            var payload = new JSONObject(download.get(String.format(Locale.ROOT, SEC_FACTS, cik)));
            var figures = UsFinancialFacts.read(payload, cik, day);
            if (figures == null) return null;
            return new JSONObject().put("symbol", target.getString("symbol")).put("exchange", target.getString("exchange"))
                    .put("cik", cik).put("share_date", figures.shareDate().toString())
                    .put("shares", figures.shares().toPlainString()).put("profit", figures.profit().toPlainString())
                    .put("equity", figures.equity().toPlainString());
        } catch (UsDailyWorker.HttpStatus error) {
            if (error.code == 404) return null;
            throw error;
        } catch (JSONException invalidIssuer) {
            // Invalid issuer facts cannot become a candidate.
            return null;
        }
    }

    private void updateProgress(int position, int total, int verified) {
        ScanWorker.prefs(getApplicationContext()).edit().putString(UsDailyWorker.PRIVATE_STATUS,
                "SEC財務を取得中 " + position + " / " + total + "銘柄 · 財務・株数照合 " + verified + "銘柄").apply();
    }
}
