package jp.valuehunter.privatewatch;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;

import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

/** Records explicit clears so a restarted worker can finish saving a posted alert. */
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

    static boolean recorded(Context context, String receipt) {
        var state = context.getSharedPreferences(STORE, Context.MODE_PRIVATE);
        return isRecent(state.getLong(receipt, 0), System.currentTimeMillis());
    }

    static boolean isRecent(long at, long now) {
        return at > 0 && at <= now && now - at < RETAIN;
    }

    @Override public void onReceive(Context context, Intent intent) {
        var data = intent.getData();
        if (data == null || !SCHEME.equals(data.getScheme())) return;
        String receipt = data.getSchemeSpecificPart();
        if (receipt == null || !RECEIPT.matcher(receipt).matches()) return;
        long now = System.currentTimeMillis();
        var state = context.getSharedPreferences(STORE, Context.MODE_PRIVATE);
        var edit = state.edit();
        state.getAll().forEach((key, value) -> {
            if (!(value instanceof Long at) || !isRecent(at, now)) edit.remove(key);
        });
        edit.putLong(receipt, now).commit();
    }
}
