package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.atomic.AtomicInteger;

enum MarketUpdate {
    JPX("jpx_last_update"),
    US_CLOSE("us_close_last_update"),
    US_FINANCE("us_finance_last_update");

    private static final DateTimeFormatter JAPAN_TIME = DateTimeFormatter
            .ofPattern("M月d日 HH:mm", Locale.JAPAN).withZone(ZoneId.of("Asia/Tokyo"));
    private static final Set<Runnable> LISTENERS = new CopyOnWriteArraySet<>();
    private final AtomicInteger running = new AtomicInteger();
    final String lastUpdate;

    MarketUpdate(String lastUpdate) {
        this.lastUpdate = lastUpdate;
    }

    static void addListener(Runnable listener) {
        LISTENERS.add(listener);
    }

    static void removeListener(Runnable listener) {
        LISTENERS.remove(listener);
    }

    void started() {
        if (running.getAndIncrement() == 0) publish();
    }

    void finished() {
        if (running.decrementAndGet() == 0) publish();
    }

    private static void publish() {
        if (!LISTENERS.isEmpty()) {
            new Handler(Looper.getMainLooper()).post(() -> LISTENERS.forEach(Runnable::run));
        }
    }

    SharedPreferences.Editor completed(SharedPreferences.Editor edit) {
        return edit.putLong(lastUpdate, System.currentTimeMillis());
    }

    String display(SharedPreferences state) {
        long last = state.getLong(lastUpdate, 0);
        String status = MarketNetwork.allowed() && running.get() > 0 ? "更新中" : "";
        if (last == 0) return status;
        if (!MarketNetwork.allowed()) return lastUpdateLabel(last);
        return (status.isEmpty() ? "前回の更新完了" : status) + " · " + lastUpdateLabel(last);
    }

    private static String lastUpdateLabel(long time) {
        return "最終更新 " + JAPAN_TIME.format(Instant.ofEpochMilli(time)) + "（日本時間）";
    }
}
