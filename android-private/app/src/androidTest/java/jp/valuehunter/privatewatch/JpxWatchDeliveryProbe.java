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
import androidx.work.testing.TestWorkerBuilder;
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
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

final class JpxWatchDeliveryProbe {
    private static final LocalDate FRIDAY = LocalDate.of(2026, 11, 13);
    private static final LocalDate MONDAY = LocalDate.of(2026, 11, 16);

    private record Inputs(JpxDailyCheck.Comparison comparison, JpxShareRights rights) {}

    static void run(Context context, File directory, JpxShareRights rights,
                    JpxStockUniverse universe) throws Exception {
        verifyOutcomeComparison(context, directory);
        var updatedMonths = new HashSet<>(rights.months());
        updatedMonths.add(YearMonth.of(2026, 10));
        var octoberRights = new JpxShareRights(rights.coveredCodes(), updatedMonths, rights.notices());
        var published = new JpxDailyCheck.Comparison(
                JpxDailyCheck.readReport(context, new File(directory, "jpx-20261116.pdf"), MONDAY, universe, ""),
                JpxDailyCheck.readReport(context, new File(directory, "jpx-20261113.pdf"), FRIDAY, universe, ""));
        var months = new HashSet<YearMonth>();
        for (int month = 4; month <= 9; month++) months.add(YearMonth.of(2026, month));
        var review = new JpxIssuerArchive.Review(LocalDate.of(2026, 10, 1), MONDAY.plusDays(4));
        var complete = new JpxShareRights(Set.of("3861"), months, List.of(), Map.of("3861", review));
        var inputs = new AtomicReference<>(new Inputs(new JpxDailyCheck.Comparison(
                sample(FRIDAY, "900.00"), sample(FRIDAY.minusDays(1), "920.00")), complete));

        var starts = new AtomicInteger();
        var denyAlert = new AtomicBoolean();
        var lastProcessedKey = new AtomicReference<String>();
        var executor = new SynchronousExecutor();
        var factory = new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context appContext, String name,
                                                            WorkerParameters parameters) {
                if (!name.equals(JpxWatchWorker.class.getName())) return null;
                var input = inputs.get();
                return new JpxWatchWorker(appContext, parameters, (ignored, key, revision) -> {
                    starts.incrementAndGet();
                    lastProcessedKey.set(key);
                    return input.comparison();
                }, ignored -> new JpxShareRights.Selection(input.rights(), "", "probe-revision"),
                        (app, id, title, detail) -> !denyAlert.get()
                                && ScanWorker.postNotification(app, id, title, detail));
            }
        };
        var config = new Configuration.Builder().setExecutor(executor).setWorkerFactory(factory).build();
        WorkManagerTestInitHelper.initializeTestWorkManager(context, config);
        var work = WorkManager.getInstance(context);
        var driver = WorkManagerTestInitHelper.getTestDriver();
        var notifications = context.getSystemService(NotificationManager.class);
        var state = ScanWorker.prefs(context);
        notifications.cancelAll();
        if (!notifications.areNotificationsEnabled()) throw new AssertionError("Test notification permission missing");
        try {
            if (JpxWatchWorker.checkNow(context)) {
                throw new AssertionError("Manual JPX monitoring was queued while disabled");
            }
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

            inputs.set(new Inputs(published, rights));
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 2);
            String checked = JpxWatchWorker.displayStatus(state);
            if (!checked.contains("最終確認") || !checked.contains("（日本時間）")
                    || !checked.contains("保留 " + JpxDailyCheck.WATCH_CODES.size() + "銘柄") || !checked.contains("比較日 2026-11-13")
                    || !checked.contains("終値取得 3676 / 3686銘柄")
                    || !checked.contains("財務照合済み 0 / 登録 " + JpxDailyCheck.WATCH_CODES.size() + "銘柄")
                    || !checked.contains("1301・3861・7203 · 権利落月報の未確認月 2026-10、2026-11")
                    || checked.contains("<a")) {
                throw new AssertionError("JPX status did not show the official reports' hold reason: " + checked);
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(published, octoberRights));
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 3);
            String updated = JpxWatchWorker.displayStatus(state);
            if (!updated.contains("保留 " + JpxDailyCheck.WATCH_CODES.size() + "銘柄")
                    || !updated.contains("1301・3861・7203 · 権利落月報の未確認月 2026-11")
                    || updated.contains("未確認月 2026-10")) {
                throw new AssertionError("New monthly coverage did not update the watch status: " + updated);
            }
            expectQuiet(notifications);

            inputs.set(new Inputs(null, octoberRights));
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 4);
            String unchanged = JpxWatchWorker.displayStatus(state);
            if (!unchanged.contains("版に変更なし · PDFの再取得を省略")
                    || !unchanged.contains("保留 " + JpxDailyCheck.WATCH_CODES.size() + "銘柄") || !unchanged.contains("最終確認")
                    || !unchanged.contains("未確認月 2026-11")) {
                throw new AssertionError("The no-change check dropped the previous screening status");
            }
            expectQuiet(notifications);

            String previousStatus = state.getString(JpxWatchWorker.STATUS, "");
            inputs.set(new Inputs(new JpxDailyCheck.Comparison(sample(MONDAY.plusDays(1), "900.00"), null),
                    complete));
            for (int attempt = 0; attempt <= 2; attempt++) {
                var worker = TestWorkerBuilder.from(context, JpxWatchWorker.class, executor)
                        .setWorkerFactory(factory).setRunAttemptCount(attempt).build();
                boolean retry = attempt < 2;
                var expectedResult = retry ? ListenableWorker.Result.retry() : ListenableWorker.Result.success();
                var result = worker.doWork();
                String status = JpxWatchWorker.displayStatus(state);
                if (!result.equals(expectedResult)
                        || !status.contains("比較用の日報を取得できなかった")
                        || !status.contains("優先候補 1銘柄")
                        || status.contains("再試行を予約した") != retry
                        || !previousStatus.equals(state.getString(JpxWatchWorker.STATUS, ""))) {
                    throw new AssertionError("Incomplete comparison changed the last verified status: " + status);
                }
                expectQuiet(notifications);
            }

            inputs.set(new Inputs(new JpxDailyCheck.Comparison(
                    sample(MONDAY, "900.00"), sample(FRIDAY, "920.00")), complete));
            denyAlert.set(true);
            var blocked = TestWorkerBuilder.from(context, JpxWatchWorker.class, executor)
                    .setWorkerFactory(factory).setRunAttemptCount(0).build().doWork();
            denyAlert.set(false);
            String blockedStatus = JpxWatchWorker.displayStatus(state);
            if (!blocked.equals(ListenableWorker.Result.retry())
                    || !blockedStatus.contains("無音通知を送信できなかった")
                    || !blockedStatus.contains("再試行を予約した")) {
                throw new AssertionError("JPX did not retry a blocked alert: " + blocked + " " + blockedStatus);
            }
            expectQuiet(notifications);

            var power = context.getSystemService(PowerManager.class);
            if (power.isInteractive()) throw new AssertionError("Emulator display was awake before the alert");
            if (!JpxWatchWorker.checkNow(context) || !JpxWatchWorker.checkNow(context)) {
                throw new AssertionError("The enabled monitor could not queue an immediate check");
            }
            var manualId = pendingManual(work);
            driver.setAllConstraintsMet(manualId);
            awaitManual(work, manualId);
            if (starts.get() != 9 || !lastProcessedKey.get().isEmpty()) {
                throw new AssertionError("JPX skipped rechecking a blocked alert or ran duplicate work");
            }
            verifySilentNotification(notifications);
            if (!AlertOutcomes.report(context, AlertOutcomes.Market.JPX).contains("3861 · 従来条件")) {
                throw new AssertionError("JPX financial delivery was not recorded by the outcome pilot");
            }

            notifications.cancelAll();
            driver.setAllConstraintsMet(id);
            driver.setPeriodDelayMet(id);
            awaitRun(work, id, starts, 10);
            if (lastProcessedKey.get().isEmpty()) {
                throw new AssertionError("JPX did not save the edition after submitting the alert");
            }
            expectQuiet(notifications);

            JpxWatchWorker.checkNow(context);
            var cancelledManual = pendingManual(work);
            JpxWatchWorker.setEnabled(context, false);
            awaitCancelled(work, id);
            awaitCancelled(work, cancelledManual);
            if (JpxWatchWorker.enabled(context) || starts.get() != 10
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
            awaitRun(work, restartedId, starts, 11);
            expectQuiet(notifications);
            verifyTestNotification(context, notifications);
        } finally {
            JpxWatchWorker.setEnabled(context, false);
        }
    }

    private static void verifyOutcomeComparison(Context context, File directory) throws Exception {
        var market = AlertOutcomes.Market.JPX;
        var real = JpxDailyCheck.readReport(context, new File(directory, "jpx-20261116.pdf"), MONDAY,
                new JpxStockUniverse(MONDAY, Set.of("1306", "3861")), "");
        if (real.close("1306") == null || real.close("3861") == null) {
            throw new AssertionError("JPX PDF did not provide both TOPIX ETF and stock closes");
        }
        long posted = java.time.Instant.parse("2026-11-20T08:00:00Z").toEpochMilli();
        var window = AlertOutcomes.window(market, posted);
        if (!window.entry().equals(LocalDate.of(2026, 11, 24))
                || !window.exit().equals(LocalDate.of(2026, 12, 22))) {
            throw new AssertionError("JPX outcome window did not skip the November holiday");
        }
        var file = new android.util.AtomicFile(File.createTempFile("jpx-outcomes-probe", ".json", context.getCacheDir()));
        file.delete();
        try {
            var alert = new NotificationHistory.Entry("jpx-outcome-probe", posted, "test", "test");
            AlertOutcomes.add(file, market, alert, Map.of("3861", "割安", "7203", "割安"), posted);
            var rights = new JpxShareRights(Set.of(), Set.of(YearMonth.of(2026, 11), YearMonth.of(2026, 12)),
                    List.of(), Map.of(), List.of(new JpxShareRights.Adjustment("7203", window.exit(),
                    window.exit().plusDays(2), BigDecimal.ONE, BigDecimal.valueOf(2))));
            if (!rights.splitMonthsCovered(window.entry(), window.exit())) {
                throw new AssertionError("Complete monthly split evidence rejected");
            }
            AlertOutcomes.evaluate(file, market, window.exit(), () -> false, range -> false,
                    (range, codes) -> { throw new AssertionError("JPX fetched quotes before rights verification"); });
            AlertOutcomes.evaluate(file, market, window.exit(), () -> false,
                    range -> rights.splitMonthsCovered(range.entry(), range.exit()),
                    (range, codes) -> JpxAlertOutcomes.prices(range, codes, rights, () -> false, (day, eligible) -> {
                        if (!eligible.equals(Set.of("3861", "1306"))) {
                            throw new AssertionError("Split stock remained eligible or TOPIX ETF missing");
                        }
                        boolean entry = day.equals(range.entry());
                        return new JpxDailyCheck.Report(day, "fixture", Map.of(
                                "3861", new JpxCloseTable.Sessions(null, BigDecimal.valueOf(entry ? 100 : 108)),
                                "1306", new JpxCloseTable.Sessions(null, BigDecimal.valueOf(entry ? 100 : 103))), Set.of());
                    }));
            String result = AlertOutcomes.report(file, market);
            if (!result.contains("銘柄 +8.00% · 1306 +3.00% · 差 +5.00ポイント")
                    || !result.contains("計測済み 1件 · 待ち 1件")) {
                throw new AssertionError("Unexpected JPX outcome: " + result);
            }
        } finally {
            file.delete();
        }
    }

    static void verifyWifiRecovery(Context context, Runnable disconnect, Runnable reconnect) throws Exception {
        var months = new HashSet<YearMonth>();
        for (int month = 4; month <= 9; month++) months.add(YearMonth.of(2026, month));
        var review = new JpxIssuerArchive.Review(LocalDate.of(2026, 10, 1), MONDAY.plusDays(4));
        var rights = new JpxShareRights(Set.of("3861"), months, List.of(), Map.of("3861", review));
        var inputs = new AtomicReference<>(new JpxDailyCheck.Comparison(
                sample(FRIDAY, "920.00"), sample(FRIDAY.minusDays(1), "920.00")));
        var expected = new AtomicReference<>(FRIDAY);
        var unavailable = new AtomicBoolean();
        var interrupt = new AtomicBoolean();
        var resumed = new AtomicInteger();
        var factory = new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context app, String name, WorkerParameters parameters) {
                return new JpxWatchWorker(app, parameters, (ignored, key, revision) -> {
                    if (unavailable.get()) throw new java.io.IOException("Fixture delivery failed");
                    return inputs.get();
                },
                        ignored -> new JpxShareRights.Selection(rights, "", "wifi-recovery-probe"),
                        (target, id, title, detail) -> {
                            if (interrupt.getAndSet(false)) {
                                disconnect.run();
                                return false;
                            }
                            if (ScanWorker.postNotification(target, id, title, detail)) {
                                resumed.incrementAndGet();
                                return true;
                            }
                            return false;
                        }, expected::get);
            }
        };
        var manager = context.getSystemService(NotificationManager.class);
        var state = ScanWorker.prefs(context);
        try {
            JpxWatchWorker.setEnabled(context, true);
            var initial = TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                    .setWorkerFactory(factory).build().doWork();
            if (!initial.equals(ListenableWorker.Result.success())) throw new AssertionError("JPX baseline failed");

            inputs.set(new JpxDailyCheck.Comparison(sample(MONDAY, "900.00"), sample(FRIDAY, "920.00")));
            expected.set(MONDAY);
            interrupt.set(true);
            long oldRoute = MarketNetwork.generation();
            var lost = TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                    .setWorkerFactory(factory).build().doWork();
            if (!lost.equals(ListenableWorker.Result.retry()) || resumed.get() != 0 || interrupt.get()) {
                throw new AssertionError("JPX did not suspend the old run");
            }
            expectQuiet(manager);
            reconnect.run();
            if (!MarketNetwork.interrupted(oldRoute)) {
                throw new AssertionError("The interrupted run could continue on the restored route");
            }

            // A later refresh can see a different report edition. Delivery must use the queued old result.
            inputs.set(null);
            for (int attempt = 0; attempt < 2; attempt++) {
                var result = TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                        .setWorkerFactory(factory).build().doWork();
                if (!result.equals(ListenableWorker.Result.success())) throw new AssertionError("JPX recovery failed");
                if (attempt == 0) {
                    if (!MarketUpdate.JPX.display(state).contains("最終更新")) {
                        throw new AssertionError("JPX completion time was not saved");
                    }
                    verifySilentNotification(manager);
                    manager.cancelAll();
                }
            }
            expectQuiet(manager);
            long receipts = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis())
                    .stream().filter(row -> row.title().equals("東証日報で参考条件入り 1銘柄")
                            && row.detail().contains("3861") && row.detail().contains(MONDAY.toString())).count();
            if (receipts != 1 || resumed.get() != 1) throw new AssertionError("JPX recovery lost or repeated the alert");
            if (!JpxWatchWorker.displayFreshness(state).contains(MONDAY + " の取引分 · 判定済み")) {
                throw new AssertionError("JPX did not display the screened trading day");
            }

            LocalDate next = MONDAY.plusDays(1);
            expected.set(next);
            checkFreshness(context, factory, MarketFreshness.Phase.PUBLICATION, MONDAY);
            inputs.set(new JpxDailyCheck.Comparison(sample(next, "920.00"), sample(FRIDAY, "920.00")));
            checkFreshness(context, factory, MarketFreshness.Phase.COMPARISON, MONDAY);
            unavailable.set(true);
            checkFreshness(context, factory, MarketFreshness.Phase.ERROR, MONDAY);
            unavailable.set(false);
            inputs.set(new JpxDailyCheck.Comparison(sample(next, "920.00"), sample(MONDAY, "900.00")));
            checkFreshness(context, factory, MarketFreshness.Phase.FINANCE, next);
            if (!MarketCoverage.JPX.summary(state).contains("終値確認 1 / 1銘柄")
                    || !MarketCoverage.JPX.summary(state).contains("割安判定 1 / 1銘柄")
                    || !MarketCoverage.JPX.groups(state).isEmpty()) {
                throw new AssertionError("JPX coverage does not match the assessed fixture: " + MarketCoverage.JPX.summary(state));
            }
            inputs.set(null);
            long alertGeneration = state.getLong(ScanWorker.ALERT_GENERATION, 0);
            long oldFinancial = state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0);
            var posted = queuedAlert(MONDAY, alertGeneration, oldFinancial)
                    .put("title", "前の取引日に投稿した東証通知").put("detail", "前の取引日の成績復元 3861")
                    .put("codes", new org.json.JSONArray().put("3861"));
            if (!ScanWorker.postNotification(context, posted.getInt("id"), posted.getString("title"),
                    posted.getString("detail"))) {
                throw new AssertionError("Cannot prepare a submitted JPX alert from the previous session");
            }
            var original = AlertOutcomes.deliveredEntry(context, posted.getInt("id"), posted.getString("title"),
                    posted.getString("detail"), System.currentTimeMillis());
            if (original == null) throw new AssertionError("Missing original JPX delivery receipt");
            manager.cancelAll();
            var stale = new org.json.JSONArray()
                    .put(posted)
                    .put(queuedAlert(MONDAY, alertGeneration, oldFinancial + 1))
                    .put(queuedAlert(next, alertGeneration, oldFinancial));
            if (!state.edit().putLong(ScanWorker.FINANCIAL_ALERT_GENERATION, oldFinancial + 1)
                    .putString("jpx_watch_pending", stale.toString()).commit()) {
                throw new AssertionError("Cannot save stale JPX queue fixture");
            }
            try {
                var pass = TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                        .setWorkerFactory(factory).build().doWork();
                if (!pass.equals(ListenableWorker.Result.success()) || resumed.get() != 1
                        || !"[]".equals(state.getString("jpx_watch_pending", ""))) {
                    throw new AssertionError("Old JPX trading day or old financial rules stayed queued");
                }
                var file = new android.util.AtomicFile(new File(context.getNoBackupFilesDir(),
                        "jpx-alert-outcomes-v1.json"));
                var ledger = new org.json.JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
                if (ledger.getJSONObject(original.receipt() + ":3861").getLong("at") != original.postedAt()) {
                    throw new AssertionError("Old JPX delivery lost its original timestamp or outcome");
                }
            } finally {
                state.edit().putLong(ScanWorker.FINANCIAL_ALERT_GENERATION, oldFinancial).commit();
            }
            var muted = queuedAlert(next, alertGeneration, oldFinancial)
                    .put("title", "無音通知をオフにする前に投稿した東証通知")
                    .put("detail", "設定変更後の成績復元 3861")
                    .put("codes", new org.json.JSONArray().put("3861"));
            if (!ScanWorker.postNotification(context, muted.getInt("id"), muted.getString("title"),
                    muted.getString("detail"))) throw new AssertionError("Cannot submit the JPX alert before muting");
            var beforeMute = AlertOutcomes.deliveredEntry(context, muted.getInt("id"), muted.getString("title"),
                    muted.getString("detail"), System.currentTimeMillis());
            if (beforeMute == null) throw new AssertionError("Missing the pre-mute delivery receipt");
            manager.cancelAll();
            if (!state.edit().putString("jpx_watch_pending", new org.json.JSONArray().put(muted)
                    .put(queuedAlert(next, alertGeneration, oldFinancial)).toString()).commit()) {
                throw new AssertionError("Cannot queue the submitted alert and the unsent alert");
            }
            ScanWorker.setNotificationsRequested(state, false);
            try {
                var pass = TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                        .setWorkerFactory(factory).build().doWork();
                if (!pass.equals(ListenableWorker.Result.success()) || resumed.get() != 1
                        || !"[]".equals(state.getString("jpx_watch_pending", ""))) {
                    throw new AssertionError("Muting notifications replayed or retained a pending JPX alert");
                }
                var file = new android.util.AtomicFile(new File(context.getNoBackupFilesDir(),
                        "jpx-alert-outcomes-v1.json"));
                var ledger = new org.json.JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
                if (ledger.getJSONObject(beforeMute.receipt() + ":3861").getLong("at") != beforeMute.postedAt()) {
                    throw new AssertionError("Muting notifications lost the pre-mute alert outcome");
                }
            } finally {
                ScanWorker.setNotificationsRequested(state, true);
            }
            expectQuiet(manager);
        } finally {
            JpxWatchWorker.setEnabled(context, false);
            manager.cancelAll();
        }
    }

    private static org.json.JSONObject queuedAlert(LocalDate day, long alertGeneration, long financialGeneration)
            throws org.json.JSONException {
        return new org.json.JSONObject().put("day", day.toString()).put("id", 5)
                .put("title", "古いテスト通知").put("detail", "古い条件").put("codes", new org.json.JSONArray())
                .put("error", "古い通知を投稿した").put("alertGeneration", alertGeneration)
                .put("financialGeneration", financialGeneration);
    }

    private static void checkFreshness(Context context, WorkerFactory factory, MarketFreshness.Phase phase,
                                       LocalDate screenedDay) {
        TestWorkerBuilder.from(context, JpxWatchWorker.class, new SynchronousExecutor())
                .setWorkerFactory(factory).build().doWork();
        var state = ScanWorker.prefs(context);
        var market = MarketFreshness.JPX;
        if (phase != market.phase(state) || !screenedDay.equals(market.day(state))
                || !JpxWatchWorker.displayFreshness(state).contains(screenedDay + " の取引分 · 判定済み")) {
            throw new AssertionError("Unexpected JPX freshness: " + JpxWatchWorker.displayFreshness(state));
        }
    }

    private static UUID pendingManual(WorkManager work) throws Exception {
        var jobs = work.getWorkInfosForUniqueWork(JpxWatchWorker.MANUAL).get(15, TimeUnit.SECONDS)
                .stream().filter(info -> !info.getState().isFinished()).toList();
        if (jobs.size() != 1 || jobs.get(0).getPeriodicityInfo() != null
                || jobs.get(0).getConstraints().getRequiredNetworkType() != NetworkType.CONNECTED) {
            throw new AssertionError("JPX did not queue exactly one connected manual check: " + jobs);
        }
        return jobs.get(0).getId();
    }

    private static void awaitManual(WorkManager work, UUID id) throws Exception {
        for (int attempt = 0; attempt < 80; attempt++) {
            var info = work.getWorkInfoById(id).get(5, TimeUnit.SECONDS);
            if (info != null && info.getState() == WorkInfo.State.SUCCEEDED) return;
            if (info != null && info.getState().isFinished()) {
                throw new AssertionError("JPX immediate check ended in " + info.getState());
            }
            Thread.sleep(100);
        }
        throw new AssertionError("JPX immediate check did not finish");
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
                new JpxCloseTable.Sessions(null, new BigDecimal(close))), Set.of(), "probe-" + day);
    }
}
