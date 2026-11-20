package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.provider.Settings;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;

import java.text.NumberFormat;
import java.util.HashSet;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

public final class ScanWorker extends Worker {
    private static final String PERIODIC = "japan-watch";
    private static final String MANUAL = "japan-check-now";
    static final String LEGACY_API_REQUEST = "explicit_legacy_api_request";
    static final String CHANNEL = "value-alerts";
    private static final int SCREEN_VERSION = 2;
    private static final Object SCAN_LOCK = new Object();

    public ScanWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences("private-stock-watch", Context.MODE_PRIVATE);
    }

    static void cancelLegacyApiWork(Context context) {
        var work = WorkManager.getInstance(context);
        for (String name : new String[] {PERIODIC, MANUAL, "us-watch", "us-check-now", "sg-watch", "sg-check-now"}) {
            work.cancelUniqueWork(name);
        }
        var manager = context.getSystemService(NotificationManager.class);
        manager.cancel(1);
        manager.cancel(3);
        manager.cancel(4);
    }

    private static Data legacyApiRequest() {
        return new Data.Builder().putBoolean(LEGACY_API_REQUEST, true).build();
    }

    static void schedule(Context context) {
        var connected = connected();
        var work = WorkManager.getInstance(context);
        work.enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP,
                new PeriodicWorkRequest.Builder(ScanWorker.class, 6, TimeUnit.HOURS)
                        .setInputData(legacyApiRequest()).setConstraints(connected).build());
    }

    static void scheduleUs(Context context) {
        WorkManager.getInstance(context).enqueueUniquePeriodicWork("us-watch", ExistingPeriodicWorkPolicy.KEEP,
                new PeriodicWorkRequest.Builder(UsScanWorker.class, 6, TimeUnit.HOURS)
                        .setInitialDelay(6, TimeUnit.HOURS).setInputData(legacyApiRequest()).setConstraints(connected()).build());
        WorkManager.getInstance(context).enqueueUniqueWork("us-check-now", ExistingWorkPolicy.KEEP,
                new OneTimeWorkRequest.Builder(UsScanWorker.class).setInputData(legacyApiRequest()).setConstraints(connected()).build());
    }

    static void checkSingapore(Context context) {
        WorkManager.getInstance(context).enqueueUniqueWork("sg-check-now", ExistingWorkPolicy.REPLACE,
                new OneTimeWorkRequest.Builder(SgCheckWorker.class).setInputData(legacyApiRequest()).setConstraints(connected())
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES).build());
    }

    static void scheduleSingaporeWatch(Context context) {
        WorkManager.getInstance(context).enqueueUniquePeriodicWork("sg-watch", ExistingPeriodicWorkPolicy.KEEP,
                new PeriodicWorkRequest.Builder(SgCheckWorker.class, 6, TimeUnit.HOURS)
                        .setInitialDelay(6, TimeUnit.HOURS).setInputData(legacyApiRequest()).setConstraints(connected())
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES).build());
    }

    static void stopSingaporeWatch(Context context) {
        WorkManager.getInstance(context).cancelUniqueWork("sg-watch");
    }

    private static Constraints connected() {
        return new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
    }

    static void checkNow(Context context) {
        var connected = connected();
        WorkManager.getInstance(context).enqueueUniqueWork(MANUAL, ExistingWorkPolicy.KEEP,
                new OneTimeWorkRequest.Builder(ScanWorker.class).setInputData(legacyApiRequest()).setConstraints(connected).build());
    }

    @NonNull @Override public Result doWork() {
        if (!getInputData().getBoolean(LEGACY_API_REQUEST, false)) return Result.success();
        synchronized (SCAN_LOCK) {
            return scan();
        }
    }

    private Result scan() {
        Context context = getApplicationContext();
        SharedPreferences state = prefs(context);
        String key = state.getString("key", "");
        if (key.isEmpty()) return Result.success();
        boolean delayed = state.getBoolean("delayed", true);
        // Rebuild the baseline when introducing a new screening tier.
        boolean currentScreen = state.getInt("screen_version", 1) == SCREEN_VERSION;
        String lastDate = currentScreen ? state.getString("latest_date", "") : "";
        status(state, "株価と指標を確認中…");
        try {
            var snapshot = new JQuants(key).scan(delayed, lastDate);
            if (isStopped() || !key.equals(state.getString("key", ""))
                    || delayed != state.getBoolean("delayed", true)) return Result.success();
            if (snapshot == null) {
                status(state, "この時点で取得できる新しい取引日はなかった");
                return Result.success();
            }
            if (!WatchTransitions.shouldStoreSnapshot(lastDate, snapshot.date())) {
                status(state, "取得した取引日が保存済みの基準日以前のため、監視履歴を維持した");
                return Result.success();
            }
            var candidates = snapshot.candidates();
            var previous = state.getStringSet("qualified", new HashSet<>());
            var added = WatchTransitions.newEntrants(lastDate, snapshot.date(), candidates, previous);
            var codes = new HashSet<String>();
            var lines = new JSONArray();
            for (var candidate : candidates) {
                codes.add(candidate.code());
                lines.put(format(candidate));
            }
            var editor = state.edit().putInt("screen_version", SCREEN_VERSION)
                    .putString("latest_date", snapshot.date().toString())
                    .putStringSet("qualified", codes).putString("rows", lines.toString())
                    .putString("status", "取得完了 · 条件に該当 " + codes.size() + "銘柄");
            // Commit the date and the qualifying set together before posting the notification.
            if (!editor.commit()) return Result.retry();
            if (!added.isEmpty()) {
                notifyUser(snapshot.date().toString(), added.size(), format(added.get(0)), delayed);
            }
            return Result.success();
        } catch (JQuants.HttpFailure error) {
            status(state, "J-Quantsから取得できなかった（HTTP " + error.status + "）。キー・プラン・接続を確認");
            return retryTransient(error.status == 429 || error.status >= 500);
        } catch (JSONException error) {
            status(state, "株価・銘柄・指標の応答を照合できなかった");
            return retryTransient(true);
        } catch (java.io.IOException error) {
            status(state, "接続できないか、取得できる終値がまだない");
            return retryTransient(true);
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            return Result.retry();
        }
    }

    private Result retryTransient(boolean transientFailure) {
        return transientFailure && getRunAttemptCount() < 2 ? Result.retry() : Result.failure();
    }

    private static void status(SharedPreferences state, String value) {
        state.edit().putString("status", value).apply();
    }

    private static String format(JapanScreen.Candidate row) {
        var currency = NumberFormat.getNumberInstance(Locale.JAPAN);
        currency.setMaximumFractionDigits(3);
        String lotNote = row.quantity() == 1 ? "（単元未満）" : "";
        return String.format(Locale.JAPAN, "%s %s\n%d株 %s円%s   PER %.2f倍   PBR %.2f倍",
                row.code(), row.name(), row.quantity(), currency.format(row.cost()), lotNote, row.per(), row.pbr());
    }

    private void notifyUser(String date, int count, String example, boolean delayed) {
        String detail = date + "の終値" + (delayed ? "（遅延データ）" : "") + "\n" + example;
        postNotification(getApplicationContext(), 1, "新しい割安候補 " + count + "銘柄", detail);
    }

    static void testNotification(Context context) {
        postNotification(context, 2, "VALUE HUNTER AI 無音通知テスト", "新しい候補が見つかると、この通知欄に表示される");
    }

    static boolean alertsEnabled(Context context) {
        var manager = context.getSystemService(NotificationManager.class);
        var channel = manager.getNotificationChannel(CHANNEL);
        return manager.areNotificationsEnabled()
                && (channel == null || channel.getImportance() != NotificationManager.IMPORTANCE_NONE);
    }

    static Intent alertSettings(Context context) {
        var manager = context.getSystemService(NotificationManager.class);
        if (!manager.areNotificationsEnabled()) {
            return new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    .putExtra(Settings.EXTRA_APP_PACKAGE, context.getPackageName());
        }
        createAlertChannel(manager);
        return new Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS)
                .putExtra(Settings.EXTRA_APP_PACKAGE, context.getPackageName())
                .putExtra(Settings.EXTRA_CHANNEL_ID, CHANNEL);
    }

    private static void createAlertChannel(NotificationManager manager) {
        var channel = new NotificationChannel(CHANNEL, "割安候補（無音）", NotificationManager.IMPORTANCE_LOW);
        channel.setSound(null, null);
        channel.enableVibration(false);
        manager.createNotificationChannel(channel);
    }

    static boolean postNotification(Context context, int id, String title, String detail) {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) return false;
        var manager = context.getSystemService(NotificationManager.class);
        createAlertChannel(manager);
        var tap = PendingIntent.getActivity(context, 0, new Intent(context, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        if (!alertsEnabled(context)) return false;
        String receipt = notificationReceipt(title, detail);
        var extras = new android.os.Bundle();
        extras.putString(NOTIFICATION_RECEIPT, receipt);
        try {
            submitNotification(receipt, () -> {
                for (var active : manager.getActiveNotifications()) {
                    if (active.getId() == id && active.getTag() == null && active.getNotification().extras != null) {
                        return active.getNotification().extras.getString(NOTIFICATION_RECEIPT);
                    }
                }
                return null;
            }, () -> manager.notify(id, new Notification.Builder(context, CHANNEL)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle(title)
                    .setContentText(detail.replace('\n', ' '))
                    .setStyle(new Notification.BigTextStyle().bigText(detail))
                    .addExtras(extras).setContentIntent(tap).setAutoCancel(true).setOnlyAlertOnce(true).build()));
            return true;
        } catch (SecurityException denied) {
            return false;
        }
    }

    private static final String NOTIFICATION_RECEIPT = "jp.valuehunter.privatewatch.delivery";

    static String notificationReceipt(String title, String detail) {
        return UsReferenceAlerts.sha256((title.length() + ":" + title + detail)
                .getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    static void submitNotification(String receipt, java.util.function.Supplier<String> active, Runnable post) {
        if (!receipt.equals(active.get())) post.run();
    }
}
