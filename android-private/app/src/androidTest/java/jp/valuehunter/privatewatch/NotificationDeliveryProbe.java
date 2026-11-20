package jp.valuehunter.privatewatch;

import android.app.Instrumentation;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Intent;
import android.os.ParcelFileDescriptor;
import android.os.PowerManager;
import android.os.SystemClock;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Switch;
import android.widget.Button;
import android.widget.TextView;

import java.io.IOException;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLStreamHandler;
import java.util.function.BooleanSupplier;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import javax.net.ssl.HttpsURLConnection;

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
            require(!MarketNetwork.allowed(), "Market communication was re-enabled by reboot");
            requireBlocked();
            require(MarketNetwork.setAllowed(context, true), "Cannot restore communication for the alert replay");
            require(!ScanWorker.notificationsRequested(context)
                    && prefs.getBoolean(NotificationScreenWake.ENABLED, false),
                    "The two switch settings did not survive reboot");
            var saved = NotificationHistory.recent(history, System.currentTimeMillis());
            require(saved.size() == 2, "Both notifications should survive reboot");
            require(saved.stream().anyMatch(row -> row.title().equals(JP_TITLE) && row.detail().equals(JP_DETAIL))
                    && saved.stream().anyMatch(row -> row.title().equals(US_TITLE) && row.detail().equals(US_DETAIL)),
                    "History did not retain market, issuer and reason");
            require(saved.get(0).postedAt() > saved.get(1).postedAt(), "Newest notification must appear first");
            require(prefs.edit().putBoolean(ScanWorker.NOTIFICATIONS_ENABLED, true).commit(),
                    "Cannot re-enable notifications");
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

        require(ScanWorker.testNotification(context), "Diagnostic notification did not submit");
        require(await(() -> active(manager, ScanWorker.TEST_NOTIFICATION_ID) != null),
                "Diagnostic notification did not reach Android");
        require(!power.isInteractive() && NotificationHistory.recent(history, System.currentTimeMillis()).size() == 2,
                "Diagnostic notification ignored disabled wake or changed real history");
        manager.cancel(ScanWorker.TEST_NOTIFICATION_ID);

        var disconnected = new CountDownLatch(1);
        var connection = MarketNetwork.open(openUntilStopped(disconnected));
        var input = MarketNetwork.input(connection);
        exerciseSettings(instrumentation, power);
        require(disconnected.await(5, TimeUnit.SECONDS), "OFF did not disconnect an open market connection");
        try (input) {
            try {
                input.read();
                throw new AssertionError("An open market stream was readable after OFF");
            } catch (IOException stopped) {
                require(!MarketNetwork.allowed(), "Stream should fail after explicit OFF");
            }
        }
        sleep(instrumentation, power);
        require(!ScanWorker.postNotification(context, 53, "抑止テスト", "1299")
                && !ScanWorker.testNotification(context), "Disabled notifications still accepted submission");
        SystemClock.sleep(350);
        require(active(manager, 53) == null && !power.isInteractive(),
                "Notifications off should block posts and screen wake even with wake preference on");
        require(NotificationHistory.recent(history, System.currentTimeMillis()).size() == 2,
                "A suppressed notification changed history");
        return "ALERT_SILENT_WAKE_AND_HISTORY_OK";
    }

    private static void exerciseSettings(Instrumentation instrumentation, PowerManager power) throws IOException {
        var context = instrumentation.getTargetContext();
        // Leave market monitoring paused while driving the notification controls.
        require(ScanWorker.prefs(context).edit().putBoolean("public_jpx_watch_paused", true).commit(),
                "Cannot pause JPX in UI probe");
        shell(instrumentation, "input keyevent KEYCODE_WAKEUP");
        shell(instrumentation, "wm dismiss-keyguard");
        require(await(power::isInteractive), "Screen could not turn on to inspect settings");
        var activity = instrumentation.startActivitySync(new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        try {
            instrumentation.runOnMainSync(() -> {
                var root = activity.getWindow().getDecorView();
                var alerts = control(root, "無音通知", Switch.class);
                var wake = control(root, "通知時に画面を点灯", Switch.class);
                var network = control(root, "相場データの通信", Switch.class);
                require(network != null && network.isChecked(), "Market communication switch did not start enabled");
                require(alerts != null && wake != null, "Notification switches could not be found");
                require(alerts.isChecked() && !wake.isChecked(), "Switches did not show the saved state");
                alerts.performClick();
                require(!alerts.isChecked() && !wake.isChecked()
                        && !ScanWorker.notificationsRequested(context), "Alerts OFF changed the wake preference");
                wake.performClick();
                require(wake.isChecked() && !alerts.isChecked()
                        && ScanWorker.prefs(context).getBoolean(NotificationScreenWake.ENABLED, false),
                        "Wake ON incorrectly enabled notifications");
                alerts.performClick();
                require(alerts.isChecked() && wake.isChecked(), "Alerts ON did not retain the wake preference");
                alerts.performClick();
                require(!alerts.isChecked() && wake.isChecked(), "Could not retain wake with notifications off");

                network.performClick();
                require(!network.isChecked() && !MarketNetwork.allowed(), "Communication OFF did not apply");
                require(!control(root, "今すぐ更新", Button.class).isEnabled()
                        && !control(root, "終値と判定の詳細", Button.class).isEnabled(),
                        "Manual network actions are available with communication off");
                require(control(root, "通知履歴（7日間）", Button.class).isEnabled(), "Offline history is unavailable");
                require(!alerts.isChecked() && wake.isChecked(), "Communication toggle affected notification options");
                network.performClick();
                require(network.isChecked() && MarketNetwork.allowed()
                        && control(root, "終値と判定の詳細", Button.class).isEnabled(),
                        "Turning communication on did not restore manual updates");
                network.performClick();
            });
            requireBlocked();
        } finally {
            instrumentation.runOnMainSync(activity::finish);
            instrumentation.waitForIdleSync();
        }
    }

    private static <T extends TextView> T control(View view, String text, Class<T> type) {
        if (type.isInstance(view) && text.contentEquals(type.cast(view).getText())) return type.cast(view);
        if (view instanceof ViewGroup group) {
            for (int i = 0; i < group.getChildCount(); i++) {
                var found = control(group.getChildAt(i), text, type);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static URL openUntilStopped(CountDownLatch disconnected) throws IOException {
        return new URL(null, "https://market.invalid/", new URLStreamHandler() {
            @Override protected URLConnection openConnection(URL address) {
                return new HttpsURLConnection(address) {
                    @Override public void connect() {}
                    @Override public boolean usingProxy() { return false; }
                    @Override public void disconnect() { disconnected.countDown(); }
                    @Override public String getCipherSuite() { return ""; }
                    @Override public java.security.cert.Certificate[] getLocalCertificates() { return null; }
                    @Override public java.security.cert.Certificate[] getServerCertificates() { return null; }
                    @Override public java.io.InputStream getInputStream() {
                        return new java.io.ByteArrayInputStream(new byte[]{1});
                    }
                };
            }
        });
    }

    private static void requireBlocked() throws IOException {
        var destination = new URL(null, "https://market.invalid/", new URLStreamHandler() {
            @Override protected URLConnection openConnection(URL address) {
                throw new AssertionError("Market request reached the transport while off");
            }
        });
        try {
            MarketNetwork.open(destination);
            throw new AssertionError("MarketNetwork.open accepted a request while off");
        } catch (IOException stopped) {
            require(!MarketNetwork.allowed(), "Blocked test should exercise the explicit OFF state");
        }
    }

    private static void sleep(Instrumentation instrumentation, PowerManager power) throws IOException {
        shell(instrumentation, "input keyevent KEYCODE_SLEEP");
        require(await(() -> !power.isInteractive()), "Emulator could not enter screen-off state");
    }

    private static void shell(Instrumentation instrumentation, String command) throws IOException {
        try (var input = new ParcelFileDescriptor.AutoCloseInputStream(
                instrumentation.getUiAutomation().executeShellCommand(command))) {
            while (input.read() >= 0) { /* Wait for the command to finish. */ }
        }
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
