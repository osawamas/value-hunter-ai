package jp.valuehunter.privatewatch;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;

import androidx.work.Configuration;
import androidx.work.ListenableWorker;
import androidx.work.OneTimeWorkRequest;
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
import java.util.concurrent.TimeUnit;
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

        var config = new Configuration.Builder().setExecutor(new SynchronousExecutor())
                .setWorkerFactory(new WorkerFactory() {
                    @Override public ListenableWorker createWorker(Context appContext, String name,
                                                                    WorkerParameters parameters) {
                        if (!name.equals(JpxWatchWorker.class.getName())) return null;
                        var input = inputs.get();
                        return new JpxWatchWorker(appContext, parameters, ignored -> input.comparison(),
                                ignored -> input.rights());
                    }
                }).build();
        WorkManagerTestInitHelper.initializeTestWorkManager(context, config);
        var work = WorkManager.getInstance(context);
        var notifications = context.getSystemService(NotificationManager.class);
        var state = ScanWorker.prefs(context);
        notifications.cancelAll();
        if (!notifications.areNotificationsEnabled()) throw new AssertionError("Test notification permission missing");
        try {
            JpxWatchWorker.setEnabled(context, true);
            var jobs = work.getWorkInfosForUniqueWork(JpxWatchWorker.WORK).get(15, TimeUnit.SECONDS);
            if (jobs.size() != 1 || jobs.get(0).getState() != WorkInfo.State.ENQUEUED) {
                throw new AssertionError("JPX monitoring did not schedule one periodic worker");
            }
            // Leave the periodic work's network constraint unmet. Drive the same worker via WorkManager.
            runScan(work);
            if (!state.getString(JpxWatchWorker.STATUS, "").startsWith(FRIDAY.toString())) {
                throw new AssertionError("The first watch scan did not save a baseline");
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(published, JpxShareRights.load(context)));
            runScan(work);
            if (!state.getString(JpxWatchWorker.STATUS, "").contains("保留 3銘柄")) {
                throw new AssertionError("Official data with missing rights months did not stay on hold");
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(new JpxDailyCheck.Comparison(
                    sample(MONDAY, "900.00"), sample(FRIDAY, "920.00")), complete));
            runScan(work);
            verifySilentNotification(notifications);

            notifications.cancelAll();
            runScan(work);
            expectQuiet(notifications);
        } finally {
            JpxWatchWorker.setEnabled(context, false);
        }
    }

    private static void runScan(WorkManager work) throws Exception {
        var request = new OneTimeWorkRequest.Builder(JpxWatchWorker.class).build();
        work.enqueue(request).getResult().get(15, TimeUnit.SECONDS);
        for (int attempt = 0; attempt < 50; attempt++) {
            var info = work.getWorkInfoById(request.getId()).get(5, TimeUnit.SECONDS);
            if (info != null && info.getState() == WorkInfo.State.SUCCEEDED) return;
            if (info != null && info.getState().isFinished()) {
                throw new AssertionError("JPX worker ended in " + info.getState());
            }
            Thread.sleep(100);
        }
        throw new AssertionError("JPX worker did not complete through WorkManager");
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

    private static JpxDailyCheck.Report sample(LocalDate day, String close) {
        return new JpxDailyCheck.Report(day, "", Map.of("3861",
                new JpxCloseTable.Sessions(null, new BigDecimal(close))), Set.of());
    }
}
