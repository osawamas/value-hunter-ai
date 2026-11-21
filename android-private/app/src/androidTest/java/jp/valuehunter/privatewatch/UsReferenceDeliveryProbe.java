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
                verifyOutdatedNotificationIgnored(context, notifications);
                verifyStaleBudgetClears(context);
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
        var before = meterLedger(FIRST, hash, 50);
        var after = meterLedger(SECOND, hash, 78);
        UsDailyWorker.applyFinancialScreen(context, state, before, FIRST, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false);
        verifySilentNotice(notifications, SECOND, "米国株 · かなり割安 · 割安度の新規・昇格 1銘柄",
                "METER · 100株 · かなり割安 · 78点");
        var receipts = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis());
        if (receipts.stream().noneMatch(row -> row.title().contains("かなり割安")
                && row.detail().contains("METER · 100株 · かなり割安 · 78点"))) {
            throw new AssertionError("US notification did not use the saved meter band");
        }
        notifications.cancelAll();
        UsDailyWorker.applyFinancialScreen(context, state, after, SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
    }

    private static void verifyOutdatedNotificationIgnored(Context context, NotificationManager notifications) throws Exception {
        var state = context.getSharedPreferences("us-stale-alert-probe", Context.MODE_PRIVATE);
        String hash = "a".repeat(64);
        String old = "古いテスト通知\n" + FIRST + "の終値（参考）\n過去の条件";
        if (!state.edit().clear().putBoolean(ValueAlertPreview.LIVE, true).commit()) {
            throw new AssertionError("Cannot prepare stale alert settings");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(FIRST, hash, 50), FIRST, PROVIDER, hash, () -> false);
        if (!state.edit().putString("us_private_sec_pending", old).commit()) {
            throw new AssertionError("Cannot save old delivery fixture");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(SECOND, hash, 50), SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        if (UsDailyWorker.hasPendingFinancialAlert(state)) throw new AssertionError("Old trading day stayed queued");
        ScanWorker.setNotificationsRequested(state, false);
        ScanWorker.setNotificationsRequested(state, true);
        String muted = "オフにする前の通知\n" + SECOND + "の終値（参考）\n過去の条件";
        if (!state.edit().putString("us_private_sec_pending", muted).commit()) {
            throw new AssertionError("Cannot save old settings fixture");
        }
        UsDailyWorker.applyFinancialScreen(context, state, meterLedger(SECOND, hash, 50), SECOND, PROVIDER, hash, () -> false);
        expectQuiet(notifications);
        if (UsDailyWorker.hasPendingFinancialAlert(state)) throw new AssertionError("Muted alert stayed queued");
    }

    private static JSONObject meterLedger(LocalDate day, String hash, int score) throws Exception {
        var observations = new JSONArray().put(new JSONObject().put("symbol", "METER").put("cik", 12345)
                .put("exchange", "NYSE").put("status", "priority").put("quantity", 100));
        var scores = new JSONObject().put("METER", ValueAlertPreview.encode(new ValueAlertMeter.Score(score, 2, 4), 100));
        var reference = new JSONObject().put("provider", PROVIDER).put("close_sha256", hash)
                .put("fx_date", day.toString()).put("observations", observations).put("meter_rows", scores);
        var coverage = new JSONObject();
        for (var exchange : java.util.List.of("NYSE", "Nasdaq")) {
            coverage.put(exchange, new JSONObject().put("with_close_and_reference_financials", 1));
        }
        return new JSONObject().put("trading_date_et", day.toString()).put("close_provider", PROVIDER)
                .put("close_sha256", hash).put("coverage", coverage).put("reference_screen", reference);
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
        throw new AssertionError("Android did not receive the US reference notification");
    }
}
