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
import android.view.accessibility.AccessibilityNodeInfo;
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
        if ("recovery".equals(phase)) return exerciseMarketRecovery(instrumentation);
        if ("archive_repair_prep".equals(phase)) return ArchivedRepairProbe.prepare(context);
        if ("archive_repair_resume".equals(phase)) return ArchivedRepairProbe.resume(context);
        if ("restore".equals(phase)) {
            require("60,75,90".equals(ScanWorker.prefs(context).getString(ValueAlertPreview.SETTINGS, "")),
                    "Saved alert thresholds did not survive reboot");
            require(DiagnosticLog.read(context).contains("テスト通知をAndroidに投稿"),
                    "Diagnostic events did not survive reboot");
            require(!MarketNetwork.allowed(), "Market communication was re-enabled by reboot");
            require(MarketNetwork.wifiOnly(), "Wi-Fi-only choice did not survive reboot");
            requireBlocked();
            require(MarketNetwork.setWifiOnly(context, false) && MarketNetwork.setAllowed(context, true),
                    "Cannot restore communication for the alert replay");
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
            ListingArchiveProbe.checkAfterReboot(context);
            return "ALERT_HISTORY_AFTER_REBOOT_OK\nUS_LISTING_ARCHIVE_AFTER_REBOOT_OK";
        }
        if (!"post".equals(phase)) throw new IllegalArgumentException("Unknown alert probe phase");
        exerciseCommunicationNotice(instrumentation, power);
        manager.cancelAll();
        if (history.exists() && !history.delete()) throw new IOException("Cannot clear alert probe state");
        require(prefs.edit().putBoolean(NotificationScreenWake.ENABLED, true).commit(), "Cannot enable wake");
        sleep(instrumentation, power);
        require(ScanWorker.postNotification(context, JAPAN, JP_TITLE, JP_DETAIL), "JPX notification submission failed");
        require(await(() -> active(manager, JAPAN) != null), "JPX notification did not appear");
        require(await(power::isInteractive), "Screen did not wake for a new JPX notification");
        require(await(() -> DiagnosticLog.read(context).contains("点灯を観測")),
                "Diagnostic log did not distinguish the wake request from the observation");
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
        exerciseWifiOnly(instrumentation, power);
        ListingArchiveProbe.prepare(context);
        return "ALERT_SILENT_WAKE_AND_HISTORY_OK\nMARKET_WIFI_SWITCH_OK";
    }

    private static String exerciseMarketRecovery(Instrumentation instrumentation) throws Exception {
        var context = instrumentation.getTargetContext();
        var work = androidx.work.WorkManager.getInstance(context);
        work.cancelAllWork().getResult().get(10, TimeUnit.SECONDS);
        androidx.work.testing.WorkManagerTestInitHelper.initializeTestWorkManager(context,
                new androidx.work.Configuration.Builder().setExecutor(new androidx.work.testing.SynchronousExecutor()).build());
        var settings = ScanWorker.prefs(context);
        require(settings.edit().putBoolean(ScanWorker.NOTIFICATIONS_ENABLED, true)
                .putBoolean(NotificationScreenWake.ENABLED, false).commit(), "Cannot set alert recovery controls");
        require(MarketNetwork.setWifiOnly(context, true) && MarketNetwork.setAllowed(context, true),
                "Cannot enable Wi-Fi-only recovery");
        shell(instrumentation, "input keyevent KEYCODE_WAKEUP");
        shell(instrumentation, "wm dismiss-keyguard");
        shell(instrumentation, "svc data enable");
        var activity = instrumentation.startActivitySync(new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        Runnable disconnect = () -> changeWifi(instrumentation, false);
        Runnable reconnect = () -> changeWifi(instrumentation, true);
        try {
            changeWifi(instrumentation, true);
            try {
                JpxWatchDeliveryProbe.verifyWifiRecovery(context, disconnect, reconnect);
            } catch (AssertionError error) {
                throw new AssertionError("JPX Wi-Fi recovery: " + error.getMessage(), error);
            }
            try {
                UsReferenceDeliveryProbe.run(context, disconnect, reconnect);
            } catch (AssertionError error) {
                throw new AssertionError("US Wi-Fi recovery: " + error.getMessage(), error);
            }
            instrumentation.waitForIdleSync();
            instrumentation.runOnMainSync(() -> {
                var button = control(activity.getWindow().getDecorView(), "米国株の未判定の内訳", Button.class);
                require(button != null && button.isEnabled() && button.performClick(), "Cannot open US market coverage");
            });
            require(await(() -> findDialogText(instrumentation, "当日・比較日の上場市場と株式の種類を確認待ち · 1銘柄") != null),
                    "US coverage did not present the missing-close group");
            var group = findDialogText(instrumentation, "当日・比較日の上場市場と株式の種類を確認待ち · 1銘柄");
            require(group != null && group.performAction(AccessibilityNodeInfo.ACTION_CLICK),
                    "Could not open the missing-close group");
            require(await(() -> findDialogText(instrumentation, "OTHER") != null),
                    "The missing-close group did not show its ticker");
            return "MARKET_WIFI_RECOVERY_OK";
        } finally {
            shell(instrumentation, "svc wifi enable");
            shell(instrumentation, "svc data enable");
            instrumentation.runOnMainSync(activity::finish);
            instrumentation.waitForIdleSync();
        }
    }

    private static void changeWifi(Instrumentation instrumentation, boolean connected) {
        try {
            if (connected) {
                shell(instrumentation, "svc wifi enable");
                if (!await(MarketNetwork::allowed, 10_000)) {
                    // Some emulator images prefer their cellular transport after reconnecting.
                    // Force route selection for the fixture, then require the normal Wi-Fi gate to open.
                    shell(instrumentation, "svc data disable");
                }
                require(await(MarketNetwork::allowed, 40_000),
                        "Wi-Fi connection did not enable the market path: "
                                + wifiDiagnostics(instrumentation.getTargetContext()));
            } else {
                shell(instrumentation, "svc data enable");
                shell(instrumentation, "svc wifi disable");
                require(await(MarketNetwork::waitingForWifi, 40_000), "Recovery probe did not lose Wi-Fi");
            }
        } catch (IOException error) {
            throw new AssertionError("Cannot toggle Wi-Fi in the recovery probe", error);
        }
    }

    private static void exerciseWifiOnly(Instrumentation instrumentation, PowerManager power) throws Exception {
        var context = instrumentation.getTargetContext();
        shell(instrumentation, "input keyevent KEYCODE_WAKEUP");
        shell(instrumentation, "wm dismiss-keyguard");
        shell(instrumentation, "svc data enable");
        shell(instrumentation, "svc wifi disable");
        require(await(power::isInteractive), "Screen could not turn on for the Wi-Fi test");
        var activity = instrumentation.startActivitySync(new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        try {
            instrumentation.runOnMainSync(() -> {
                var root = activity.getWindow().getDecorView();
                var wifi = control(root, "Wi-Fi接続時のみ更新", Switch.class);
                var network = control(root, "相場データの通信", Switch.class);
                require(wifi != null && network != null && !network.isChecked(), "Communication options missing");
                wifi.performClick();
                network.performClick();
                require(wifi.isChecked() && network.isChecked() && MarketNetwork.requested()
                        && MarketNetwork.wifiOnly(), "Wi-Fi wait changed the user's ON setting");
            });
            require(await(MarketNetwork::waitingForWifi, 25_000), "App did not wait while Wi-Fi was disabled");
            requireBlocked();

            changeWifi(instrumentation, true);
            var bound = MarketNetwork.open(new URL("https://127.0.0.1:1/"));
            try {
                changeWifi(instrumentation, false);
                requireBlocked();
                try {
                    MarketNetwork.response(bound);
                    throw new AssertionError("Old Wi-Fi connection remained active after Wi-Fi loss");
                } catch (IOException stopped) {
                    require("Market data communication stopped".equals(stopped.getMessage()),
                            "Lost-Wi-Fi request reached the transport");
                }
            } finally {
                MarketNetwork.close(bound);
            }

            changeWifi(instrumentation, true);
            require(!androidx.work.WorkManager.getInstance(context)
                            .getWorkInfosForUniqueWork(UsDailyWorker.ON_WIFI).get(5, TimeUnit.SECONDS).isEmpty(),
                    "Restoring Wi-Fi did not queue the US update");
            instrumentation.runOnMainSync(() -> {
                var network = control(activity.getWindow().getDecorView(), "相場データの通信", Switch.class);
                require(network.isChecked(), "Wi-Fi loss changed the requested communication state");
                network.performClick();
            });
            require(MarketNetwork.wifiOnly() && !MarketNetwork.requested(), "OFF did not keep the Wi-Fi preference");
        } finally {
            shell(instrumentation, "svc wifi enable");
            shell(instrumentation, "svc data enable");
            instrumentation.runOnMainSync(activity::finish);
            instrumentation.waitForIdleSync();
        }
    }

    private static String wifiDiagnostics(android.content.Context context) {
        var manager = context.getSystemService(android.net.ConnectivityManager.class);
        if (manager == null) return "ConnectivityManager unavailable";
        var network = manager.getActiveNetwork();
        if (network == null) return "no active default network";
        var caps = manager.getNetworkCapabilities(network);
        if (caps == null) return "default network has no capabilities";
        return "default transport wifi=" + caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)
                + ", cellular=" + caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR)
                + ", vpn=" + caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN)
                + ", internet=" + caps.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
                + ", requested=" + MarketNetwork.requested()
                + ", wifiOnly=" + MarketNetwork.wifiOnly();
    }

    private static void exerciseCommunicationNotice(Instrumentation instrumentation, PowerManager power)
            throws IOException {
        var context = instrumentation.getTargetContext();
        require(MarketNetwork.noticeRequired(context) && !MarketNetwork.allowed(),
                "Fresh install should require a choice before allowing communication");
        requireBlocked();
        require(ScanWorker.prefs(context).edit().putBoolean("public_jpx_watch_paused", true).commit(),
                "Cannot pause JPX in notice probe");
        shell(instrumentation, "input keyevent KEYCODE_WAKEUP");
        shell(instrumentation, "wm dismiss-keyguard");
        require(await(power::isInteractive), "Screen could not turn on to show the communication notice");

        chooseCommunication(instrumentation, "通信オフで使う");
        require(!MarketNetwork.noticeRequired(context) && !MarketNetwork.allowed(),
                "Offline choice did not acknowledge the warning");
        requireBlocked();

        var oldSettings = context.getSharedPreferences("market-network", android.content.Context.MODE_PRIVATE);
        require(oldSettings.edit().putBoolean(MarketNetwork.ALLOWED, true).remove(MarketNetwork.NOTICE).commit(),
                "Cannot prepare a pre-warning upgrade fixture");
        MarketNetwork.initialize(context);
        require(MarketNetwork.noticeRequired(context) && !MarketNetwork.allowed(),
                "Pre-warning ON preference bypassed the updated notice");
        requireBlocked();

        chooseCommunication(instrumentation, "相場通信をオン");
        require(MarketNetwork.allowed() && !MarketNetwork.noticeRequired(context),
                "Explicit approval did not enable communication");
    }

    private static void chooseCommunication(Instrumentation instrumentation, String choice) {
        var context = instrumentation.getTargetContext();
        var activity = instrumentation.startActivitySync(new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        try {
            require(await(() -> findDialogText(instrumentation, "通信量について") != null),
                    "First-open communication notice was not visible");
            require(await(() -> findDialogText(instrumentation, "従量制のモバイル回線") != null
                    && findDialogText(instrumentation, "データ無制限") != null),
                    "The warning did not describe affected plans and recommended networks");
            var button = findDialogText(instrumentation, choice);
            require(button != null && button.performAction(AccessibilityNodeInfo.ACTION_CLICK),
                    "Could not select " + choice);
            require(await(() -> !MarketNetwork.noticeRequired(context)), "Communication choice was not saved");
        } finally {
            instrumentation.runOnMainSync(activity::finish);
            instrumentation.waitForIdleSync();
        }
    }

    private static AccessibilityNodeInfo findDialogText(Instrumentation instrumentation, String text) {
        var automation = instrumentation.getUiAutomation();
        var root = automation.getRootInActiveWindow();
        if (root != null) {
            var matches = root.findAccessibilityNodeInfosByText(text);
            if (!matches.isEmpty()) return matches.get(0);
        }
        // API 35 may keep the launcher or permission window active briefly after startActivitySync.
        // Search all accessible windows rather than assuming the foreground root is our dialog.
        for (var window : automation.getWindows()) {
            var candidate = window.getRoot();
            if (candidate == null) continue;
            var matches = candidate.findAccessibilityNodeInfosByText(text);
            if (!matches.isEmpty()) return matches.get(0);
        }
        return null;
    }

    private static void exerciseValueMeter(Instrumentation instrumentation, android.app.Activity activity) {
        var state = ScanWorker.prefs(instrumentation.getTargetContext());
        require(state.edit().remove(ValueAlertPreview.SETTINGS).commit(), "Cannot reset the meter fixture");
        openValueMeter(instrumentation, activity);
        require(await(() -> findDialogText(instrumentation, "割安 · 60点以上") != null
                && findDialogText(instrumentation, "かなり割安 · 75点以上") != null
                && findDialogText(instrumentation, "超割安 · 85点以上") != null), "Bad meter defaults");
        var slider = findDialogText(instrumentation, "下限スライダー 超割安 · 85点以上");
        var value = new android.os.Bundle();
        value.putFloat(AccessibilityNodeInfo.ACTION_ARGUMENT_PROGRESS_VALUE, 90);
        require(slider != null && slider.performAction(
                AccessibilityNodeInfo.AccessibilityAction.ACTION_SET_PROGRESS.getId(), value),
                "Cannot change the highest threshold");
        require(await(() -> findDialogText(instrumentation, "超割安 · 90点以上") != null), "Meter did not update");
        var save = findDialogText(instrumentation, "境界を保存");
        require(save != null && save.performAction(AccessibilityNodeInfo.ACTION_CLICK), "Cannot save the threshold");
        require(await(() -> "60,75,90".equals(state.getString(ValueAlertPreview.SETTINGS, ""))),
                "Meter did not persist thresholds");
        openValueMeter(instrumentation, activity);
        require(await(() -> findDialogText(instrumentation, "超割安 · 90点以上") != null), "Saved threshold did not reopen");
        var reset = findDialogText(instrumentation, "初期値に戻す");
        require(reset != null && reset.performAction(AccessibilityNodeInfo.ACTION_CLICK), "Cannot reset the meter");
        require(await(() -> findDialogText(instrumentation, "超割安 · 85点以上") != null), "Reset did not restore defaults");
        var recreation = new android.os.Bundle();
        instrumentation.runOnMainSync(() -> instrumentation.callActivityOnSaveInstanceState(activity, recreation));
        require("60,75,85".equals(recreation.getString("valueMeterDraft")),
                "Uncommitted thresholds were lost from the activity state");
        var cancel = findDialogText(instrumentation, "キャンセル");
        require(cancel != null && cancel.performAction(AccessibilityNodeInfo.ACTION_CLICK), "Cannot close the meter");
        require("60,75,90".equals(state.getString(ValueAlertPreview.SETTINGS, "")),
                "Cancel persisted the reset without saving");
    }

    private static void openValueMeter(Instrumentation instrumentation, android.app.Activity activity) {
        instrumentation.runOnMainSync(() -> {
            var button = control(activity.getWindow().getDecorView(), "割安アラートの境界", Button.class);
            require(button != null && button.performClick(), "Cannot open the threshold meter");
        });
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
            exerciseValueMeter(instrumentation, activity);
            exerciseMeterEntries(context);
            exerciseDiagnosticCopy(instrumentation, activity);
            requireBlocked();
        } finally {
            instrumentation.runOnMainSync(activity::finish);
            instrumentation.waitForIdleSync();
        }
    }

    private static void exerciseMeterEntries(android.content.Context context) {
        var state = context.getSharedPreferences("instrumented-meter", android.content.Context.MODE_PRIVATE);
        var market = ValueAlertPreview.Market.JPX;
        var today = java.time.LocalDate.of(2026, 11, 19);
        var yesterday = today.minusDays(1);
        try {
            var prior = new org.json.JSONObject();
            var current = new org.json.JSONObject();
            for (var code : java.util.List.of("1111", "2222", "3333", "4444")) {
                prior.put(code, ValueAlertPreview.encode(new ValueAlertMeter.Score(50, 3, 6), 100));
            }
            current.put("1111", ValueAlertPreview.encode(new ValueAlertMeter.Score(66, 1, 3), 100));
            current.put("2222", ValueAlertPreview.encode(new ValueAlertMeter.Score(79, 2, 4), 100));
            current.put("3333", ValueAlertPreview.encode(new ValueAlertMeter.Score(88, 3, 6), 1));
            current.put("4444", ValueAlertPreview.encode(new ValueAlertMeter.Score(91, 3, 6), 100));
            current.put("5555", ValueAlertPreview.encode(new ValueAlertMeter.Score(92, 3, 6), 100));
            require(state.edit().clear().commit(), "Cannot reset meter alert test data");
            require(ValueAlertPreview.entries(state, market, today, "JPX", current, java.util.Set.of(),
                    code -> true).isEmpty(), "First session generated a meter alert");
            var edit = state.edit();
            ValueAlertPreview.save(state, edit, market, yesterday, "JPX", prior);
            require(edit.commit(), "Cannot save previous day meter evidence");
            var qualified = ValueAlertPreview.entries(state, market, today, "JPX", current,
                    java.util.Set.of(), code -> !code.equals("4444"));
            require(qualified.keySet().equals(java.util.Set.of("meter:1:1111", "meter:2:2222", "meter:3:3333")),
                    "Meter bands, issuer filter, or previous evidence check failed: " + qualified.keySet());
            require(ValueAlertPreview.title("東証", qualified).contains("超割安"), "Highest tier missing from heading");
            edit = state.edit();
            ValueAlertPreview.save(state, edit, market, today, "JPX", current);
            require(edit.putString(ValueAlertPreview.SETTINGS, "60,75,90").commit(), "Cannot store revised boundaries");
            var retry = ValueAlertPreview.entries(state, market, today, "JPX", current, qualified.keySet(),
                    code -> !code.equals("4444"));
            require(retry.isEmpty(), "Same-day retry lowered or duplicated a delivered tier");
            var corrupted = new org.json.JSONObject().put("latest", new org.json.JSONObject().put("day", "unknown"));
            require(state.edit().putString(market.key, corrupted.toString()).commit(), "Cannot write damaged meter metadata");
            edit = state.edit();
            ValueAlertPreview.save(state, edit, market, today, "JPX", current);
            require(edit.commit() && today.equals(ValueAlertPreview.history(state, market).latest().day()),
                    "Valid meter evidence did not recover from damaged metadata");
        } catch (org.json.JSONException invalid) {
            throw new AssertionError(invalid);
        }
    }

    private static void exerciseDiagnosticCopy(Instrumentation instrumentation, android.app.Activity activity) {
        var context = instrumentation.getTargetContext();
        instrumentation.runOnMainSync(() -> {
            var button = control(activity.getWindow().getDecorView(), "診断ログ", Button.class);
            require(button != null && button.performClick(), "Cannot open diagnostics offline");
        });
        require(await(() -> findDialogText(instrumentation, "診断ログをコピー") != null), "Diagnostics dialog is not visible");
        var copy = findDialogText(instrumentation, "診断ログをコピー");
        require(copy != null && copy.performAction(AccessibilityNodeInfo.ACTION_CLICK), "Cannot copy the diagnostic report");
        var clipboard = context.getSystemService(android.content.ClipboardManager.class);
        require(await(() -> {
            var clip = clipboard.getPrimaryClip();
            if (clip == null) return false;
            var report = clip.getItemAt(0).getText().toString();
            return report.contains("アプリ: ") && report.contains("（ビルド ")
                    && report.contains("現在の通信状態: 相場通信オフ")
                    && report.contains("テスト通知をAndroidに投稿") && report.contains("点灯を観測")
                    && !report.contains(JP_DETAIL) && !report.contains(US_DETAIL);
        }), "Offline diagnostic copy was missing stages or included notification details");
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
        return await(condition, 3500);
    }

    private static boolean await(BooleanSupplier condition, long timeout) {
        long until = SystemClock.elapsedRealtime() + timeout;
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
