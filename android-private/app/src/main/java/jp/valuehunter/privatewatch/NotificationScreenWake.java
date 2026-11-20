package jp.valuehunter.privatewatch;

import android.content.Context;
import android.os.PowerManager;
import android.util.Log;

final class NotificationScreenWake {
    static final String ENABLED = "notification_wake_screen";
    private static final long SCREEN_MILLIS = 4000;

    private NotificationScreenWake() {}

    @SuppressWarnings("deprecation")
    static void afterPost(Context context) {
        try {
            if (!ScanWorker.alertsEnabled(context) || !ScanWorker.prefs(context).getBoolean(ENABLED, true)) return;
            var power = context.getSystemService(PowerManager.class);
            if (power == null || power.isInteractive()
                    || !power.isWakeLockLevelSupported(PowerManager.SCREEN_DIM_WAKE_LOCK)) return;
            // A timed screen lock requests wake without starting an activity or unlocking the device.
            var lock = power.newWakeLock(PowerManager.SCREEN_DIM_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                    "valuehunter:notification-screen");
            lock.setReferenceCounted(false);
            lock.acquire(SCREEN_MILLIS);
        } catch (SecurityException | IllegalStateException unavailable) {
            Log.d("ValueHunterNotify", "Screen wake unavailable");
        }
    }
}
