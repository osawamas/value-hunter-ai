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
        var notifications = context.getSystemService(NotificationManager.class);
        var directory = context.getNoBackupFilesDir();
        var close = new AtomicFile(new File(directory, "us-daily-closes.json"));
        var checkpoint = new AtomicFile(new File(directory, "us-sec-financials.json"));
        var factRequests = new AtomicInteger();
        var factory = new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context app, String name, WorkerParameters parameters) {
                if (!name.equals(UsSecFinanceWorker.class.getName())) return null;
                return new UsSecFinanceWorker(app, parameters, url -> payload(url, factRequests));
            }
        };
        notifications.cancelAll();
        try {
            writeClose(close, FIRST, 20);
            verifyResult(context, factory, ListenableWorker.Result.retry());
            expectQuiet(notifications);
            verifyResult(context, factory, ListenableWorker.Result.success());
            expectQuiet(notifications);
            if (factRequests.get() != 2) throw new AssertionError("First day was not retried exactly once");

            writeClose(close, SECOND, 5);
            verifyResult(context, factory, ListenableWorker.Result.success());
            verifySilentNotice(notifications);

            notifications.cancelAll();
            verifyResult(context, factory, ListenableWorker.Result.success());
            expectQuiet(notifications);
            if (factRequests.get() != 3) throw new AssertionError("Completed day downloaded facts again");
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

    private static void writeClose(AtomicFile close, LocalDate day, int price) throws Exception {
        var prices = new JSONObject().put("trading_date_et", day.toString()).put("source", PROVIDER)
                .put("adjusted", JSONObject.NULL).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "TEST").put("close_usd", price)));
        UsDailyWorker.writeSnapshot(close, prices);
    }

    private static String payload(String url, AtomicInteger factRequests) throws IOException {
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
        if (url.contains("frankfurter.dev")) {
            return "[{\"date\":\"2026-11-16\",\"base\":\"USD\",\"quote\":\"JPY\",\"rate\":150}]";
        }
        if (url.contains("DOLT_HASHOF")) {
            return "{\"query_execution_status\":\"Success\",\"rows\":[{\"revision\":\"" + "a".repeat(32) + "\"}]}";
        }
        if (url.contains("FROM+split")) return "{\"query_execution_status\":\"Success\",\"rows\":[]}";
        throw new AssertionError("Unexpected source " + url);
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
