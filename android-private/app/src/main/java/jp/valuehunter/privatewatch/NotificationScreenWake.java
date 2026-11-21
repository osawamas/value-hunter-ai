package jp.valuehunter.privatewatch;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;

final class NotificationScreenWake {
    static final String ENABLED = "notification_wake_screen";
    private static final long SCREEN_MILLIS = 4000;

    private NotificationScreenWake() {}

    @SuppressWarnings("deprecation")
    static void afterPost(Context context) {
        try {
            if (!ScanWorker.alertsEnabled(context) || !ScanWorker.prefs(context).getBoolean(ENABLED, true)) {
                DiagnosticLog.record(context, DiagnosticLog.Area.WAKE, "設定により点灯を省略");
                return;
            }
            var power = context.getSystemService(PowerManager.class);
            if (power == null || !power.isWakeLockLevelSupported(PowerManager.SCREEN_DIM_WAKE_LOCK)) {
                DiagnosticLog.record(context, DiagnosticLog.Area.WAKE, "端末が点灯要求に対応していない");
                return;
            }
            if (power.isInteractive()) {
                DiagnosticLog.record(context, DiagnosticLog.Area.WAKE, "画面が既に点灯中");
                return;
            }
            // A timed screen lock requests wake without starting an activity or unlocking the device.
            var lock = power.newWakeLock(PowerManager.SCREEN_DIM_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                    "valuehunter:notification-screen");
            lock.setReferenceCounted(false);
            lock.acquire(SCREEN_MILLIS);
            DiagnosticLog.record(context, DiagnosticLog.Area.WAKE, "Androidに点灯を要求");
            var app = context.getApplicationContext();
            new Handler(Looper.getMainLooper()).postDelayed(() -> {
                try {
                    DiagnosticLog.record(app, DiagnosticLog.Area.WAKE, power.isInteractive()
                            ? "点灯を観測" : "観測時点では消灯中");
                } catch (RuntimeException unavailable) {
                    DiagnosticLog.record(app, DiagnosticLog.Area.WAKE, "点灯状態を確認できず");
                }
            }, 750);
        } catch (SecurityException | IllegalStateException unavailable) {
            Log.d("ValueHunterNotify", "Screen wake unavailable");
            DiagnosticLog.record(context, DiagnosticLog.Area.WAKE, "点灯要求に失敗");
        }
    }
}
