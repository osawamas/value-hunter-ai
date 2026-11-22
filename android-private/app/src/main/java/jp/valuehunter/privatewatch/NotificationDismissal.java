package jp.valuehunter.privatewatch;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;

import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

/** Records independently of history so a restarted worker can recover a submitted alert. */
public final class NotificationDismissal extends BroadcastReceiver {
    private static final String STORE = "notification-dismissals";
    private static final String SCHEME = "valuehunter-dismiss";
    private static final long RETAIN = TimeUnit.DAYS.toMillis(7);
    private static final Pattern RECEIPT = Pattern.compile("[0-9]+-[a-f0-9]{64}");

    static PendingIntent intent(Context context, String receipt) {
        var acknowledge = new Intent(context, NotificationDismissal.class)
                .setData(Uri.fromParts(SCHEME, receipt, null));
        return PendingIntent.getBroadcast(context, 0, acknowledge, PendingIntent.FLAG_IMMUTABLE);
    }

    static PendingIntent openIntent(Context context, String receipt) {
        var open = new Intent(context, NotificationOpenActivity.class)
                .setData(Uri.fromParts(SCHEME, receipt, null));
        return PendingIntent.getActivity(context, 0, open, PendingIntent.FLAG_IMMUTABLE);
    }

    static long recordedAt(Context context, String receipt, long now) {
        var state = context.getSharedPreferences(STORE, Context.MODE_PRIVATE);
        long at = state.getLong(receipt, 0);
        return isRecent(at, now) ? at : 0;
    }

    static void recordSubmission(Context context, String receipt) {
        remember(context.getSharedPreferences(STORE, Context.MODE_PRIVATE), receipt, System.currentTimeMillis());
    }

    static boolean isRecent(long at, long now) {
        return at > 0 && at <= now && now - at < RETAIN;
    }

    @Override public void onReceive(Context context, Intent intent) {
        record(context, intent.getData());
    }

    static void record(Context context, Uri data) {
        if (data == null || !SCHEME.equals(data.getScheme())) return;
        String receipt = data.getSchemeSpecificPart();
        if (receipt == null || !RECEIPT.matcher(receipt).matches()) return;
        remember(context.getSharedPreferences(STORE, Context.MODE_PRIVATE), receipt, System.currentTimeMillis());
    }

    static synchronized void remember(android.content.SharedPreferences state, String receipt, long now) {
        var edit = state.edit();
        var saved = state.getAll();
        saved.forEach((key, value) -> {
            if (!(value instanceof Long at) || !isRecent(at, now)) edit.remove(key);
        });
        long original = saved.get(receipt) instanceof Long at ? at : 0;
        edit.putLong(receipt, isRecent(original, now) ? original : now).commit();
    }
}
