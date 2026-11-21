package jp.valuehunter.privatewatch;

import android.app.NotificationManager;
import android.content.Context;
import android.util.AtomicFile;

import androidx.work.Configuration;
import androidx.work.ListenableWorker;
import androidx.work.WorkManager;
import androidx.work.WorkerFactory;
import androidx.work.WorkerParameters;
import androidx.work.testing.SynchronousExecutor;
import androidx.work.testing.TestWorkerBuilder;
import androidx.work.testing.WorkManagerTestInitHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

final class ArchivedRepairProbe {
    private static final LocalDate BEFORE = LocalDate.of(2026, 11, 16);
    private static final LocalDate DAY = BEFORE.plusDays(1);
    private static final String TICKER = "FIX";
    private static final String EXPECTED_QUOTE_PROGRESS = "終値補完 1銘柄 · 割安判定まで完了 0銘柄";
    private static final String EXPECTED_SCREEN_PROGRESS = "終値補完 1銘柄 · 割安判定まで完了 1銘柄";

    private ArchivedRepairProbe() {}

    static String prepare(Context context) throws Exception {
        initialize(context);
        var state = ScanWorker.prefs(context);
        var clear = state.edit();
        for (String key : state.getAll().keySet()) {
            if (key.startsWith("us_")) clear.remove(key);
        }
        require(clear.commit(), "Could not isolate the archived-repair fixture");
        require(state.edit().putBoolean(ScanWorker.NOTIFICATIONS_ENABLED, true)
                .putBoolean(NotificationScreenWake.ENABLED, false).commit(), "Could not set silent notifications");
        var manager = context.getSystemService(NotificationManager.class);
        manager.cancelAll();
        var dir = context.getNoBackupFilesDir();
        file(context, "us-sec-financials.json").delete();
        file(context, "us-previous-daily-closes.json").delete();
        writeClose(context, BEFORE, true);
        var beforeFacts = new AtomicInteger();
        var stableFacts = new AtomicInteger();
        verifyFinance(context, beforeFacts, stableFacts);
        require(beforeFacts.get() == 1 && stableFacts.get() == 1, "The baseline was not acquired");
        UsReferenceDeliveryProbe.expectQuiet(manager);

        writeClose(context, DAY, false);
        verifyFinance(context, new AtomicInteger(), new AtomicInteger());
        require(MarketCoverage.US.groups(state).getOrDefault(MarketCoverage.Reason.DATED_LISTING, java.util.List.of())
                .contains(TICKER), "The incomplete session did not retain the unpriced ticker");

        archive(dir, BEFORE, "1116202616:08", "Former");
        archive(dir, DAY, "1117202616:08", "Current");
        require(UsListingHistory.verifiedSupplementSymbols(dir, DAY).equals(Set.of(TICKER, "AAA")),
                "The archive pair admitted a different security");

        var requests = new AtomicInteger();
        var success = new AtomicInteger();
        var repair = repairFactory(url -> {
            if (!url.contains("%27FIX%27") || url.contains("%27AAA%27") || url.contains("%27OTHER%27")) {
                throw new AssertionError("The archived recheck contacted the wrong tickers");
            }
            if (requests.incrementAndGet() == 1) throw new IOException("Simulated close-feed disconnect");
            success.incrementAndGet();
            return new JSONObject().put("query_execution_status", "Success").put("rows", new JSONArray()
                    .put(new JSONObject().put("symbol", TICKER).put("trading_date", DAY.toString()).put("close", 5)));
        });
        verifyClose(context, repair, ListenableWorker.Result.retry());
        require(!quotes(context).contains(TICKER), "The failed request changed the quote snapshot");
        verifyClose(context, repair, ListenableWorker.Result.success());
        require(success.get() == 1 && requests.get() == 2 && quotes(context).equals(Set.of("AAA", TICKER)),
                "The successful retry did not preserve the old close and add exactly one");
        require(UsDailyWorker.repairStatus(state, DAY.toString()).contains(EXPECTED_QUOTE_PROGRESS),
                "The market did not expose the persisted quote recovery");
        UsReferenceDeliveryProbe.expectQuiet(manager);
        require(MarketNetwork.setAllowed(context, false), "Could not hold network through fixture reboot");
        return "US_ARCHIVE_REPAIR_BEFORE_REBOOT_OK";
    }

    static String resume(Context context) throws Exception {
        initialize(context);
        var state = ScanWorker.prefs(context);
        require(quotes(context).equals(Set.of("AAA", TICKER))
                && UsDailyWorker.repairStatus(state, DAY.toString()).contains(EXPECTED_QUOTE_PROGRESS),
                "Recovered closes or repair progress disappeared after reboot");
        verifyClose(context, repairFactory(url -> { throw new AssertionError("The saved close was requested again"); }),
                ListenableWorker.Result.success());
        var restoredFacts = new AtomicInteger();
        var reusedFacts = new AtomicInteger();
        verifyFinance(context, restoredFacts, reusedFacts);
        require(restoredFacts.get() == 1 && reusedFacts.get() == 0,
                "Only the newly priced issuer should need financial data");
        require(UsDailyWorker.repairStatus(state, DAY.toString()).contains(EXPECTED_SCREEN_PROGRESS),
                "The recovered issuer did not complete screening");
        var manager = context.getSystemService(NotificationManager.class);
        UsReferenceDeliveryProbe.verifySilentNotice(manager, TICKER, DAY);
        manager.cancelAll();
        verifyFinance(context, restoredFacts, reusedFacts);
        UsReferenceDeliveryProbe.expectQuiet(manager);
        long delivered = NotificationHistory.recent(NotificationHistory.file(context), System.currentTimeMillis())
                .stream().filter(row -> row.detail().contains(TICKER + " · ") && row.detail().contains(DAY.toString())).count();
        require(delivered == 1 && restoredFacts.get() == 1 && reusedFacts.get() == 0,
                "The resumed job repeated a financial download or notification");
        return "US_ARCHIVE_REPAIR_AFTER_REBOOT_OK";
    }

