package jp.valuehunter.privatewatch;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.os.PowerManager;
import android.provider.Settings;

import androidx.work.Configuration;
import androidx.work.ListenableWorker;
import androidx.work.NetworkType;
import androidx.work.WorkInfo;
import androidx.work.WorkManager;
import androidx.work.WorkerFactory;
import androidx.work.WorkerParameters;
import androidx.work.testing.SynchronousExecutor;
import androidx.work.testing.WorkManagerTestInitHelper;

import java.io.File;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.YearMonth;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class JpxWatchDeliveryProbe {
    private static final LocalDate FRIDAY = LocalDate.of(2026, 11, 13);
    private static final LocalDate MONDAY = LocalDate.of(2026, 11, 16);

    private record Inputs(JpxDailyCheck.Comparison comparison, JpxShareRights rights) {}

    static void run(Context context, File directory) throws Exception {
        var published = new JpxDailyCheck.Comparison(
                JpxDailyCheck.readReport(new File(directory, "jpx-20261116.pdf"), MONDAY),
                JpxDailyCheck.readReport(new File(directory, "jpx-20261113.pdf"), FRIDAY));
        var months = new HashSet<YearMonth>();
        for (int month = 4; month <= 11; month++) months.add(YearMonth.of(2026, month));
        var complete = new JpxShareRights(Set.of("3861"), months, List.of());
        var inputs = new AtomicReference<>(new Inputs(new JpxDailyCheck.Comparison(
                sample(FRIDAY, "900.00"), sample(FRIDAY.minusDays(1), "920.00")), complete));

        var starts = new AtomicInteger();
        var config = new Configuration.Builder().setExecutor(new SynchronousExecutor())
                .setWorkerFactory(new WorkerFactory() {
                    @Override public ListenableWorker createWorker(Context appContext, String name,
                                                                    WorkerParameters parameters) {
                        if (!name.equals(JpxWatchWorker.class.getName())) return null;
                        var input = inputs.get();
                        return new JpxWatchWorker(appContext, parameters, (ignored, key, revision) -> {
                            starts.incrementAndGet();
                            return input.comparison();
                        }, ignored -> new JpxShareRights.Selection(input.rights(), "", ""));
                    }
                }).build();
        WorkManagerTestInitHelper.initializeTestWorkManager(context, config);
        var work = WorkManager.getInstance(context);
        var driver = WorkManagerTestInitHelper.getTestDriver();
        var notifications = context.getSystemService(NotificationManager.class);
        var state = ScanWorker.prefs(context);
        notifications.cancelAll();
        if (!notifications.areNotificationsEnabled()) throw new AssertionError("Test notification permission missing");
        try {
            JpxWatchWorker.setEnabled(context, true);
            var job = registered(work);
            JpxWatchWorker.setEnabled(context, true);
            if (!registered(work).getId().equals(job.getId()) || starts.get() != 0) {
                throw new AssertionError("JPX scheduled duplicate work or ran before it was connected");
            }
            var id = job.getId();
            driver.setAllConstraintsMet(id);
            awaitRun(work, id, starts, 1);
            if (!state.getString(JpxWatchWorker.STATUS, "").startsWith(FRIDAY.toString())) {
                throw new AssertionError("The first watch scan did not save a baseline");
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(published, JpxShareRights.load(context)));
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 2);
            String checked = JpxWatchWorker.displayStatus(state);
            if (!checked.contains("最終確認") || !checked.contains("（日本時間）")
                    || !checked.contains("保留 3銘柄") || !checked.contains("比較日 2026-11-13")
                    || !checked.contains("1301・3861・7203 · 権利落月報の未確認月 2026-10、2026-11")
                    || checked.contains("<a")) {
                throw new AssertionError("JPX status did not show the official reports' hold reason: " + checked);
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(null, JpxShareRights.load(context)));
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 3);
            String unchanged = JpxWatchWorker.displayStatus(state);
            if (!unchanged.contains("版に変更なし · PDFの再取得を省略")
                    || !unchanged.contains("保留 3銘柄") || !unchanged.contains("最終確認")) {
                throw new AssertionError("The no-change check dropped the previous screening status");
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(new JpxDailyCheck.Comparison(
                    sample(MONDAY, "900.00"), sample(FRIDAY, "920.00")), complete));
            var power = context.getSystemService(PowerManager.class);
            if (power.isInteractive()) throw new AssertionError("Emulator display was awake before the alert");
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 4);
            verifySilentNotification(notifications);

            notifications.cancelAll();
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 5);
            expectQuiet(notifications);
            JpxWatchWorker.setEnabled(context, false);
            awaitCancelled(work, id);
            if (JpxWatchWorker.enabled(context) || starts.get() != 5
                    || !JpxWatchWorker.displayStatus(state).isEmpty()) {
                throw new AssertionError("Disabling JPX monitoring did not stop and clear the previous watch");
            }

            JpxWatchWorker.setEnabled(context, true);
            var restarted = work.getWorkInfosForUniqueWork(JpxWatchWorker.WORK).get(15, TimeUnit.SECONDS)
                    .stream().filter(info -> info.getState() == WorkInfo.State.ENQUEUED).toList();
            if (restarted.size() != 1 || restarted.get(0).getId().equals(id)) {
                throw new AssertionError("JPX did not create a new periodic worker on re-enable");
            }
            var restartedId = restarted.get(0).getId();
            driver.setAllConstraintsMet(restartedId);
            awaitRun(work, restartedId, starts, 6);
            expectQuiet(notifications);
            verifyTestNotification(context, notifications);
        } finally {
            JpxWatchWorker.setEnabled(context, false);
        }
    }

    private static WorkInfo registered(WorkManager work) throws Exception {
        var jobs = work.getWorkInfosForUniqueWork(JpxWatchWorker.WORK).get(15, TimeUnit.SECONDS);
        if (jobs.size() != 1) throw new AssertionError("JPX did not enroll one periodic worker");
        var job = jobs.get(0);
        var period = job.getPeriodicityInfo();
        if (job.getState() != WorkInfo.State.ENQUEUED || period == null
                || period.getRepeatIntervalMillis() != TimeUnit.HOURS.toMillis(6)
                || job.getConstraints().getRequiredNetworkType() != NetworkType.CONNECTED) {
            throw new AssertionError("Unexpected JPX periodic work configuration: " + job);
        }
        return job;
    }

    private static void awaitRun(WorkManager work, UUID id, AtomicInteger starts, int expected)
            throws Exception {
        for (int attempt = 0; attempt < 100; attempt++) {
            var info = work.getWorkInfoById(id).get(5, TimeUnit.SECONDS);
            if (info != null && starts.get() == expected && info.getState() == WorkInfo.State.ENQUEUED) return;
            if (starts.get() > expected || (info != null && info.getState().isFinished())) {
                throw new AssertionError("Unexpected JPX run count or state: " + starts.get() + ", " + info);
            }
            Thread.sleep(100);
        }
        throw new AssertionError("JPX periodic worker did not finish run " + expected);
    }

    private static void awaitCancelled(WorkManager work, UUID id) throws Exception {
        for (int attempt = 0; attempt < 50; attempt++) {
            var info = work.getWorkInfoById(id).get(5, TimeUnit.SECONDS);
            if (info == null || info.getState() == WorkInfo.State.CANCELLED) return;
            Thread.sleep(100);
        }
        throw new AssertionError("JPX periodic worker remained active after disabling monitoring");
    }

    private static void expectQuiet(NotificationManager notifications) throws InterruptedException {
        // NotificationManager processes posts and cancellations asynchronously.
        Thread.sleep(300);
        if (notifications.getActiveNotifications().length != 0) {
            throw new AssertionError("JPX posted a notification for the baseline, hold, or duplicate");
        }
    }

    private static void verifySilentNotification(NotificationManager notifications) throws InterruptedException {
        var channel = notifications.getNotificationChannel(ScanWorker.CHANNEL);
        if (channel == null || channel.getImportance() != NotificationManager.IMPORTANCE_LOW
                || channel.getSound() != null || channel.shouldVibrate()) {
            throw new AssertionError("JPX notification channel is not silent");
        }
        for (int attempt = 0; attempt < 30; attempt++) {
            var active = notifications.getActiveNotifications();
            if (active.length == 1) {
                var note = active[0].getNotification();
                String title = note.extras.getCharSequence(Notification.EXTRA_TITLE, "").toString();
                String detail = note.extras.getCharSequence(Notification.EXTRA_BIG_TEXT, "").toString();
                if (title.contains("東証日報で参考条件入り") && detail.contains("3861 · 100株枠")
                        && detail.contains(MONDAY.toString())) return;
            }
            Thread.sleep(100);
        }
        throw new AssertionError("The expected JPX notice did not reach Android's notification manager");
    }

    private static void verifyTestNotification(Context context, NotificationManager notifications)
            throws InterruptedException {
        var intent = ScanWorker.alertSettings(context);
        if (!Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS.equals(intent.getAction())
                || !context.getPackageName().equals(intent.getStringExtra(Settings.EXTRA_APP_PACKAGE))
                || !ScanWorker.CHANNEL.equals(intent.getStringExtra(Settings.EXTRA_CHANNEL_ID))
                || !ScanWorker.alertsEnabled(context)) {
            throw new AssertionError("The app did not target the same settings used by the JPX worker");
        }
        ScanWorker.testNotification(context);
        try {
            for (int attempt = 0; attempt < 30; attempt++) {
                for (var active : notifications.getActiveNotifications()) {
                    var note = active.getNotification();
                    String title = note.extras.getCharSequence(Notification.EXTRA_TITLE, "").toString();
                    if (title.contains("無音通知テスト") && ScanWorker.CHANNEL.equals(note.getChannelId())) return;
                }
                Thread.sleep(100);
            }
            throw new AssertionError("The test notification did not use the JPX notification channel");
        } finally {
            notifications.cancelAll();
        }
    }

    private static JpxDailyCheck.Report sample(LocalDate day, String close) {
        return new JpxDailyCheck.Report(day, "", Map.of("3861",
                new JpxCloseTable.Sessions(null, new BigDecimal(close))), Set.of());
    }
}
