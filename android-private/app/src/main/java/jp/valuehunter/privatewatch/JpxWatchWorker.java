package jp.valuehunter.privatewatch;

import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;

public final class JpxWatchWorker extends Worker {
    static final String WORK = "jpx-daily-watch";
    private static final String TOKEN = "jpx_watch_token";
    private static final String BASELINE = "jpx_watch_baseline";
    private static final String LATEST = "jpx_watch_latest";
    private static final String ALERTED = "jpx_watch_alerted";
    static final String STATUS = "jpx_watch_status";
    private static final int NOTIFICATION_ID = 5;
    private static final Object STATE_LOCK = new Object();

    @FunctionalInterface
    interface ComparisonLoader {
        JpxDailyCheck.Comparison load(Context context) throws IOException;
    }

    private final ComparisonLoader comparisons;
    private final Function<Context, JpxShareRights> rights;

    public JpxWatchWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, app -> JpxDailyCheck.check(app.getCacheDir()),
                app -> JpxShareRights.refresh(app).rights());
    }

    JpxWatchWorker(Context context, WorkerParameters parameters, ComparisonLoader comparisons,
                   Function<Context, JpxShareRights> rights) {
        super(context, parameters);
        this.comparisons = comparisons;
        this.rights = rights;
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
                var constraints = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
                var request = new PeriodicWorkRequest.Builder(JpxWatchWorker.class, 6, TimeUnit.HOURS)
                        .setConstraints(constraints).build();
                work.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
            } else {
                state.edit().remove(TOKEN).remove(BASELINE).remove(LATEST).remove(ALERTED).remove(STATUS).apply();
                work.cancelUniqueWork(WORK);
                context.getSystemService(NotificationManager.class).cancel(NOTIFICATION_ID);
            }
        }
    }

    @NonNull @Override public Result doWork() {
        if (Build.VERSION.SDK_INT < 35 || isStopped()) return Result.success();
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        String token = state.getString(TOKEN, "");
        if (token.isEmpty()) return Result.success();

        try {
            var comparison = comparisons.load(context);
            if (isStopped()) return Result.success();
            var screen = comparison.screen(rights.apply(context));
            LocalDate date = comparison.latest().date();
            synchronized (STATE_LOCK) {
                if (isStopped() || !token.equals(state.getString(TOKEN, ""))) return Result.success();
                var baseline = dateOrNull(state.getString(BASELINE, ""));
                var last = dateOrNull(state.getString(LATEST, ""));
                if (last != null && date.isBefore(last)) return Result.success();
                var alerted = date.equals(last)
                        ? new HashSet<>(state.getStringSet(ALERTED, Set.of())) : new HashSet<String>();
                boolean notifyEnabled = ScanWorker.alertsEnabled(context);
                var added = notifyEnabled ? pending(baseline, last, date, screen.entered(), alerted)
                        : List.<JpxDailyCheck.Entrant>of();
                for (var entry : added) alerted.add(entry.code());
                String summary = date + " 東証日報を確認 · 保留 " + screen.held() + "銘柄";
                if (!notifyEnabled) summary += " · 通知設定を確認";
                LocalDate savedBaseline = baseline == null || last == null ? date : baseline;
                var update = state.edit().putString(BASELINE, savedBaseline.toString())
                        .putString(LATEST, date.toString()).putStringSet(ALERTED, alerted).putString(STATUS, summary);
                if (!update.commit()) return Result.retry();
                if (!added.isEmpty()) {
                    var detail = new StringBuilder(date + "の終値（参考）");
                    for (var entry : added) detail.append("\n").append(entry.code())
                            .append(" · ").append(entry.quantity()).append("株枠");
                    ScanWorker.postNotification(context, NOTIFICATION_ID, "東証日報で参考条件入り " + added.size() + "銘柄",
                            detail.toString());
                }
            }
            return Result.success();
        } catch (IOException error) {
            synchronized (STATE_LOCK) {
                if (isStopped() || !token.equals(state.getString(TOKEN, ""))) return Result.success();
                state.edit().putString(STATUS, "東証日報の定期確認で取得できなかった").apply();
            }
            return getRunAttemptCount() < 2 ? Result.retry() : Result.success();
        }
    }

    static List<JpxDailyCheck.Entrant> pending(LocalDate baseline, LocalDate last, LocalDate date,
                                             List<JpxDailyCheck.Entrant> entered, Set<String> alerted) {
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