    private static void initialize(Context context) throws Exception {
        WorkManager.getInstance(context).cancelAllWork().getResult().get(10, TimeUnit.SECONDS);
        WorkManagerTestInitHelper.initializeTestWorkManager(context,
                new Configuration.Builder().setExecutor(new SynchronousExecutor()).build());
        require(MarketNetwork.setWifiOnly(context, false) && MarketNetwork.setAllowed(context, true),
                "Could not enable the archive replay");
    }

    private static void archive(File dir, LocalDate day, String time, String issuer) throws Exception {
        var nyse = UsMarketCoverage.directory("ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
                + "FIX|Repair Corp Common Stock|N|N|N\nAAA|Stable Corp Common Stock|N|N|N\n"
                + "File Creation Time: " + time + "||||", false);
        var nasdaq = UsMarketCoverage.directory("Symbol|Security Name|NextShares|ETF|Test Issue\n"
                + "OTHER|" + issuer + " Corp Common Stock|N|N|N\nFile Creation Time: " + time + "||||", true);
        require(UsListingHistory.capture(dir, day, LocalTime.of(17, 0), nyse, nasdaq), "Archive capture failed");
    }

    private static WorkerFactory repairFactory(UsDoltCloses.Download download) {
        return new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context app, String name, WorkerParameters parameters) {
                return new UsDailyWorker(app, parameters, download);
            }
        };
    }

    private static void verifyClose(Context context, WorkerFactory factory, ListenableWorker.Result result) {
        var worker = TestWorkerBuilder.from(context, UsDailyWorker.class, new SynchronousExecutor())
                .setWorkerFactory(factory).setInputData(UsDailyWorker.archiveRecheckData(DAY)).build();
        require(result.equals(worker.doWork()), "Unexpected archived close retry result");
    }

    private static void verifyFinance(Context context, AtomicInteger missing, AtomicInteger stable) {
        var factory = new WorkerFactory() {
            @Override public ListenableWorker createWorker(Context app, String name, WorkerParameters parameters) {
                return new UsSecFinanceWorker(app, parameters, url -> {
                    if (url.endsWith("/CIK0000043210.json")) {
                        stable.incrementAndGet();
                        return UsReferenceDeliveryProbe.facts().replace("12345", "43210");
                    }
                    if (url.endsWith("/CIK0000012345.json")) {
                        missing.incrementAndGet();
                        return UsReferenceDeliveryProbe.facts();
                    }
                    var result = UsReferenceDeliveryProbe.payload(url, new AtomicInteger(), new AtomicInteger());
                    if (url.endsWith("/otherlisted.txt")) {
                        return result.replace("TEST", TICKER).replace("File Creation",
                                "AAA|Stable Corp Common Stock|N|N|N\nFile Creation");
                    }
                    if (UsDeviceFinancials.SEC_DIRECTORY.equals(url)) {
                        return result.replace("\"TEST\",\"NYSE\"]]", "\"FIX\",\"NYSE\"],[43210,\"Stable Corp\",\"AAA\",\"NYSE\"]]");
                    }
                    return result;
                });
            }
        };
        var worker = TestWorkerBuilder.from(context, UsSecFinanceWorker.class, new SynchronousExecutor())
                .setWorkerFactory(factory).build();
        require(ListenableWorker.Result.success().equals(worker.doWork()), "Unexpected financial screening result");
    }

    private static AtomicFile file(Context context, String name) {
        return new AtomicFile(new File(context.getNoBackupFilesDir(), name));
    }

    private static void writeClose(Context context, LocalDate day, boolean full) throws Exception {
        var quotes = new JSONArray().put(new JSONObject().put("symbol", "AAA").put("close_usd", 30));
        if (full) quotes.put(new JSONObject().put("symbol", TICKER).put("close_usd", 20));
        var snapshot = new JSONObject().put("source", UsDoltCloses.SOURCE).put("trading_date_et", day.toString())
                .put("adjusted", JSONObject.NULL).put("closes", quotes);
        UsDailyWorker.writeSnapshot(file(context, "us-daily-closes.json"), snapshot);
    }

    private static Set<String> quotes(Context context) throws Exception {
        byte[] bytes = file(context, "us-daily-closes.json").readFully();
        return UsDeviceFinancials.prices(new JSONObject(new String(bytes, StandardCharsets.UTF_8))
                .getJSONArray("closes")).keySet();
    }

    private static void require(boolean pass, String message) {
        if (!pass) throw new AssertionError(message);
    }
}
