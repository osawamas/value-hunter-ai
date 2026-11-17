package jp.valuehunter.privatewatch;

import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.text.Html;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.HashSet;
import java.util.List;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;

public final class JpxWatchWorker extends Worker {
    static final String WORK = "jpx-daily-watch";
    static final String MANUAL = "jpx-daily-check-now";
    private static final String TOKEN = "jpx_watch_token";
    private static final String BASELINE = "jpx_watch_baseline";
    private static final String LATEST = "jpx_watch_latest";
    private static final String PROCESSED = "jpx_watch_processed";
    private static final String ALERTED = "jpx_watch_alerted";
    private static final String CHECKED_AT = "jpx_watch_checked_at";
    private static final String OUTCOME = "jpx_watch_outcome";
    private static final DateTimeFormatter JAPAN_TIME = DateTimeFormatter.ofPattern("M月d日 HH:mm", Locale.JAPAN)
            .withZone(ZoneId.of("Asia/Tokyo"));
    static final String STATUS = "jpx_watch_status";
    private static final int NOTIFICATION_ID = 5;
    private static final Object STATE_LOCK = new Object();
    private static final Object CHECK_LOCK = new Object();

    @FunctionalInterface
    interface ComparisonLoader {
        JpxDailyCheck.Comparison load(Context context, String processedKey, String rightsRevision) throws IOException;
    }

    @FunctionalInterface
    interface AlertSender {
        boolean post(Context context, int id, String title, String detail);
    }

    private final ComparisonLoader comparisons;
    private final Function<Context, JpxShareRights.Selection> rights;
    private final AlertSender alerts;

