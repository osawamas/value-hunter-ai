package jp.valuehunter.privatewatch;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.util.AtomicFile;

import androidx.work.ListenableWorker;
import androidx.work.WorkerFactory;
import androidx.work.WorkerParameters;
import androidx.work.testing.SynchronousExecutor;
import androidx.work.testing.TestWorkerBuilder;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicInteger;
import java.time.LocalDate;

final class UsReferenceDeliveryProbe {
    private static final LocalDate FIRST = LocalDate.of(2026, 11, 16);
    private static final LocalDate SECOND = FIRST.plusDays(1);
    private static final String PROVIDER = UsDoltCloses.SOURCE;

    private UsReferenceDeliveryProbe() {}

    static void run(Context context) throws Exception {
        run(context, null, null);
    }

    static void run(Context context, Runnable disconnect, Runnable reconnect) throws Exception {
        var notifications = context.getSystemService(NotificationManager.class);
        var directory = context.getNoBackupFilesDir();
        var close = new AtomicFile(new File(directory, "us-daily-closes.json"));
        var checkpoint = new AtomicFile(new File(directory, "us-sec-financials.json"));
        var factRequests = new AtomicInteger();
        var extraRequests = new AtomicInteger();
        var indexRequests = new AtomicInteger();
        boolean wifi = disconnect != null;
        var factory = new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context app, String name, WorkerParameters parameters) {
                if (!name.equals(UsSecFinanceWorker.class.getName())) return null;
                return new UsSecFinanceWorker(app, parameters, url -> {
                    if (wifi && url.endsWith("/CIK0000043210.json")) {
                        extraRequests.incrementAndGet();
                        return facts().replace("12345", "43210");
                    }
                    if (wifi && url.endsWith("/CIK0000012345.json") && factRequests.get() == 0) {
                        disconnect.run();
                    }
                    String data = payload(url, factRequests, indexRequests);
                    if (wifi && url.endsWith("/otherlisted.txt")) {
                        return data.replace("File Creation", "AAA|Second Corp Common Stock|N|N|N\nFile Creation");
                    }
                    if (wifi && url.equals(UsDeviceFinancials.SEC_DIRECTORY)) {
                        return data.replace(
                                "\"TEST\",\"NYSE\"]]", "\"TEST\",\"NYSE\"],[43210,\"Second Corp\",\"AAA\",\"NYSE\"]]");
                    }
                    return data;
                });
            }
        };
        notifications.cancelAll();
        try {
            writeClose(close, FIRST, 20, wifi);
            verifyResult(context, factory, ListenableWorker.Result.retry());
            expectQuiet(notifications);
            if (wifi) {
                var saved = new JSONObject(new String(checkpoint.readFully(), java.nio.charset.StandardCharsets.UTF_8));
                if (saved.getInt("cursor") != 1 || saved.getJSONArray("results").length() != 1
                        || extraRequests.get() != 1 || !MarketNetwork.waitingForWifi()) {
                    throw new AssertionError("SEC did not persist the finished issuer and stop at the interrupted issuer");
                }
                reconnect.run();
            }
            verifyResult(context, factory, ListenableWorker.Result.success());
            expectQuiet(notifications);
            if (factRequests.get() != 2) throw new AssertionError("First day was not retried exactly once");

            writeClose(close, SECOND, 5, wifi);
            verifyResult(context, factory, ListenableWorker.Result.success());
            verifySilentNotice(notifications);

            notifications.cancelAll();
            verifyResult(context, factory, ListenableWorker.Result.success());
            expectQuiet(notifications);
            if (wifi) {
                verifyFreshness(context, checkpoint);
                var coverageState = ScanWorker.prefs(context);
                String coverage = MarketCoverage.US.summary(coverageState);
                if (!coverage.contains("監視対象 3銘柄") || !coverage.contains("終値確認 2 / 3銘柄")
                        || !coverage.contains("割安判定 2 / 3銘柄")
                        || !MarketCoverage.US.groups(coverageState).getOrDefault(MarketCoverage.Reason.DATED_LISTING, java.util.List.of())
                                .equals(java.util.List.of("OTHER"))) {
                    throw new AssertionError("US coverage lost an unpriced listing: " + coverage);
                }
                expectQuiet(notifications);
                long receipts = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis())
                        .stream().filter(row -> row.title().equals("米国株の参考条件入り 1銘柄")
                                && row.detail().contains("TEST") && row.detail().contains(SECOND.toString())).count();
                if (receipts != 1 || extraRequests.get() != 1
                        || !MarketUpdate.US_FINANCE.display(ScanWorker.prefs(context)).contains("最終更新")) {
                    throw new AssertionError("SEC recovery repeated an issuer, lost the update time, or duplicated delivery");
                }
            }
            if (factRequests.get() != 2 || indexRequests.get() != 2) {
                throw new AssertionError("Unchanged issuer was not reused after checking the SEC index");
            }
            if (wifi) {
                verifyMeterDelivery(context, notifications);
                verifyRejectedAlertCanBeRecalculated(context, notifications);
                verifyRetriedAlertUsesCorrectedLedger(context, notifications);
                verifyDeliveredAlertWithNewText(context, notifications);
                verifyDeliveryRecoveryOnNextSession(context, notifications);
                verifyBothOutcomeStoresFail(context, notifications);
                verifyOutdatedNotificationIgnored(context, notifications);
                verifyStaleBudgetClears(context);
                close.delete();
                verifyOutcomeRecoveryWithoutQuotes(context, notifications, factory);
            }
        } finally {
            notifications.cancelAll();
            close.delete();
            checkpoint.delete();
        }
    }

    private static void verifyMeterDelivery(Context context, NotificationManager notifications) throws Exception {
        var state = context.getSharedPreferences("us-meter-delivery-probe", Context.MODE_PRIVATE);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Could not prepare isolated meter settings");
        }
        String hash = "a".repeat(64);
        var before = meterLedger(FIRST, hash, 15);
        var after = meterLedger(SECOND, hash, 9);
        UsDailyWorker.applyFinancialScreen(context, state, before, FIRST, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        boolean done = UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash,
                () -> false, (app, id, title, detail) -> false);
        if (done || !UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("A failed submission did not keep the alert for retry");
        }
        expectQuiet(notifications);
        if (!UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false)
                || UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Retry did not acknowledge delivery");
        }
        verifySilentNotice(notifications, SECOND, "米国株 · かなり割安 · 割安度の新規・昇格 1銘柄",
                "METER · 100株 · かなり割安 · 84点");
        var receipts = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis());
        if (receipts.stream().noneMatch(row -> row.title().contains("かなり割安")
                && row.detail().contains("METER · 100株 · かなり割安 · 84点"))) {
            throw new AssertionError("US notification did not use the saved meter band");
        }
        var pilot = AlertOutcomes.report(context, AlertOutcomes.Market.US);
        if (!pilot.contains("METER · かなり割安") || !pilot.contains("計測待ち")) {
            throw new AssertionError("Delivered meter alert was not recorded for the forward test");
        }
        verifyOutcomeComparison(context);
        verifyCorruptHistoryCannotBeOverwritten(context);
        verifyOutcomeRetryDoesNotBlockOtherWindows(context);
        verifyOutcomeRecovery(context);
        verifySnapshotWriteVerification(context);
        verifyDuplicateOutcomeSkipsUnnecessaryWrite(context);
        verifyOutcomeWriteFailureRecovery(context, AlertOutcomes.Market.US);
        verifyOutcomeWriteFailureRecovery(context, AlertOutcomes.Market.JPX);
        notifications.cancelAll();
        UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        if (!state.edit().putBoolean(ValueAlertPreview.LIVE, false).commit()) {
            throw new AssertionError("Cannot switch back to the conventional alert rules");
        }
        UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
    }

    private static void verifyOutcomeComparison(Context context) throws Exception {
        var temp = java.io.File.createTempFile("outcomes-probe", ".json", context.getCacheDir());
        var file = new android.util.AtomicFile(temp);
        file.delete();
        try {
            long posted = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
            var entry = new NotificationHistory.Entry("pilot-test", posted, "test", "test");
            var signals = java.util.Map.of("METER", "かなり割安", "ABSENT", "割安");
            AlertOutcomes.add(file, AlertOutcomes.Market.US, entry, signals, posted);
            AlertOutcomes.add(file, AlertOutcomes.Market.US, entry, signals, posted);
            var window = AlertOutcomes.window(AlertOutcomes.Market.US, posted);
            if (!window.entry().toString().equals("2026-11-27")
                    || !window.exit().toString().equals("2026-12-28")) {
                throw new AssertionError("US pilot window failed to skip Thanksgiving or Christmas");
            }
            AlertOutcomes.evaluate(file, AlertOutcomes.Market.US, window.exit().minusDays(1), () -> false, range -> true,
                    (range, symbols) -> { throw new AssertionError("An immature cohort requested prices"); });
            var rows = new JSONArray();
            for (String ticker : java.util.List.of("METER", "IWV")) {
                rows.put(new JSONObject().put("symbol", ticker).put("trading_date", window.entry().toString()).put("close", 100));
                rows.put(new JSONObject().put("symbol", ticker).put("trading_date", window.exit().toString())
                        .put("close", ticker.equals("IWV") ? 103 : 110));
            }
            var response = new JSONObject().put("query_execution_status", "Success").put("rows", rows);
            AlertOutcomes.evaluate(file, AlertOutcomes.Market.US, window.exit(), () -> false, range -> true,
                    (range, symbols) -> UsDoltCloses.outcomePrices(range, symbols, unused -> response));
            if (!AlertOutcomes.report(file, AlertOutcomes.Market.US).contains("計測済み 1件 · 待ち 1件 · 集計対象外 0件")) {
                throw new AssertionError("Missing closing prices were counted as a completed comparison");
            }
            AlertOutcomes.evaluate(file, AlertOutcomes.Market.US, window.exit().plusDays(7), () -> false, range -> true, (range, symbols) -> java.util.Map.of());
            var result = AlertOutcomes.report(file, AlertOutcomes.Market.US);
            if (!result.contains("計測済み 1件 · 待ち 0件 · 集計対象外 1件")
                    || !result.contains("差 +7.00ポイント")) {
                throw new AssertionError("Outcome did not persist fair close-to-close comparison: " + result);
            }
        } finally {
            file.delete();
        }
    }

    private static void verifyCorruptHistoryCannotBeOverwritten(Context context) throws Exception {
        var file = File.createTempFile("notification-history-corrupt", ".json", context.getCacheDir());
        long now = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
        String damaged = "{broken-history";
        try {
            java.nio.file.Files.writeString(file.toPath(), damaged, java.nio.charset.StandardCharsets.UTF_8);
            var posted = new AtomicInteger();
            try {
                NotificationHistory.deliver(file, "broken-receipt", "TEST", "TEST", now,
                        () -> 0L, posted::incrementAndGet, () -> {});
                throw new AssertionError("Corrupt history was treated as empty");
            } catch (IOException expected) {
                // No delivery is safe before a corrupted receipt history is recovered.
            }
            if (posted.get() != 0
                    || !damaged.equals(java.nio.file.Files.readString(file.toPath(), java.nio.charset.StandardCharsets.UTF_8))) {
                throw new AssertionError("Corrupted notification history was overwritten or alert repeated");
            }
            java.nio.file.Files.writeString(file.toPath(), "[]", java.nio.charset.StandardCharsets.UTF_8);
            if (!NotificationHistory.deliver(file, "broken-receipt", "TEST", "TEST", now,
                    () -> 0L, posted::incrementAndGet, () -> {})
                    || posted.get() != 1 || NotificationHistory.recent(file, now).size() != 1) {
                throw new AssertionError("Notification history did not recover after valid data was restored");
            }
            NotificationHistory.deliver(file, "broken-receipt", "TEST", "TEST", now,
                    () -> 0L, posted::incrementAndGet, () -> {});
            if (posted.get() != 1) throw new AssertionError("Recovered notification was duplicated");
        } finally {
            file.delete();
        }
    }

    private static void verifyOutcomeRetryDoesNotBlockOtherWindows(Context context) throws Exception {
        var file = new android.util.AtomicFile(java.io.File.createTempFile("outcomes-retry", ".json", context.getCacheDir()));
        file.delete();
        try {
            var market = AlertOutcomes.Market.US;
            long posted = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
            long later = posted + java.util.concurrent.TimeUnit.DAYS.toMillis(2);
            AlertOutcomes.add(file, market, new NotificationHistory.Entry("old", posted, "test", "test"),
                    java.util.Map.of("EARLY", "割安"), later);
            AlertOutcomes.add(file, market, new NotificationHistory.Entry("new", later, "test", "test"),
                    java.util.Map.of("LATER", "割安"), later);
            LocalDate latest = AlertOutcomes.window(market, later).exit().plusDays(8);
            var unavailable = new java.io.IOException("simulated price provider timeout");
            try {
                AlertOutcomes.evaluate(file, market, latest, () -> false, range -> true, (range, symbols) -> {
                    if (!symbols.contains("EARLY")) throw new AssertionError("Expected the older window first");
                    throw unavailable;
                });
                throw new AssertionError("Price provider failure was concealed");
            } catch (java.io.IOException expected) {
                if (expected != unavailable) throw expected;
            }
            if (!AlertOutcomes.report(file, market).contains("計測済み 0件 · 待ち 2件 · 集計対象外 0件")) {
                throw new AssertionError("An old window was excluded after a provider failure");
            }
            var deferred = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            var first = deferred.getJSONObject("old:EARLY");
            if (!latest.toString().equals(first.optString("checked"))
                    || first.optLong("retryAfterMs") <= System.currentTimeMillis()) {
                throw new AssertionError("Provider failure did not preserve a timed retry");
            }
            AlertOutcomes.evaluate(file, market, latest, () -> false, range -> true, (range, symbols) -> {
                if (!symbols.equals(java.util.Set.of("LATER", "IWV"))) {
                    throw new AssertionError("The failed window blocked a later window: " + symbols);
                }
                return java.util.Map.of("LATER", new AlertOutcomes.Prices(100, 107),
                        "IWV", new AlertOutcomes.Prices(100, 101));
            });
            if (!AlertOutcomes.report(file, market).contains("計測済み 1件 · 待ち 1件 · 集計対象外 0件")) {
                throw new AssertionError("Later outcome did not complete after an earlier timeout");
            }
            // The provider is back but the old range is still cooling down.
            AlertOutcomes.evaluate(file, market, latest, () -> false, range -> true,
                    (range, symbols) -> { throw new AssertionError("Retry ignored the provider cooldown"); });
            var expired = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            expired.getJSONObject("old:EARLY").put("retryAfterMs", System.currentTimeMillis() - 1000);
            UsDailyWorker.writeSnapshot(file, expired);
            AlertOutcomes.evaluate(file, market, latest, () -> false, range -> true, (range, symbols) -> {
                if (!symbols.equals(java.util.Set.of("EARLY", "IWV"))) {
                    throw new AssertionError("Timed retry lost the original comparison: " + symbols);
                }
                return java.util.Map.of("EARLY", new AlertOutcomes.Prices(100, 105),
                        "IWV", new AlertOutcomes.Prices(100, 101));
            });
            if (!AlertOutcomes.report(file, market).contains("計測済み 2件 · 待ち 0件 · 集計対象外 0件")) {
                throw new AssertionError("Provider recovery was not retried on the same closing date");
            }
        } finally {
            file.delete();
        }
    }

    private static void verifyOutcomeRecovery(Context context) throws Exception {
        var file = new android.util.AtomicFile(java.io.File.createTempFile("outcomes-recovery", ".json", context.getCacheDir()));
        file.delete();
        try {
            var market = AlertOutcomes.Market.US;
            long posted = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
            AlertOutcomes.add(file, market, new NotificationHistory.Entry("old", posted, "test", "test"),
                    java.util.Map.of("KEEP", "割安"), posted);
            var window = AlertOutcomes.window(market, posted);
            var ledger = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            ledger.put("invalid-row", "partial data");
            ledger.put("invalid-date", new JSONObject(ledger.getJSONObject("old:KEEP").toString()).put("exit", "bad"));
            UsDailyWorker.writeSnapshot(file, ledger);
            AlertOutcomes.add(file, market, new NotificationHistory.Entry("new", posted, "test", "test"),
                    java.util.Map.of("NEW", "割安"), posted);
            if (!AlertOutcomes.report(file, market).contains("計測済み 0件 · 待ち 2件 · 集計対象外 0件")) {
                throw new AssertionError("A damaged row blocked or changed valid notifications");
            }

            var stopped = new java.util.concurrent.atomic.AtomicBoolean();
            var interruption = new java.io.IOException("simulated Wi-Fi disconnect");
            try {
                AlertOutcomes.evaluate(file, market, window.exit(), stopped::get, range -> true, (range, symbols) -> {
                    stopped.set(true);
                    throw interruption;
                });
                throw new AssertionError("Interrupted retrieval did not abort");
            } catch (java.io.IOException expected) {
                if (expected != interruption) throw expected;
            }
            stopped.set(false);
            AlertOutcomes.evaluate(file, market, window.exit(), stopped::get, range -> true, (range, symbols) -> {
                if (!symbols.equals(java.util.Set.of("NEW", "KEEP", "IWV"))) {
                    throw new AssertionError("Wi-Fi recovery dropped pending comparisons");
                }
                var prices = new AlertOutcomes.Prices(100, 104);
                return java.util.Map.of("NEW", prices, "KEEP", prices, "IWV", prices);
            });
            if (!AlertOutcomes.report(file, market).contains("計測済み 2件 · 待ち 0件 · 集計対象外 0件")) {
                throw new AssertionError("Wi-Fi recovery could not process both valid comparisons on the same date");
            }
        } finally {
            file.delete();
        }
    }

    private static void verifySnapshotWriteVerification(Context context) throws Exception {
        var parent = File.createTempFile("snapshot-write-failure", ".test", context.getCacheDir());
        var blocked = new AtomicFile(new File(parent, "us-daily-closes.json"));
        var valid = new AtomicFile(File.createTempFile("snapshot-write-verified", ".json", context.getCacheDir()));
        valid.delete();
        try {
            var snapshot = new JSONObject().put("trading_date_et", "2026-11-23")
                    .put("source", "fixture").put("closes", new JSONArray().put(
                            new JSONObject().put("symbol", "TEST").put("close", 12)));
            try {
                UsDailyWorker.writeSnapshot(blocked, snapshot);
                throw new AssertionError("Blocked close snapshot was falsely acknowledged");
            } catch (IOException expected) {
                // The caller must retry without marking the close as saved.
            }
            UsDailyWorker.writeSnapshot(valid, snapshot);
            if (!java.util.Arrays.equals(snapshot.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8),
                    valid.readFully())) {
                throw new AssertionError("Verified close snapshot did not preserve exact bytes");
            }
        } finally {
            blocked.delete();
            valid.delete();
            parent.delete();
        }
    }

    private static void verifyDuplicateOutcomeSkipsUnnecessaryWrite(Context context) throws Exception {
        var target = File.createTempFile("outcomes-duplicate", ".json", context.getCacheDir());
        var regular = new AtomicFile(target);
        regular.delete();
        var retry = context.getSharedPreferences("outcomes-duplicate-probe", Context.MODE_PRIVATE);
        long now = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
        var entry = new NotificationHistory.Entry("duplicate", now, "test", "test");
        var signals = java.util.Map.of("STABLE", "割安");
        try {
            if (!retry.edit().clear().commit()) throw new AssertionError("Cannot clear test preferences");
            AlertOutcomes.add(regular, AlertOutcomes.Market.US, entry, signals, now);
            byte[] before = regular.readFully();
            // Once a receipt was committed, replay must not require another write.
            var blockedWrites = new AtomicFile(target) {
                @Override public java.io.FileOutputStream startWrite() throws IOException {
                    throw new IOException("simulated unavailable writer");
                }
            };
            AlertOutcomes.add(blockedWrites, AlertOutcomes.Market.US, entry, signals, now);
            if (!java.util.Arrays.equals(before, regular.readFully())) {
                throw new AssertionError("Duplicate outcome rewrote the saved receipt");
            }
            if (!retry.edit().putString("rows", new JSONObject().put("duplicate",
                    new JSONObject().put("at", now).put("signals", new JSONObject(signals))).toString()).commit()) {
                throw new AssertionError("Could not stage previously committed retry");
            }
            AlertOutcomes.recoverDeferred(blockedWrites, retry, AlertOutcomes.Market.US, now);
            if (retry.contains("rows") || !java.util.Arrays.equals(before, regular.readFully())) {
                throw new AssertionError("Recovered duplicate could not clear retry without rewriting ledger");
            }
            try {
                AlertOutcomes.add(blockedWrites, AlertOutcomes.Market.US,
                        new NotificationHistory.Entry("new", now, "test", "test"), signals, now);
                throw new AssertionError("A genuinely new receipt bypassed the write failure");
            } catch (IOException expected) {
                // New observations still require a successful ledger write.
            }
        } finally {
            retry.edit().clear().commit();
            regular.delete();
        }
    }

    private static void verifyOutcomeWriteFailureRecovery(Context context, AlertOutcomes.Market market)
            throws Exception {
        var parent = File.createTempFile("outcomes-write-failure", ".test", context.getCacheDir());
        var file = new AtomicFile(new File(parent, "outcomes.json"));
        var retry = context.getSharedPreferences("outcomes-write-failure-probe", Context.MODE_PRIVATE);
        long firstPosted = java.time.Instant.parse("2026-11-25T21:30:00Z").toEpochMilli();
        int count = 65;
        long now = firstPosted + count * 1000;
        try {
            if (!retry.edit().clear().commit()) throw new AssertionError("Cannot prepare outcome retry storage");
            // Do not acknowledge a delivered alert when its stable receipt is unavailable.
            if (AlertOutcomes.record(context, market, (NotificationHistory.Entry) null,
                    java.util.Map.of("UNRECEIPTED", "割安"), now)) {
                throw new AssertionError(market + " acknowledged an outcome without a receipt");
            }
            if (!AlertOutcomes.record(context, market, (NotificationHistory.Entry) null,
                    java.util.Map.of(), now)) {
                throw new AssertionError(market + " rejected a notification without outcome signals");
            }
            for (int i = 0; i < count; i++) {
                var alert = new NotificationHistory.Entry("receipt-" + i, firstPosted + i * 1000, "title", "detail");
                var signals = java.util.Map.of("FIXTURE" + i, i % 2 == 0 ? "割安" : "超割安");
                // A regular file at the parent path prevents the ledger from being written.
                AlertOutcomes.recordOrDefer(file, retry, market, alert, signals, now);
                if (i == 0) AlertOutcomes.recordOrDefer(file, retry, market, alert, signals, now);
            }
            // Replaying a submitted receipt with revised data must preserve the first
            // submission's timestamp and signal, even while the ledger is unwritable.
            var replay = new NotificationHistory.Entry("receipt-0", firstPosted + 999_000, "changed", "changed");
            var revised = java.util.Map.of("FIXTURE0", "再判定", "REVISED", "再判定");
            AlertOutcomes.recordOrDefer(file, retry, market, replay, revised, now);
            var firstPending = new JSONObject(retry.getString("rows", "{}")).getJSONObject("receipt-0");
            if (firstPending.getLong("at") != firstPosted
                    || !"割安".equals(firstPending.getJSONObject("signals").getString("FIXTURE0"))) {
                throw new AssertionError(market + " overwrote the original submitted receipt");
            }
            var pending = retry.getString("rows", "{}");
            if (new JSONObject(pending).length() != count) {
                throw new AssertionError(market + " lost a deferred outcome after 65 consecutive failures");
            }
            try {
                AlertOutcomes.recoverDeferred(file, retry, market, now);
                throw new AssertionError("Recovery unexpectedly wrote to the blocked ledger");
            } catch (IOException expected) {
                if (!pending.equals(retry.getString("rows", "{}"))) {
                    throw new AssertionError("Failed recovery changed the pending outcomes");
                }
            }
            if (!parent.delete() || !parent.mkdir()) throw new AssertionError("Cannot restore outcome storage");
            AlertOutcomes.recordOrDefer(file, retry, market, replay, revised, now);
            var restored = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            var first = restored.getJSONObject("receipt-0:FIXTURE0");
            if (first.getLong("at") != firstPosted || !"割安".equals(first.getString("rule"))
                    || restored.has("receipt-0:REVISED")) {
                throw new AssertionError(market + " used the replay instead of the deferred observation on recovery");
            }
            // Simulate restarting after committing the ledger but before clearing the retry data.
            if (!retry.edit().putString("rows", pending).commit()) throw new AssertionError("Cannot replay the retry data");
            AlertOutcomes.recoverDeferred(file, retry, market, now);

            var ledger = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            if (retry.contains("rows") || ledger.length() != count) {
                throw new AssertionError(market + " did not restore exactly 65 outcomes");
            }
            for (int i = 0; i < count; i++) {
                String symbol = "FIXTURE" + i;
                var row = ledger.getJSONObject("receipt-" + i + ":" + symbol);
                if (row.getLong("at") != firstPosted + i * 1000 || !symbol.equals(row.getString("symbol"))
                        || !(i % 2 == 0 ? "割安" : "超割安").equals(row.getString("rule"))) {
                    throw new AssertionError(market + " changed the original outcome at index " + i);
                }
            }
        } finally {
            retry.edit().clear().commit();
            file.delete();
            parent.delete();
        }
    }

    private static void verifyRejectedAlertCanBeRecalculated(Context context, NotificationManager notifications)
            throws Exception {
        var state = context.getSharedPreferences("us-meter-rule-change-probe", Context.MODE_PRIVATE);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare the rule-change probe");
        }
        String hash = "b".repeat(64);
        var before = meterLedger(FIRST, hash, 15);
        var after = meterLedger(SECOND, hash, 9);
        // This unsubmitted fixture must not match a receipt from another probe.
        after.getJSONObject("reference_screen").getJSONObject("meter_rows").getJSONArray("NYSE:12345:METER").put(0, 85);
        UsDailyWorker.applyFinancialScreen(context, state, before, FIRST, PROVIDER, hash, () -> false);
        if (UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false,
                (app, id, title, detail) -> false)) {
            throw new AssertionError("An unsent alert was acknowledged");
        }
        if (!state.edit().putBoolean(ValueAlertPreview.LIVE, false)
                .putLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 1).commit()) {
            throw new AssertionError("Cannot change the alert rules");
        }
        UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false);
        verifySilentNotice(notifications, "METER", SECOND);
        notifications.cancelAll();
        expectQuiet(notifications);
    }

    private static void verifyRetriedAlertUsesCorrectedLedger(Context context, NotificationManager notifications)
            throws Exception {
        var state = context.getSharedPreferences("us-meter-corrected-ledger-probe", Context.MODE_PRIVATE);
        String hash = "c".repeat(64);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare the same-day correction probe");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 15), FIRST, PROVIDER, hash, () -> false);
        var rises = meterLedger(SECOND, hash, 9);
        rises.getJSONObject("reference_screen").getJSONObject("meter_rows").getJSONArray("NYSE:12345:METER").put(0, 83);
        if (UsDailyWorker.applyFinancialScreen(context, state, rises, SECOND, PROVIDER, hash, () -> false,
                (app, id, title, detail) -> false) || !UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Unsubmitted meter alert was not queued");
        }

        // The close snapshot remains the same. Revised earnings make the old notification ineligible.
        var corrected = meterLedger(SECOND, hash, 9, true);
        if (!UsDailyWorker.applyFinancialScreen(context, state, corrected, SECOND, PROVIDER, hash, () -> false)
                || UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Corrected financial data did not invalidate the queued alert");
        }
        expectQuiet(notifications);
    }

    private static void verifyDeliveredAlertWithNewText(Context context, NotificationManager notifications)
            throws Exception {
        var state = context.getSharedPreferences("us-delivered-alert-recovery-probe", Context.MODE_PRIVATE);
        String hash = "d".repeat(64);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot set up delivery recovery");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 15), FIRST, PROVIDER, hash, () -> false);
        var current = meterLedger(SECOND, hash, 9);
        var scores = current.getJSONObject("reference_screen").getJSONObject("meter_rows");
        var meter = scores.getJSONArray("NYSE:12345:METER");
        meter.put(0, 81);
        if (UsDailyWorker.applyFinancialScreen(context, state, current, SECOND, PROVIDER, hash, () -> false,
                (app, id, title, detail) -> {
                    if (!detail.contains("81点") || !ScanWorker.postNotification(app, id, title, detail)) {
                        throw new AssertionError("Could not post the original alert");
                    }
                    // The worker stops after submission but before returning success and saving the sent set.
                    return false;
                }) || !UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Expected posted but unacknowledged alert");
        }
        notifications.cancelAll();
        expectQuiet(notifications);
        String originalSignals = state.getString("us_private_sec_pending_signals", "");
        String postedPending = state.getString("us_private_sec_pending", "");
        if (originalSignals.isEmpty() || postedPending.isEmpty()
                || !state.edit().putString("us_private_sec_pending_signals", "{broken-json").commit()) {
            throw new AssertionError("Could not inject malformed pending alert signals");
        }
        if (UsDailyWorker.recoverSubmittedFinancialAlert(context, state)
                || !postedPending.equals(state.getString("us_private_sec_pending", ""))) {
            throw new AssertionError("Malformed posted alert signals were acknowledged or discarded");
        }
        if (!state.edit().putString("us_private_sec_pending_signals", "{}").commit()) {
            throw new AssertionError("Could not inject empty pending alert signals");
        }
        if (UsDailyWorker.recoverSubmittedFinancialAlert(context, state)
                || !postedPending.equals(state.getString("us_private_sec_pending", ""))) {
            throw new AssertionError("Empty posted alert signals were acknowledged or discarded");
        }
        if (!state.edit().putString("us_private_sec_pending_signals", originalSignals).commit()) {
            throw new AssertionError("Could not restore original pending signals");
        }
        meter.put(0, 82);
        if (!UsDailyWorker.applyFinancialScreen(context, state, current, SECOND, PROVIDER, hash, () -> false,
                (app, id, title, detail) -> { throw new AssertionError("Updated text reposted the same alert"); })
                || UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Could not reconcile the posted alert");
        }
        var posted = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis())
                .stream().filter(row -> row.detail().contains("METER · 100株 · かなり割安 · 81点"))
                .findFirst().orElseThrow(() -> new AssertionError("Original receipt missing"));
        var outcomeFile = new android.util.AtomicFile(new java.io.File(context.getNoBackupFilesDir(),
                "us-alert-outcomes-v1.json"));
        var outcomes = new JSONObject(new String(outcomeFile.readFully(), java.nio.charset.StandardCharsets.UTF_8));
        if (!outcomes.has(posted.receipt() + ":METER")) {
            throw new AssertionError("Recovered delivery is missing from alert outcomes");
        }
        expectQuiet(notifications);
    }

    private static void verifyDeliveryRecoveryOnNextSession(Context context, NotificationManager notifications)
            throws Exception {
        var state = context.getSharedPreferences("us-next-session-delivery-probe", Context.MODE_PRIVATE);
        String hash = "e".repeat(64);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare next-session recovery");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 15), FIRST, PROVIDER, hash, () -> false);
        var current = meterLedger(SECOND, hash, 9);
        current.getJSONObject("reference_screen").getJSONObject("meter_rows").getJSONArray("NYSE:12345:METER").put(0, 80);
        var history = NotificationHistory.file(context);
        var blocker = new java.io.File(history.getParentFile(), history.getName() + ".tmp");
        if (!blocker.mkdir()) throw new AssertionError("Cannot simulate history write failure");
        try {
            if (UsDailyWorker.applyFinancialScreen(context, state, current, SECOND, PROVIDER, hash, () -> false)
                    || !UsDailyWorker.hasPendingFinancialAlert(state)) {
                throw new AssertionError("History write failure was acknowledged prematurely");
            }
            verifySilentNotice(notifications, SECOND, "米国株 · かなり割安 · 割安度の新規・昇格 1銘柄", "METER · 100株 · かなり割安 · 80点");
        } finally {
            notifications.cancelAll();
            blocker.delete();
        }
        expectQuiet(notifications);
        LocalDate next = SECOND.plusDays(1);
        if (!UsDailyWorker.applyFinancialScreen(context, state, meterLedger(next, hash, 15), next, PROVIDER, hash, () -> false,
                (app, id, title, detail) -> { throw new AssertionError("Next-session recovery posted an old alert again"); })
                || UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Next session did not reconcile the original delivery");
        }
        var original = NotificationHistory.recent(history, System.currentTimeMillis()).stream()
                .filter(row -> row.detail().contains("METER · 100株 · かなり割安 · 80点"))
                .collect(java.util.stream.Collectors.toList());
        if (original.size() != 1) throw new AssertionError("The original notification history was not restored exactly once");
        var file = new android.util.AtomicFile(new java.io.File(context.getNoBackupFilesDir(), "us-alert-outcomes-v1.json"));
        var outcomes = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
        if (!outcomes.has(original.get(0).receipt() + ":METER")) {
            throw new AssertionError("The next session lost the original alert outcome");
        }
        expectQuiet(notifications);
    }

    private static void verifyBothOutcomeStoresFail(Context context, NotificationManager notifications)
            throws Exception {
        var state = context.getSharedPreferences("us-outcome-storage-probe", Context.MODE_PRIVATE);
        String hash = "f".repeat(64);
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare outcome storage recovery probe");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 15), FIRST, PROVIDER, hash, () -> false);
        var current = meterLedger(SECOND, hash, 9);
        current.getJSONObject("reference_screen").getJSONObject("meter_rows").getJSONArray("NYSE:12345:METER").put(0, 83);
        String retryName = "us-deferred-alert-outcomes";
        var retry = context.getSharedPreferences(retryName, Context.MODE_PRIVATE);
        var ledger = new File(context.getNoBackupFilesDir(), "us-alert-outcomes-v1.json").toPath();
        var xml = context.getDataDir().toPath().resolve("shared_prefs").resolve(retryName + ".xml");
        var backup = java.nio.file.Files.createTempDirectory(context.getCacheDir().toPath(), "blocked-outcomes");
        var blocked = new java.util.ArrayList<java.nio.file.Path>();
        String detail = "METER · 100株 · かなり割安 · 83点";
        try {
            // The SDK 28 ledger uses .bak and later SDKs use .new; preferences also use .bak.
            for (var path : java.util.List.of(ledger, ledger.resolveSibling(ledger.getFileName() + ".bak"),
                    ledger.resolveSibling(ledger.getFileName() + ".new"), xml,
                    xml.resolveSibling(xml.getFileName() + ".bak"))) {
                if (java.nio.file.Files.exists(path)) java.nio.file.Files.move(path, backup.resolve(path.getFileName()));
                blocked.add(path);
                java.nio.file.Files.createDirectories(path);
                java.nio.file.Files.createFile(path.resolve("blocker"));
            }
            if (UsDailyWorker.applyFinancialScreen(context, state, current, SECOND, PROVIDER, hash, () -> false)
                    || !UsDailyWorker.hasPendingFinancialAlert(state)) {
                throw new AssertionError("Posted alert was acknowledged even though both outcome stores failed");
            }
            verifySilentNotice(notifications, SECOND, "米国株 · かなり割安 · 割安度の新規・昇格 1銘柄", detail);
            notifications.cancelAll();
            if (UsDailyWorker.applyFinancialScreen(context, state, current, SECOND, PROVIDER, hash, () -> false,
                    (app, id, title, message) -> { throw new AssertionError("Failed storage repeated the alert"); })
                    || !UsDailyWorker.hasPendingFinancialAlert(state)) {
                throw new AssertionError("The second storage failure lost the submitted alert");
            }
        } finally {
            for (var path : blocked) {
                java.nio.file.Files.deleteIfExists(path.resolve("blocker"));
                java.nio.file.Files.deleteIfExists(path);
                var original = backup.resolve(path.getFileName());
                if (java.nio.file.Files.exists(original)) java.nio.file.Files.move(original, path);
            }
            java.nio.file.Files.delete(backup);
            notifications.cancelAll();
        }
        var next = SECOND.plusDays(1);
        if (!UsDailyWorker.applyFinancialScreen(context, state, meterLedger(next, hash, 15), next, PROVIDER, hash, () -> false,
                (app, id, title, message) -> { throw new AssertionError("Recovery reposted the old alert"); })
                || UsDailyWorker.hasPendingFinancialAlert(state)) {
            throw new AssertionError("Both outcome stores recovered but the delivered alert stayed queued");
        }
        long now = System.currentTimeMillis();
        var file = new AtomicFile(ledger.toFile());
        AlertOutcomes.recoverDeferred(file, retry, AlertOutcomes.Market.US, now);
        var original = NotificationHistory.recent(NotificationHistory.file(context), now).stream()
                .filter(row -> row.detail().contains(detail)).findFirst().orElseThrow();
        var outcomes = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
        if (outcomes.getJSONObject(original.receipt() + ":METER").getLong("at") != original.postedAt()) {
            throw new AssertionError("Restored outcome lost its original posting time");
        }
        expectQuiet(notifications);
    }

    private static void verifyOutcomeRecoveryWithoutQuotes(Context context, NotificationManager notifications,
                                                           WorkerFactory factory) throws Exception {
        var state = ScanWorker.prefs(context);
        String pending = "us_private_sec_pending";
        String signals = "us_private_sec_pending_signals";
        String sent = "us_private_sec_sent";
        if (UsDailyWorker.hasPendingFinancialAlert(state)) throw new AssertionError("Expected an empty US alert queue");
        var previousSent = state.getStringSet(sent, java.util.Set.of());
        String title = "終値なしで復元する試験通知";
        String detail = "投稿済みの成績 NOQUOTE";
        var parent = File.createTempFile("blocked-outcome-no-quotes", ".test", context.getCacheDir());
        var blocked = new AtomicFile(new File(parent, "outcomes.json"));
        var retry = context.getSharedPreferences("us-deferred-alert-outcomes", Context.MODE_PRIVATE);
        var market = AlertOutcomes.Market.US;
        try {
            if (!state.edit().putString(pending, title + "\n" + detail)
                    .putString(signals, new JSONObject().put("NOQUOTE", "参考候補").toString()).commit()
                    || !ScanWorker.postNotification(context, 6, title, detail)) {
                throw new AssertionError("Cannot prepare a submitted alert without a closing-price snapshot");
            }
            notifications.cancelAll();
            long now = System.currentTimeMillis();
            var submitted = AlertOutcomes.deliveredEntry(context, 6, title, detail, now);
            if (submitted == null) throw new AssertionError("No submission receipt for the test alert");
            var deferred = new NotificationHistory.Entry("deferred-no-quotes", now, "title", "detail");
            AlertOutcomes.recordOrDefer(blocked, retry, market, deferred, java.util.Map.of("DEFERRED", "割安"), now);

            verifyResult(context, factory, ListenableWorker.Result.success());
            if (UsDailyWorker.hasPendingFinancialAlert(state) || retry.contains("rows")) {
                throw new AssertionError("Prior submissions or deferred outcomes stayed queued without market data");
            }
            var file = new AtomicFile(new File(context.getNoBackupFilesDir(), "us-alert-outcomes-v1.json"));
            var ledger = new JSONObject(new String(file.readFully(), java.nio.charset.StandardCharsets.UTF_8));
            if (ledger.getJSONObject(submitted.receipt() + ":NOQUOTE").getLong("at") != submitted.postedAt()
                    || ledger.getJSONObject("deferred-no-quotes:DEFERRED").getLong("at") != now) {
                throw new AssertionError("No-quote recovery lost the original posting times");
            }
            expectQuiet(notifications);
        } finally {
            state.edit().remove(pending).remove(signals).putStringSet(sent, previousSent).commit();
            blocked.delete();
            parent.delete();
            notifications.cancelAll();
        }
    }

    private static void verifyOutdatedNotificationIgnored(Context context, NotificationManager notifications) throws Exception {
        var state = context.getSharedPreferences("us-stale-alert-probe", Context.MODE_PRIVATE);
        String hash = "a".repeat(64);
        String old = "古いテスト通知\n" + FIRST + "の終値（参考）\n過去の条件";
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare stale alert settings");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 15), FIRST, PROVIDER, hash, () -> false);
        if (!state.edit().putString("us_private_sec_pending", old).commit()) {
            throw new AssertionError("Cannot save old delivery fixture");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(SECOND, hash, 15), SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        if (UsDailyWorker.hasPendingFinancialAlert(state)) throw new AssertionError("Old trading day stayed queued");
        ScanWorker.setNotificationsRequested(state, false);
        ScanWorker.setNotificationsRequested(state, true);
        String muted = "オフにする前の通知\n" + SECOND + "の終値（参考）\n過去の条件";
        if (!state.edit().putString("us_private_sec_pending", muted).commit()) {
            throw new AssertionError("Cannot save old settings fixture");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(SECOND, hash, 15), SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        if (UsDailyWorker.hasPendingFinancialAlert(state)) throw new AssertionError("Muted alert stayed queued");
    }

    private static JSONObject meterLedger(LocalDate day, String hash, int close) throws Exception {
        return meterLedger(day, hash, close, false);
    }

    private static JSONObject meterLedger(LocalDate day, String hash, int close, boolean revisedEarnings) throws Exception {
        var financials = new JSONArray();
        var prices = new java.util.HashMap<String, java.math.BigDecimal>();
        boolean current = SECOND.equals(day);
        for (var ticker : java.util.List.of("METER", "NEWCIK", "NEWVENUE")) {
            int cik = ticker.equals("NEWCIK") && current ? 54321 : 12345;
            String exchange = ticker.equals("NEWVENUE") && current ? "Nasdaq" : "NYSE";
            var target = new JSONObject().put("symbol", ticker).put("exchange", exchange).put("cik", cik);
            var payload = new JSONObject(facts().replace("12345", Integer.toString(cik)));
            var gaap = payload.getJSONObject("facts").getJSONObject("us-gaap");
            if (revisedEarnings) gaap.getJSONObject("NetIncomeLoss").getJSONObject("units")
                    .getJSONArray("USD").getJSONObject(0).put("val", 10);
            gaap.put("EarningsPerShareBasic", new JSONObject().put("units", new JSONObject()
                    .put("USD/shares", meterAnnualFacts(cik, 0.9, 0.8))));
            gaap.put("NetCashProvidedByUsedInOperatingActivities", new JSONObject().put("units", new JSONObject()
                    .put("USD", meterAnnualFacts(cik, 100, 80))));
            var row = UsDeviceFinancials.financialRow(target, payload, day);
            if (row == null) throw new AssertionError("SEC fixture did not qualify for financial screening: " + ticker);
            financials.put(row);
            prices.put(ticker, java.math.BigDecimal.valueOf(close));
        }
        // Exercise the same persisted composite keys as the SEC finance worker.
        var ledger = UsDeviceFinancials.screen(day, PROVIDER, hash, financials, prices,
                new UsScreen.Fx(day, 65), java.util.Map.of());
        var scores = ledger.getJSONObject("reference_screen").getJSONObject("meter_rows");
        if (!scores.has("NYSE:12345:METER") || scores.length() != 3) {
            throw new AssertionError("Production screening did not produce the expected meter identities");
        }
        return ledger;
    }

    private static JSONArray meterAnnualFacts(int cik, double latest, double previous) throws Exception {
        var facts = new JSONArray();
        for (int year = 2026; year >= 2025; year--) {
            facts.put(new JSONObject().put("start", (year - 1) + "-10-01").put("end", year + "-09-30")
                    .put("val", year == 2026 ? latest : previous).put("filed", "2026-10-20").put("form", "10-K")
                    .put("accn", String.format(java.util.Locale.ROOT, "%010d-26-000001", cik)));
        }
        return facts;
    }

    private static void verifyStaleBudgetClears(Context context) throws Exception {
        var folder = new File(context.getNoBackupFilesDir(), "budget-clear-probe");
        if (!folder.isDirectory() && !folder.mkdirs()) throw new IOException("Cannot create budget probe directory");
        var isolated = new android.content.ContextWrapper(context) {
            @Override public File getNoBackupFilesDir() { return folder; }

            @Override public android.content.SharedPreferences getSharedPreferences(String name, int mode) {
                return super.getSharedPreferences("budget-clear-probe-" + name, mode);
            }
        };
        var quote = new AtomicFile(new File(folder, "us-daily-closes.json"));
        var day = UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(java.time.Instant.now()));
        var state = ScanWorker.prefs(isolated);
        var edit = state.edit().clear();
        MarketCoverage.US.save(edit, MarketCoverage.build(day, day, java.util.Set.of(), java.util.Set.of(),
                java.util.Set.of(), java.util.Map.of()));
        var old = new JSONObject().put("day", day.toString()).put("eligible", 1)
                .put("results", new JSONObject().put("TEST", "WITHIN"));
        if (!edit.putString("us_single_session_budget", old.toString()).commit()) {
            throw new AssertionError("Cannot save stale budget fixture");
        }
        try {
            writeClose(quote, day, 20, false);
            if (!UsSingleSessionBudgetCheck.hasPublishedResult(state, day)) {
                throw new AssertionError("Listing refresh would skip the previously published budget count");
            }
            UsSingleSessionBudgetCheck.run(isolated, day, () -> false,
                    url -> { throw new AssertionError("Empty budget refresh should not download data"); });
            if (UsSingleSessionBudgetCheck.hasPublishedResult(state, day)
                    || !UsSingleSessionBudgetCheck.display(state, day.toString(), PROVIDER).isEmpty()) {
                throw new AssertionError("A budget count survived removal of all eligible symbols");
            }
        } finally {
            quote.delete();
            state.edit().clear().commit();
        }
    }

    private static void verifyFreshness(Context context, AtomicFile checkpoint) throws Exception {
        var state = ScanWorker.prefs(context);
        var market = MarketFreshness.US_FINANCE;
        if (!SECOND.equals(market.day(state)) || market.phase(state) != null) {
            throw new AssertionError("US did not display the completed trading day");
        }
        var next = SECOND.plusDays(1);
        var scan = new JSONObject(new String(checkpoint.readFully(), java.nio.charset.StandardCharsets.UTF_8));
        var ledger = new JSONObject(scan.getJSONObject("ledger").toString()).put("trading_date_et", next.toString());
        var screen = ledger.getJSONObject("reference_screen").put("fx_date", next.toString());
        var rows = screen.getJSONArray("observations");
        String hash = ledger.getString("close_sha256");
        screen.put("observations", new JSONArray());
        UsDailyWorker.applyFinancialScreen(context, state, ledger, next, PROVIDER, hash, () -> false);
        if (!SECOND.equals(market.day(state)) || market.phase(state) != MarketFreshness.Phase.FINANCE
                || !UsDailyWorker.displayStatus(state).contains(SECOND + " の取引分 · 判定済み")) {
            throw new AssertionError("An incomplete US screen replaced the previous result");
        }
        var test = new JSONObject();
        var recovered = new JSONObject();
        for (int index = 0; index < rows.length(); index++) {
            var row = rows.getJSONObject(index);
            if ("TEST".equals(row.getString("symbol"))) test = row;
            if ("AAA".equals(row.getString("symbol"))) recovered = row;
        }
        var scope = java.util.Set.of("TEST", "AAA");
        var marketCoverage = MarketCoverage.US;
        screen.put("observations", new JSONArray(java.util.List.of(test)));
        UsDailyWorker.applyFinancialScreen(context, state, ledger, next, PROVIDER, hash, () -> false);
        marketCoverage.track(state, state.edit(), MarketCoverage.build(next, next, scope, scope,
                java.util.Set.of("TEST"), java.util.Map.of()), true).commit();

        recovered.put("status", "priority").put("quantity", 100);
        screen.put("observations", new JSONArray(java.util.List.of(test, recovered)));
        UsDailyWorker.applyFinancialScreen(context, state, ledger, next, PROVIDER, hash, () -> false);
        marketCoverage.track(state, state.edit(), MarketCoverage.build(next, next, scope, scope, scope,
                java.util.Map.of()), true).commit();
        if (!next.equals(market.day(state)) || market.phase(state) != null
                || !marketCoverage.summary(state).contains("同日初回の判定比 +1銘柄")) {
            throw new AssertionError("US same-day repair did not advance the verified result");
        }

        var manager = context.getSystemService(NotificationManager.class);
        verifySilentNotice(manager, "AAA", next);
        manager.cancelAll();
        UsDailyWorker.applyFinancialScreen(context, state, ledger, next, PROVIDER, hash, () -> false);
        expectQuiet(manager);

        // Keep the worker-produced coverage snapshot for the independent coverage UI probe.
        var original = UsSecFinanceWorker.coverage(scan, java.util.Set.of("TEST", "AAA"), java.util.Set.of());
        marketCoverage.save(state.edit(), original).commit();

    }

    private static void verifyResult(Context context, WorkerFactory factory, ListenableWorker.Result expected) {
        var worker = TestWorkerBuilder.from(context, UsSecFinanceWorker.class, new SynchronousExecutor())
                .setWorkerFactory(factory).build();
        if (!expected.equals(worker.doWork())) throw new AssertionError("Unexpected SEC worker result");
    }

    private static void writeClose(AtomicFile close, LocalDate day, int price, boolean extra) throws Exception {
        var prices = new JSONObject().put("trading_date_et", day.toString()).put("source", PROVIDER)
                .put("adjusted", JSONObject.NULL).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "TEST").put("close_usd", price)));
        if (extra) prices.getJSONArray("closes").put(new JSONObject().put("symbol", "AAA").put("close_usd", 30));
        UsDailyWorker.writeSnapshot(close, prices);
    }

    static String payload(String url, AtomicInteger factRequests, AtomicInteger indexRequests)
            throws IOException {
        if (url.equals(UsSecFilingIndex.address(FIRST)) || url.equals(UsSecFilingIndex.address(SECOND))) {
            indexRequests.incrementAndGet();
            int day = url.equals(UsSecFilingIndex.address(FIRST)) ? 16 : 17;
            return "Last Data Received:    Nov " + day + ", 2026\n"
                    + "CIK|Company Name|Form Type|Date Filed|File Name\n"
                    + "------\n67890|Other Corp|10-Q|202611" + day + "|edgar/data/67890/0000067890-26-000001.txt";
        }
        if (url.endsWith("/otherlisted.txt")) return "ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
                + "TEST|Test Corp Common Stock|N|N|N\nFile Creation Time: 1118202612:00||||";
        if (url.endsWith("/nasdaqlisted.txt")) return "Symbol|Security Name|NextShares|ETF|Test Issue\n"
                + "OTHER|Other Corp Common Stock|N|N|N\nFile Creation Time: 1118202612:00||||";
        if (url.equals(UsDeviceFinancials.SEC_DIRECTORY)) {
            return "{\"fields\":[\"cik\",\"name\",\"ticker\",\"exchange\"],"
                    + "\"data\":[[12345,\"Test Corp\",\"TEST\",\"NYSE\"]]}";
        }
        if (url.endsWith("/CIK0000012345.json")) {
            if (factRequests.incrementAndGet() == 1) throw new IOException("Simulated connection loss");
            return facts();
        }
        if (url.contains("frankfurter.dev")) {
            return """
                    [{"date":"2026-11-16","base":"USD","quote":"JPY","rate":150},
                     {"date":"2026-11-17","base":"USD","quote":"JPY","rate":150}]
                    """;
        }
        if (url.contains("DOLT_HASHOF")) {
            return "{\"query_execution_status\":\"Success\",\"rows\":[{\"revision\":\"" + "a".repeat(32) + "\"}]}";
        }
        if (url.contains("FROM+split")) return "{\"query_execution_status\":\"Success\",\"rows\":[]}";
        throw new AssertionError("Unexpected source " + url);
    }

    static String facts() {
        return """
                    {"cik":12345,"facts":{
                     "us-gaap":{"StockholdersEquity":{"units":{"USD":[
                      {"end":"2026-09-30","filed":"2026-10-20","accn":"0000012345-26-000001","form":"10-K","val":1500}]}},
                      "NetIncomeLoss":{"units":{"USD":[
                      {"start":"2025-10-01","end":"2026-09-30","filed":"2026-10-20","accn":"0000012345-26-000001","form":"10-K","val":90}]}}},
                     "dei":{"EntityCommonStockSharesOutstanding":{"units":{"shares":[
                      {"end":"2026-10-13","filed":"2026-10-20","accn":"0000012345-26-000001","form":"10-K","val":100}]}}}}}
                    """;
    }

    static void expectQuiet(NotificationManager manager) throws InterruptedException {
        Thread.sleep(300);
        if (manager.getActiveNotifications().length != 0) {
            throw new AssertionError("US watch posted a baseline, incomplete, or duplicate notification");
        }
    }

    private static void verifySilentNotice(NotificationManager manager) throws InterruptedException {
        verifySilentNotice(manager, "TEST", SECOND);
    }

    static void verifySilentNotice(NotificationManager manager, String ticker, LocalDate day)
            throws InterruptedException {
        verifySilentNotice(manager, day, "米国株の参考条件入り 1銘柄", ticker + " · 100株 · 優先候補");
    }

    private static void verifySilentNotice(NotificationManager manager, LocalDate day, String expectedTitle,
                                           String expectedDetail)
            throws InterruptedException {
        var channel = manager.getNotificationChannel(ScanWorker.CHANNEL);
        if (channel == null || channel.getImportance() != NotificationManager.IMPORTANCE_LOW
                || channel.getSound() != null || channel.shouldVibrate()) {
            throw new AssertionError("US reference notification channel is not silent");
        }
        for (int attempt = 0; attempt < 30; attempt++) {
            for (var active : manager.getActiveNotifications()) {
                var note = active.getNotification();
                String title = note.extras.getCharSequence(Notification.EXTRA_TITLE, "").toString();
                String detail = note.extras.getCharSequence(Notification.EXTRA_BIG_TEXT, "").toString();
                if (title.equals(expectedTitle) && detail.contains(expectedDetail)
                        && detail.contains(day.toString()) && ScanWorker.CHANNEL.equals(note.getChannelId())) {
                    return;
                }
            }
            Thread.sleep(100);
        }
        throw new AssertionError("Android did not receive the US reference notification: " + expectedDetail);
    }
}
