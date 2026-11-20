package jp.valuehunter.privatewatch;

import android.app.Instrumentation;
import android.app.Notification;
import android.app.NotificationManager;
import android.os.ParcelFileDescriptor;
import android.os.PowerManager;
import android.os.SystemClock;

import java.io.IOException;
import java.util.function.BooleanSupplier;

final class NotificationDeliveryProbe {
    private static final int JAPAN = 51;
    private static final int US = 52;
    private static final String JP_TITLE = "東証の割安候補";
    private static final String JP_DETAIL = "2026-11-19の終値\n1301 · PER条件入り";
    private static final String US_TITLE = "米国株の参考条件入り";
    private static final String US_DETAIL = "2026-11-19の終値\nABC · 予算条件入り";

    private NotificationDeliveryProbe() {}

    static String run(Instrumentation instrumentation, String phase) throws Exception {
        var context = instrumentation.getTargetContext();
        var manager = context.getSystemService(NotificationManager.class);
        var power = context.getSystemService(PowerManager.class);
        var history = NotificationHistory.file(context);
        var prefs = ScanWorker.prefs(context);
        if ("restore".equals(phase)) {
            var saved = NotificationHistory.recent(history, System.currentTimeMillis());
            require(saved.size() == 2, "Both notifications should survive reboot");
            require(saved.stream().anyMatch(row -> row.title().equals(JP_TITLE) && row.detail().equals(JP_DETAIL))
                    && saved.stream().anyMatch(row -> row.title().equals(US_TITLE) && row.detail().equals(US_DETAIL)),
                    "History did not retain market, issuer and reason");
            require(saved.get(0).postedAt() > saved.get(1).postedAt(), "Newest notification must appear first");
            require(prefs.edit().putBoolean(NotificationScreenWake.ENABLED, true).commit(), "Cannot re-enable wake");
            sleep(instrumentation, power);
            require(ScanWorker.postNotification(context, JAPAN, JP_TITLE, JP_DETAIL), "Replay was not acknowledged");
            SystemClock.sleep(350);
            require(active(manager, JAPAN) == null && !power.isInteractive(), "Replay posted or woke again after reboot");
            return "ALERT_HISTORY_AFTER_REBOOT_OK";
        }
        if (!"post".equals(phase)) throw new IllegalArgumentException("Unknown alert probe phase");
        manager.cancelAll();
        if (history.exists() && !history.delete()) throw new IOException("Cannot clear alert probe state");
        require(prefs.edit().putBoolean(NotificationScreenWake.ENABLED, true).commit(), "Cannot enable wake");
        sleep(instrumentation, power);
        require(ScanWorker.postNotification(context, JAPAN, JP_TITLE, JP_DETAIL), "JPX notification submission failed");
        require(await(() -> active(manager, JAPAN) != null), "JPX notification did not appear");
        require(await(power::isInteractive), "Screen did not wake for a new JPX notification");
        var posted = active(manager, JAPAN);
        require(posted != null && posted.getGroupAlertBehavior() == Notification.GROUP_ALERT_SUMMARY
                && posted.fullScreenIntent == null, "Notification did not preserve silent group policy");
        var channel = manager.getNotificationChannel(ScanWorker.CHANNEL);
        require(channel.getSound() == null && !channel.shouldVibrate(), "Channel is not silent");

        long originalPostTime = postTime(manager, JAPAN);
        require(history.delete(), "Cannot reproduce interruption before saving history");
        require(ScanWorker.postNotification(context, JAPAN, JP_TITLE, JP_DETAIL), "Active notification recovery failed");
        SystemClock.sleep(350);
        require(postTime(manager, JAPAN) == originalPostTime
                && NotificationHistory.recent(history, System.currentTimeMillis()).get(0).postedAt() == originalPostTime,
                "Recovery should keep the original Android post");

        manager.cancel(JAPAN);
        require(await(() -> active(manager, JAPAN) == null), "JPX notification did not clear");
        require(prefs.edit().putBoolean(NotificationScreenWake.ENABLED, false).commit(), "Cannot disable wake");
        sleep(instrumentation, power);
        require(ScanWorker.postNotification(context, US, US_TITLE, US_DETAIL), "US notification submission failed");
        require(await(() -> active(manager, US) != null), "US notification did not appear with screen wake disabled");
        require(!power.isInteractive(), "Disabled screen wake still lit the screen");
        manager.cancel(US);
        require(NotificationHistory.recent(history, System.currentTimeMillis()).size() == 2,
                "Clearing the notification tray erased history");
        return "ALERT_SILENT_WAKE_AND_HISTORY_OK";
    }

    private static void sleep(Instrumentation instrumentation, PowerManager power) throws IOException {
        try (var input = new ParcelFileDescriptor.AutoCloseInputStream(
                instrumentation.getUiAutomation().executeShellCommand("input keyevent KEYCODE_SLEEP"))) {
            while (input.read() >= 0) { /* Wait for the command to finish. */ }
        }
        require(await(() -> !power.isInteractive()), "Emulator could not enter screen-off state");
    }

    private static Notification active(NotificationManager manager, int id) {
        for (var item : manager.getActiveNotifications()) {
            if (item.getId() == id) return item.getNotification();
        }
        return null;
    }

    private static long postTime(NotificationManager manager, int id) {
        for (var item : manager.getActiveNotifications()) {
            if (item.getId() == id) return item.getPostTime();
        }
        return 0;
    }

    private static boolean await(BooleanSupplier condition) {
        long until = SystemClock.elapsedRealtime() + 3500;
        do {
            if (condition.getAsBoolean()) return true;
            SystemClock.sleep(50);
        } while (SystemClock.elapsedRealtime() < until);
        return false;
    }

    private static void require(boolean success, String message) {
        if (!success) throw new AssertionError(message);
    }
}
