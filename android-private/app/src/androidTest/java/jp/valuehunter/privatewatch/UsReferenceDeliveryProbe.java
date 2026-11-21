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
        } finally {
            notifications.cancelAll();
            close.delete();
            checkpoint.delete();
        }
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

    private static String payload(String url, AtomicInteger factRequests, AtomicInteger indexRequests)
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
            return "[{\"date\":\"2026-11-16\",\"base\":\"USD\",\"quote\":\"JPY\",\"rate\":150}]";
        }
        if (url.contains("DOLT_HASHOF")) {
            return "{\"query_execution_status\":\"Success\",\"rows\":[{\"revision\":\"" + "a".repeat(32) + "\"}]}";
        }
        if (url.contains("FROM+split")) return "{\"query_execution_status\":\"Success\",\"rows\":[]}";
        throw new AssertionError("Unexpected source " + url);
    }

    private static String facts() {
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

    private static void expectQuiet(NotificationManager manager) throws InterruptedException {
        Thread.sleep(300);
        if (manager.getActiveNotifications().length != 0) {
            throw new AssertionError("US watch posted a baseline, incomplete, or duplicate notification");
        }
    }

    private static void verifySilentNotice(NotificationManager manager) throws InterruptedException {
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
                if (title.equals("米国株の参考条件入り 1銘柄") && detail.contains("TEST · 100株 · 優先候補")
                        && detail.contains(SECOND.toString()) && ScanWorker.CHANNEL.equals(note.getChannelId())) {
                    return;
                }
            }
            Thread.sleep(100);
        }
        throw new AssertionError("Android did not receive the US reference notification");
    }
}
