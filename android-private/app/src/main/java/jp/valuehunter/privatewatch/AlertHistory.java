package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/** Device-only, seven-day history of notification delivery requests (not proof of display). */
final class AlertHistory {
    private static final String STORE = "common-alert-history";
    private static final String KEY = "requests-v1";
    private static final long WINDOW = TimeUnit.DAYS.toMillis(7);
    private static final int LIMIT = 150;
    private static final Object LOCK = new Object();
    record Entry(String receipt, long at, String title, String detail) {}
    private AlertHistory() {}

    static List<Entry> prune(List<Entry> entries, long now) {
        var result = new ArrayList<Entry>();
        var seen = new java.util.HashSet<String>();
        for (Entry e : entries) {
            if (e == null || e.receipt() == null || e.receipt().isBlank()
                    || e.at() > now || e.at() <= now - WINDOW || !seen.add(e.receipt())) continue;
            result.add(e);
        }
        result.sort((a, b) -> Long.compare(b.at(), a.at()));
        return List.copyOf(result.subList(0, Math.min(LIMIT, result.size())));
    }

    static List<Entry> add(List<Entry> existing, Entry entry, long now) {
        var all = new ArrayList<Entry>();
        all.add(entry);
        all.addAll(existing);
        return prune(all, now);
    }

    static List<Entry> read(Context context) {
        synchronized (LOCK) {
            return decode(context.getSharedPreferences(STORE, Context.MODE_PRIVATE).getString(KEY, ""), System.currentTimeMillis());
        }
    }

    static boolean record(Context context, String receipt, String title, String detail, long at) {
        synchronized (LOCK) {
            SharedPreferences prefs = context.getSharedPreferences(STORE, Context.MODE_PRIVATE);
            var entries = add(decode(prefs.getString(KEY, ""), at), new Entry(receipt, at, title, detail), at);
            return prefs.edit().putString(KEY, encode(entries)).commit();
        }
    }

    static List<Entry> decode(String raw, long now) {
        var entries = new ArrayList<Entry>();
        try {
            JSONArray array = new JSONArray(raw);
            for (int i = 0; i < Math.min(array.length(), 1000); i++) {
                JSONObject item = array.optJSONObject(i);
                if (item == null) continue;
                String receipt = item.optString("receipt", "");
                String title = item.optString("title", "");
                String detail = item.optString("detail", "");
                long at = item.optLong("at", 0);
                if (receipt.matches("[a-f0-9]{64}") && title.length() <= 300 && detail.length() <= 5000)
                    entries.add(new Entry(receipt, at, title, detail));
            }
        } catch (JSONException ignored) {
            // A corrupt history must not block notification delivery.
        }
        return prune(entries, now);
    }

    static String encode(List<Entry> entries) {
        JSONArray array = new JSONArray();
        for (Entry e : entries) {
            JSONObject item = new JSONObject();
            try {
                item.put("receipt", e.receipt());
                item.put("at", e.at());
                item.put("title", e.title());
                item.put("detail", e.detail());
                array.put(item);
            } catch (JSONException ignored) { }
        }
        return array.toString();
    }
}
