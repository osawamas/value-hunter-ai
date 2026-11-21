package jp.valuehunter.privatewatch;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.function.LongSupplier;

/** Stores recent, submitted notifications independently of Android's notification list. */
final class NotificationHistory {
    static final int DAYS = 7;
    private static final int MAX_ENTRIES = 256;
    private static final long RETENTION = TimeUnit.DAYS.toMillis(DAYS);

    record Entry(String receipt, long postedAt, String title, String detail) {}

    private NotificationHistory() {}

    static File file(Context context) {
        return new File(context.getNoBackupFilesDir(), "notification-history-v1.json");
    }

    static synchronized boolean deliver(File file, String receipt, String title, String detail, long now,
                                        LongSupplier existingDelivery, Runnable post, Runnable wake) throws IOException {
        var history = read(file, now);
        if (history.stream().anyMatch(entry -> entry.receipt().equals(receipt))) return true;

        long postedAt = existingDelivery.getAsLong();
        if (postedAt <= 0) {
            post.run();
            postedAt = now;
            // Screen wake is optional; failure must not lose the successful post receipt.
            try {
                wake.run();
            } catch (RuntimeException unavailable) {
                // Continue to persist the posted notification for replay deduplication.
            }
        }

        history.add(new Entry(receipt, Math.min(postedAt, now), title, detail));
        history.sort(Comparator.comparingLong(Entry::postedAt).reversed());
        save(file, history.subList(0, Math.min(history.size(), MAX_ENTRIES)));
        return true;
    }

    static synchronized List<Entry> recent(File file, long now) throws IOException {
        return List.copyOf(read(file, now));
    }

    private static ArrayList<Entry> read(File file, long now) throws IOException {
        var entries = new ArrayList<Entry>();
        if (!file.exists()) return entries;
        try {
            var stored = new JSONArray(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
            var receipts = new java.util.HashSet<String>();
            for (int i = 0; i < stored.length(); i++) {
                var row = stored.optJSONObject(i);
                if (row == null) continue;
                long at = row.optLong("at", 0);
                String receipt = row.optString("receipt");
                String title = row.optString("title");
                if (at > 0 && (at > now || now - at < RETENTION)
                        && !receipt.isEmpty() && !title.isEmpty() && receipts.add(receipt)) {
                    entries.add(new Entry(receipt, at, title, row.optString("detail")));
                }
            }
        } catch (JSONException invalid) {
            // An invalid file has no reliable delivery records.
        }
        entries.sort(Comparator.comparingLong(Entry::postedAt).reversed());
        if (entries.size() > MAX_ENTRIES) entries.subList(MAX_ENTRIES, entries.size()).clear();
        return entries;
    }

    private static void save(File file, List<Entry> entries) throws IOException {
        var stored = new JSONArray();
        try {
            for (var entry : entries) {
                stored.put(new JSONObject().put("receipt", entry.receipt()).put("at", entry.postedAt())
                        .put("title", entry.title()).put("detail", entry.detail()));
            }
        } catch (JSONException invalid) {
            throw new IOException("Invalid notification history", invalid);
        }
        var temp = new File(file.getParentFile(), file.getName() + ".tmp");
        try {
            try (var output = new FileOutputStream(temp)) {
                output.write(stored.toString().getBytes(StandardCharsets.UTF_8));
                output.getFD().sync();
            }
            Files.move(temp.toPath(), file.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            temp.delete();
        }
    }
}