    public JpxWatchWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, (app, key, revision) -> JpxDailyCheck.checkWatch(app.getCacheDir(), key, revision),
                JpxShareRights::refresh, ScanWorker::postNotification);
    }

    JpxWatchWorker(Context context, WorkerParameters parameters, ComparisonLoader comparisons,
                   Function<Context, JpxShareRights.Selection> rights, AlertSender alerts) {
        super(context, parameters);
        this.comparisons = comparisons;
        this.rights = rights;
        this.alerts = alerts;
    }

    static boolean enabled(Context context) {
        return !ScanWorker.prefs(context).getString(TOKEN, "").isEmpty();
    }

    static void setEnabled(Context context, boolean enabled) {
        synchronized (STATE_LOCK) {
            var state = ScanWorker.prefs(context);
            var work = WorkManager.getInstance(context);
            if (enabled && Build.VERSION.SDK_INT >= 35) {
                if (!enabled(context)) {
                    state.edit().putString(TOKEN, UUID.randomUUID().toString())
                            .putString(STATUS, "東証日報の確認を予約した").apply();
                }
                var request = new PeriodicWorkRequest.Builder(JpxWatchWorker.class, 6, TimeUnit.HOURS)
                        .setConstraints(connected()).build();
                work.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
            } else {
                state.edit().remove(TOKEN).remove(BASELINE).remove(LATEST).remove(ALERTED).remove(PROCESSED)
                        .remove(STATUS).remove(CHECKED_AT).remove(OUTCOME).apply();
                work.cancelUniqueWork(WORK);
                work.cancelUniqueWork(MANUAL);
                context.getSystemService(NotificationManager.class).cancel(NOTIFICATION_ID);
            }
        }
    }

    static boolean checkNow(Context context) {
        synchronized (STATE_LOCK) {
            if (Build.VERSION.SDK_INT < 35 || !enabled(context)) return false;
            var request = new OneTimeWorkRequest.Builder(JpxWatchWorker.class)
                    .setConstraints(connected()).build();
            WorkManager.getInstance(context).enqueueUniqueWork(MANUAL, ExistingWorkPolicy.KEEP, request);
            return true;
        }
    }

    private static Constraints connected() {
        return new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
    }

    @NonNull @Override public Result doWork() {
        synchronized (CHECK_LOCK) {
            return check();
        }
    }

    private Result check() {
        if (Build.VERSION.SDK_INT < 35 || isStopped()) return Result.success();
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        String token = state.getString(TOKEN, "");
        if (token.isEmpty()) return Result.success();

        try {
            var evidence = rights.apply(context);
            if (isStopped()) return Result.success();
            String processedKey = ScanWorker.alertsEnabled(context) ? state.getString(PROCESSED, "") : "";
            var comparison = comparisons.load(context, processedKey, evidence.revision());
            if (isStopped()) return Result.success();
            synchronized (STATE_LOCK) {
                if (isStopped() || !token.equals(state.getString(TOKEN, ""))) return Result.success();
                if (comparison == null) {
                    recordCheck(state.edit(), "日報と照合資料の版に変更なし · PDFの再取得を省略").apply();
                    return Result.success();
                }
                var screen = comparison.screen(evidence.rights());
                LocalDate date = comparison.latest().date();
                var baseline = dateOrNull(state.getString(BASELINE, ""));
                var last = dateOrNull(state.getString(LATEST, ""));
                if (last != null && date.isBefore(last)) {
                    recordCheck(state.edit(), "取得した日報が保存済みより古いため、前回の判定を保持").apply();
                    return Result.success();
                }
                if (comparison.previous() == null) {
                    var partial = new StringBuilder("比較用の日報を取得できなかった");
                    partial.append("\n").append(date).append("の当日判定");
                    appendCandidates(partial, screen);
                    return retryReport(state, partial.toString());
                }
                var alerted = date.equals(last)
                        ? new HashSet<>(state.getStringSet(ALERTED, Set.of())) : new HashSet<String>();
                boolean notifyEnabled = ScanWorker.alertsEnabled(context);
                var added = notifyEnabled ? pending(baseline, last, date, screen.entered(), alerted)
                        : List.<JpxDailyCheck.Candidate>of();
                var summary = new StringBuilder(date + " 東証日報を確認 · 比較保留 " + screen.held() + "銘柄");
                summary.append("\n比較日 ").append(comparison.previous().date());
                appendCandidates(summary, screen);
                appendHolds(summary, screen);
                if (!notifyEnabled) summary.append("\n通知設定を確認");
                LocalDate savedBaseline = baseline == null || last == null ? date : baseline;
                var update = recordCheck(state.edit(), "日報を取得して再判定")
                        .putString(BASELINE, savedBaseline.toString())
                        .putString(LATEST, date.toString()).putStringSet(ALERTED, alerted)
                        .putString(STATUS, summary.toString());
                String processed = notifyEnabled ? comparison.processedKey(evidence.revision()) : "";
                // Leave the inputs eligible for another check until the notification is submitted.
                update.putString(PROCESSED, added.isEmpty() ? processed : "");
                if (!update.commit()) return Result.retry();
                if (!added.isEmpty()) {
                    var detail = new StringBuilder(date + "の終値（参考）");
                    for (var entry : added) detail.append("\n").append(entry.summary());
                    if (!alerts.post(context, NOTIFICATION_ID, "東証日報で参考条件入り " + added.size() + "銘柄",
                            detail.toString())) {
                        state.edit().putString(STATUS, summary + "\n無音通知を送信できなかった · 通知設定を確認").apply();
                        // Keep PROCESSED empty and retry promptly before the next six-hour scan.
                        // The retry limit in retryReport prevents an endless notification loop.
                        return retryReport(state, "無音通知を送信できなかった");
                    }
                    for (var entry : added) alerted.add(entry.code());
                    if (!state.edit().putStringSet(ALERTED, alerted).putString(PROCESSED, processed).commit()) {
                        return Result.retry();
                    }
                }
            }
            return Result.success();
        } catch (IOException error) {
            synchronized (STATE_LOCK) {
                if (isStopped() || !token.equals(state.getString(TOKEN, ""))) return Result.success();
                return retryReport(state, "日報を取得できなかった");
            }
        }
    }

    private Result retryReport(SharedPreferences state, String message) {
        boolean retry = getRunAttemptCount() < 2;
        recordCheck(state.edit(), retry ? message + " · 再試行を予約した" : message).apply();
        return retry ? Result.retry() : Result.success();
    }

    private static SharedPreferences.Editor recordCheck(SharedPreferences.Editor edit, String outcome) {
        return edit.putLong(CHECKED_AT, System.currentTimeMillis()).putString(OUTCOME, outcome);
    }

    static String displayStatus(SharedPreferences state) {
        var check = new StringBuilder();
        long last = state.getLong(CHECKED_AT, 0L);
        if (last > 0) {
            check.append("最終確認 ").append(JAPAN_TIME.format(Instant.ofEpochMilli(last))).append("（日本時間）");
            check.append("\n").append(state.getString(OUTCOME, ""));
        }
        String summary = state.getString(STATUS, "");
        if (!summary.isEmpty()) {
            if (check.length() > 0) check.append("\n");
            check.append(summary);
        }
        return check.toString();
    }

    private static void appendCandidates(StringBuilder message, JpxDailyCheck.Screening screen) {
        long priority = screen.candidates().stream()
                .filter(candidate -> candidate.level() == ValueCandidateScreen.Level.PRIORITY).count();
        message.append("\n優先候補 ").append(priority).append("銘柄 · 参考候補 ")
                .append(screen.candidates().size() - priority).append("銘柄");
        for (var candidate : screen.candidates()) message.append("\n").append(candidate.summary());
    }

    private static void appendHolds(StringBuilder message, JpxDailyCheck.Screening screen) {
        var byReason = new LinkedHashMap<String, List<String>>();
        for (var hold : screen.holds()) {
            String reason = Html.fromHtml(hold.reason(), Html.FROM_HTML_MODE_LEGACY).toString();
            byReason.computeIfAbsent(reason, ignored -> new ArrayList<>()).add(hold.code());
        }
        byReason.forEach((reason, codes) ->
                message.append("\n").append(String.join("・", codes)).append(" · ").append(reason));
    }

    static List<JpxDailyCheck.Candidate> pending(LocalDate baseline, LocalDate last, LocalDate date,
                                             List<JpxDailyCheck.Candidate> entered, Set<String> alerted) {
        if (baseline == null || last == null || !date.isAfter(baseline) || date.isBefore(last)) return List.of();
        if (!date.equals(last)) return entered;
        return entered.stream().filter(entry -> !alerted.contains(entry.code())).toList();
    }

    private static LocalDate dateOrNull(String text) {
        try {
            return LocalDate.parse(text);
        } catch (DateTimeParseException error) {
            return null;
        }
    }
}
