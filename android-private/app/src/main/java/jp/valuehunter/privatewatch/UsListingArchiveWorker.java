package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONException;

import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Map;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public final class UsListingArchiveWorker extends Worker {
    private static final String WORK = "us-listing-archive";
    private static final String IMMEDIATE = "us-listing-archive-now";
    private static final String STATUS_DAY = "us_listing_archive_status_day";
    private static final String STATUS_PREVIOUS = "us_listing_archive_status_previous";
    private static final String STATUS_SAVED = "us_listing_archive_status_saved";
    private static final String STATUS_PREVIOUS_SAVED = "us_listing_archive_status_previous_saved";
    private static final String STATUS_ERROR = "us_listing_archive_status_error";
    private static final String RECHECK = "us_listing_archive_recheck_day";
    private static final LocalTime START = LocalTime.of(16, 5);
    private static final LocalTime END = LocalTime.of(20, 45);
    private static final Object CAPTURE_LOCK = new Object();

    public UsListingArchiveWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    static void schedule(Context context) {
        if (!MarketNetwork.requested()) return;
        var request = new PeriodicWorkRequest.Builder(UsListingArchiveWorker.class, 1, TimeUnit.HOURS)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.LINEAR, 15, TimeUnit.MINUTES)
                .build();
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_LISTING, "定期更新");
    }

    static void checkNow(Context context) {
        if (!MarketNetwork.allowed()) return;
        var request = new OneTimeWorkRequest.Builder(UsListingArchiveWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.LINEAR, 15, TimeUnit.MINUTES)
                .build();
        WorkManager.getInstance(context).enqueueUniqueWork(IMMEDIATE, ExistingWorkPolicy.KEEP, request);
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_LISTING, "追加の更新");
    }

    static boolean captureWindow(Instant now) {
        var local = now.atZone(UsDailyCloses.NEW_YORK);
        return UsDailyCloses.tradingDay(local.toLocalDate())
                && !local.toLocalTime().isBefore(START) && local.toLocalTime().isBefore(END);
    }

    static LocalDate latestArchiveDay(Instant now) {
        var local = now.atZone(UsDailyCloses.NEW_YORK);
        var date = local.toLocalTime().isBefore(START) ? local.toLocalDate().minusDays(1) : local.toLocalDate();
        return UsDailyCloses.onOrBeforeTradingDay(date);
    }

    @NonNull @Override public Result doWork() {
        var area = DiagnosticLog.Area.US_LISTING;
        return DiagnosticLog.work(getApplicationContext(), area, getRunAttemptCount(), this::runUpdate);
    }

    private Result runUpdate() {
        synchronized (CAPTURE_LOCK) {
            long generation = MarketNetwork.generation();
            if (stopped(generation)) return MarketNetwork.pausedWork(generation);
            var app = getApplicationContext();
            var prefs = ScanWorker.prefs(app);
            var directory = app.getNoBackupFilesDir();
            var now = Instant.now();
            var day = latestArchiveDay(now);
            try {
                if (captureWindow(now) && !UsListingHistory.hasIdentity(directory, day)) {
                    var nasdaq = listings("nasdaqlisted.txt", true);
                    if (stopped(generation)) return MarketNetwork.pausedWork(generation);
                    var nyse = listings("otherlisted.txt", false);
                    if (stopped(generation)) return MarketNetwork.pausedWork(generation);
                    var fetched = Instant.now();
                    if (captureWindow(fetched) && day.equals(latestArchiveDay(fetched))) {
                        if (!UsListingHistory.capture(directory, day,
                                fetched.atZone(UsDailyCloses.NEW_YORK).toLocalTime(), nyse, nasdaq)) {
                            throw new IOException("Same-session listing directories not available");
                        }
                    }
                }
                saveStatus(prefs, directory, day, false);
                DiagnosticLog.record(app, DiagnosticLog.Area.US_LISTING,
                        UsListingHistory.hasIdentity(directory, day) ? "対象取引日の上場一覧を保存済み"
                                : captureWindow(now) ? "対象取引日の上場一覧を待機中" : "上場一覧の保存時間外");
                if (!stopped(generation)) recheck(app, prefs, directory, now);
                return Result.success();
            } catch (IOException | JSONException | ExecutionException | TimeoutException unavailable) {
                if (stopped(generation)) return MarketNetwork.pausedWork(generation);
                boolean retry = captureWindow(Instant.now());
                saveStatus(prefs, directory, day, retry);
                DiagnosticLog.record(app, DiagnosticLog.Area.US_LISTING,
                        "上場一覧を取得または保存できず: " + unavailable.getClass().getSimpleName());
                return retry ? Result.retry() : Result.success();
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return Result.retry();
            }
        }
    }

    private boolean stopped(long generation) {
        return isStopped() || MarketNetwork.interrupted(generation);
    }

    private static UsMarketCoverage.Directory listings(String path, boolean nasdaq) throws IOException, JSONException {
        return UsMarketCoverage.directory(UsDailyWorker.fetchText(UsMarketCoverage.DIRECTORY + path, ""), nasdaq);
    }

    private static void recheck(Context app, SharedPreferences prefs, File directory, Instant now)
            throws JSONException, ExecutionException, InterruptedException, TimeoutException {
        var day = UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(now));
        if (!day.equals(MarketCoverage.US.day(prefs))) return;
        var groups = MarketCoverage.US.groups(prefs);
        var verified = UsListingHistory.verifiedSupplementSymbols(directory, day);
        var single = UsListingHistory.sessionExchanges(directory, day).keySet();
        if (groups.values().stream().flatMap(List::stream).anyMatch(single::contains)) {
            UsDailyWorker.recheckSingleSessionBudget(app, day);
        }
        if (day.toString().equals(prefs.getString(RECHECK, ""))) return;
        if (!hasVerifiedPending(groups, verified)) return;
        UsDailyWorker.recheckAfterArchive(app, day).getResult().get(10, TimeUnit.SECONDS);
        prefs.edit().putString(RECHECK, day.toString()).apply();
    }

    static boolean hasVerifiedPending(Map<MarketCoverage.Reason, List<String>> groups, Set<String> verified) {
        return groups.getOrDefault(MarketCoverage.Reason.CLOSE, List.of()).stream().anyMatch(verified::contains)
                || groups.getOrDefault(MarketCoverage.Reason.DATED_LISTING, List.of()).stream().anyMatch(verified::contains);
    }

    private static void saveStatus(SharedPreferences prefs, File directory, LocalDate day, boolean retry) {
        var previous = UsPriceOnlyBudget.previousSession(day);
        boolean saved = UsListingHistory.hasIdentity(directory, day);
        prefs.edit().putString(STATUS_DAY, day.toString()).putString(STATUS_PREVIOUS, previous.toString())
                .putBoolean(STATUS_SAVED, saved)
                .putBoolean(STATUS_PREVIOUS_SAVED, UsListingHistory.hasIdentity(directory, previous))
                .putBoolean(STATUS_ERROR, retry && !saved).apply();
    }

    static String displayStatus(SharedPreferences prefs, Instant now) {
        var day = latestArchiveDay(now);
        var previous = UsPriceOnlyBudget.previousSession(day);
        String recent = prefs.getString(STATUS_DAY, "");
        boolean same = day.toString().equals(recent);
        boolean saved = same && prefs.getBoolean(STATUS_SAVED, false);
        boolean previousSaved = previous.toString().equals(recent) && prefs.getBoolean(STATUS_SAVED, false)
                || previous.toString().equals(prefs.getString(STATUS_PREVIOUS, ""))
                && prefs.getBoolean(STATUS_PREVIOUS_SAVED, false);
        String status = saved ? "保存済み"
                : same && prefs.getBoolean(STATUS_ERROR, false) && captureWindow(now) ? "取得失敗・再試行待ち"
                : captureWindow(now) ? "取得待ち" : "未取得";
        return "上場一覧（米東部） · " + day + " " + status
                + " · 比較日 " + previous + " " + (previousSaved ? "保存済み" : "未取得");
    }
}
