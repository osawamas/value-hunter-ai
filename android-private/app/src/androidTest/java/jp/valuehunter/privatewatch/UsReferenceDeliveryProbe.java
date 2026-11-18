package jp.valuehunter.privatewatch;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.util.AtomicFile;

import androidx.work.testing.SynchronousExecutor;
import androidx.work.testing.TestWorkerBuilder;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.LocalDate;

final class UsReferenceDeliveryProbe {
    private static final LocalDate FIRST = LocalDate.of(2026, 11, 16);
    private static final LocalDate SECOND = FIRST.plusDays(1);
    private static final String PROVIDER = UsDoltCloses.SOURCE;

    private UsReferenceDeliveryProbe() {}

    static void run(Context context) throws Exception {
        var notifications = context.getSystemService(NotificationManager.class);
        var state = ScanWorker.prefs(context);
        var worker = TestWorkerBuilder.from(context, UsDailyWorker.class, new SynchronousExecutor()).build();
        var directory = context.getNoBackupFilesDir();
        var close = new AtomicFile(new File(directory, "us-reference-probe-close.json"));
        var ledger = new File(directory, UsMarketCoverage.ASSET);
        notifications.cancelAll();
        try {
            writeInput(close, ledger, FIRST, "outside_valuation", true);
            worker.updatePrivateScreen(state, close, FIRST, PROVIDER);
            expectQuiet(notifications);
            writeInput(close, ledger, SECOND, "priority", false);
            worker.updatePrivateScreen(state, close, SECOND, PROVIDER);
            expectQuiet(notifications);
            writeInput(close, ledger, SECOND, "priority", true);
            worker.updatePrivateScreen(state, close, SECOND, PROVIDER);
            verifySilentNotice(notifications);
            notifications.cancelAll();
            worker.updatePrivateScreen(state, close, SECOND, PROVIDER);
            expectQuiet(notifications);
        } finally {
            notifications.cancelAll();
            close.delete();
            Files.deleteIfExists(ledger.toPath());
        }
    }

    private static void writeInput(AtomicFile close, File ledger, LocalDate day, String status, boolean matched)
            throws Exception {
        var prices = new JSONObject().put("trading_date_et", day.toString()).put("source", PROVIDER)
                .put("adjusted", JSONObject.NULL).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "TEST").put("close_usd", 5)));
        byte[] closeBytes = prices.toString().getBytes(StandardCharsets.UTF_8);
        Files.write(close.getBaseFile().toPath(), closeBytes);
        String hash = matched ? UsReferenceAlerts.sha256(closeBytes) : "0".repeat(64);
        var row = new JSONObject().put("cik", 12345).put("symbol", "TEST").put("exchange", "NYSE")
                .put("quantity", 100).put("status", status);
        var screen = new JSONObject().put("provider", PROVIDER).put("close_sha256", hash)
                .put("fx_date", day.toString()).put("observations", new JSONArray().put(row));
        var coverage = new JSONObject()
                .put("NYSE", new JSONObject().put("with_close_and_reference_financials", 1))
                .put("Nasdaq", new JSONObject().put("with_close_and_reference_financials", 0));
        var snapshot = new JSONObject().put("trading_date_et", day.toString()).put("close_provider", PROVIDER)
                .put("close_sha256", hash).put("reference_screen", screen).put("coverage", coverage);
        Files.write(ledger.toPath(), snapshot.toString().getBytes(StandardCharsets.UTF_8));
    }

    private static void expectQuiet(NotificationManager manager) throws InterruptedException {
        Thread.sleep(300);
        if (manager.getActiveNotifications().length != 0) {
            throw new AssertionError("US watch posted a baseline, mismatched, or duplicate notification");
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
