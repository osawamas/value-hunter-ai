package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.Log;

import androidx.work.ListenableWorker;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.json.JSONObject;
import org.json.JSONException;
import java.util.regex.Pattern;
import java.util.function.Supplier;

/** Bounded, on-device diagnostics. Callers provide statuses and counts, never payloads. */
final class DiagnosticLog {
    private static final String PREFS = "diagnostic-log";
    private static final String EVENTS = "events";
    private static final String STRUCTURED = "structured_events";
    private static final long RETENTION_MS = 7L * 24 * 60 * 60 * 1000;
    private static final Pattern SECRET = Pattern.compile("(?i)(api[_-]?key|token|authorization|password|secret)\\s*[:=]\\s*[^\\s,;]+");
    private static final int LIMIT = 240;
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss", Locale.JAPAN)
            .withZone(ZoneId.of("Asia/Tokyo"));

    enum Area {
        NETWORK("通信"), JPX("東証更新"), US_CLOSE("米国株終値"), US_FINANCE("米国株財務"),
        US_LISTING("米国株上場一覧"), US_BUDGET("米国株予算チェック"), ALERT("通知"), WAKE("画面点灯"), CRASH("クラッシュ");

        final String label;
        Area(String label) { this.label = label; }
    }

    static synchronized void record(Context context, Area area, String event) {
        var row = CLOCK.format(Instant.now()) + "  " + area.label + "  " + redact(event);
        Log.i("ValueHunterDiag", row);
        try {
            var state = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            state.edit().putString(EVENTS, append(state.getString(EVENTS, ""), row)).apply();
            String level = classify(event);
            String location = "";
            String trace = "";
            if (!"INFO".equals(level)) {
                for (StackTraceElement frame : Thread.currentThread().getStackTrace()) {
                    if (!frame.getClassName().startsWith("jp.valuehunter.")
                            || frame.getClassName().equals(DiagnosticLog.class.getName())) continue;
                    location = frame.getFileName() + ":" + frame.getLineNumber();
                    trace = frame.getClassName() + "." + frame.getMethodName() + " (" + location + ")";
                    break;
                }
            }
            persistStructured(state, level, area.label, event, "", location, trace, false);
        } catch (RuntimeException unavailable) {
            // Local diagnostics must never stop market work or a notification.
        }
    }

    static synchronized void recordError(Context context, Area area, String operation, Throwable error) {
        String kind = error == null ? "Unknown" : error.getClass().getSimpleName();
        var row = CLOCK.format(Instant.now()) + "  " + area.label + "  "
                + redact(operation) + " · " + kind + " · 失敗";
        Log.e("ValueHunterDiag", row);
        if (error == null) return;
        try {
            String location = "";
            StringBuilder stack = new StringBuilder(kind);
            int frames = 0;
            for (StackTraceElement frame : error.getStackTrace()) {
                if (!frame.getClassName().startsWith("jp.valuehunter.")) continue;
                String line = frame.getFileName() + ":" + frame.getLineNumber();
                if (location.isEmpty()) location = line;
                if (frames++ >= 12) break;
                stack.append("\n at ").append(frame.getClassName()).append(".")
                        .append(frame.getMethodName()).append("(").append(line).append(")");
            }
            var state = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            state.edit().putString(EVENTS, append(state.getString(EVENTS, ""), row)).commit();
            persistStructured(state, "ERROR", area.label, operation, kind, location, stack.toString(), true);
        } catch (RuntimeException ignored) {
            // Diagnostics must never obstruct notifications, workers or UI.
        }
    }

    static String classify(String event) {
        if (event.contains("再試行") || event.contains("待ち") || event.contains("タイムアウト")) return "RETRY";
        if (event.contains("失敗") || event.contains("例外") || event.contains("エラー")
                || event.contains("保存できず") || event.contains("取得できず")
                || event.contains("読み込めなかった")) return "ERROR";
        return "INFO";
    }

    private static void persistStructured(android.content.SharedPreferences prefs, String level,
                                          String area, String operation, String exception,
                                          String location, String trace, boolean urgent) {
        try {
            long now = System.currentTimeMillis();
            var entry = new JSONObject().put("time", now).put("level", level)
                    .put("area", area).put("operation", redact(operation))
                    .put("exception", exception).put("location", location)
                    .put("trace", redact(trace));
            String existing = prefs.getString(STRUCTURED, "");
            StringBuilder keep = new StringBuilder();
            if (!existing.isEmpty()) for (String row : existing.split("\n")) {
                try {
                    var old = new JSONObject(row);
                    if (now - old.optLong("time") > RETENTION_MS || now < old.optLong("time")) continue;
                    if (keep.length() > 0) keep.append('\n');
                    keep.append(row);
                } catch (JSONException ignored) {
                    // One corrupted event must not destroy remaining diagnostics.
                }
            }
            if (keep.length() > 0) keep.append('\n');
            keep.append(entry);
            String[] records = keep.toString().split("\n");
            var edit = prefs.edit().putString(STRUCTURED, String.join("\n",
                    java.util.Arrays.asList(records).subList(Math.max(0, records.length - LIMIT),
                            records.length)));
            if (urgent) edit.commit(); else edit.apply();
        } catch (JSONException | RuntimeException ignored) {
            // Logging never blocks actual work.
        }
    }

    static String redact(String value) {
        if (value == null) return "";
        return SECRET.matcher(value).replaceAll("$1=[REDACTED]");
    }

    static synchronized List<JSONObject> entries(Context context) {
        List<JSONObject> result = new ArrayList<>();
        try {
            String rows = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .getString(STRUCTURED, "");
            long now = System.currentTimeMillis();
            for (String row : rows.split("\n")) {
                if (row.isEmpty()) continue;
                try {
                    JSONObject event = new JSONObject(row);
                    long when = event.optLong("time");
                    if (when > 0 && now >= when && now - when <= RETENTION_MS) result.add(event);
                } catch (JSONException ignored) {}
            }
        } catch (RuntimeException ignored) {}
        java.util.Collections.reverse(result);
        return result;
    }

    static String detailedReport(Context context) {
        var builder = new StringBuilder(report(context)).append("\n\n--- 詳細診断 ---");
        for (JSONObject event : entries(context)) {
            builder.append("\n").append(CLOCK.format(Instant.ofEpochMilli(event.optLong("time"))))
                    .append(" [").append(event.optString("level")).append("] ")
                    .append(event.optString("area")).append(" ")
                    .append(event.optString("operation"));
            if (!event.optString("location").isEmpty())
                builder.append(" @ ").append(event.optString("location"));
            if (!event.optString("trace").isEmpty())
                builder.append("\n").append(event.optString("trace"));
        }
        return redact(builder.toString());
    }

    static String append(String saved, String row) {
        var entries = new ArrayList<>(saved.isEmpty() ? List.<String>of() : List.of(saved.split("\n")));
        entries.add(row);
        return String.join("\n", entries.subList(Math.max(0, entries.size() - LIMIT), entries.size()));
    }

    static synchronized String read(Context context) {
        try {
            return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(EVENTS, "");
        } catch (RuntimeException unavailable) {
            return "";
        }
    }

    static String report(Context context) {
        String events = read(context);
        return context.getString(R.string.app_name) + " 診断ログ（日本時間）\n"
                + Build.MANUFACTURER + " " + Build.MODEL + " · Android " + Build.VERSION.RELEASE
                + "（API " + Build.VERSION.SDK_INT + "）\n"
                + "アプリ: " + appVersion(context) + "\n"
                + "現在の通信状態: " + route() + "\n\n"
                + (events.isEmpty() ? "診断の記録はまだありません" : events);
    }

    @SuppressWarnings("deprecation")
    private static String appVersion(Context context) {
        try {
            var info = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            long code = Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
            return info.versionName + "（ビルド " + code + "）";
        } catch (PackageManager.NameNotFoundException unavailable) {
            return "ビルド情報を取得できず";
        }
    }

    static void requested(Context context, Area area, String kind) {
        record(context, area, "更新の予約を依頼（" + kind + "） · " + route());
    }

    static ListenableWorker.Result work(Context context, Area area, int attempt,
                                        Supplier<ListenableWorker.Result> action) {
        record(context, area, "実行開始 · 試行 " + (attempt + 1) + " · " + route());
        try {
            var result = action.get();
            String status = ListenableWorker.Result.retry().equals(result) ? "再試行"
                    : ListenableWorker.Result.success().equals(result) ? "完了（データの更新状態は個別の記録を確認）" : "失敗";
            record(context, area, "実行結果: " + status + " · " + route());
            recordFreshness(context, area);
            return result;
        } catch (RuntimeException failure) {
            recordError(context, area, "実行例外", failure);
            throw failure;
        }
    }

    private static void recordFreshness(Context context, Area area) {
        var market = switch (area) {
            case JPX -> MarketFreshness.JPX;
            case US_CLOSE -> MarketFreshness.US_CLOSE;
            case US_FINANCE -> MarketFreshness.US_FINANCE;
            default -> null;
        };
        if (market == null) return;
        try {
            var state = ScanWorker.prefs(context);
            var phase = market.phase(state);
            String status = phase != null ? "保存状態: " + phase.label
                    : market.day(state) != null ? "保存済み取引日: " + market.day(state) : "";
            if (!status.isEmpty()) record(context, area, status);
        } catch (RuntimeException unavailable) {
            // A diagnostic read is optional even when a saved market status is unreadable.
        }
    }

    static String route() {
        if (!MarketNetwork.requested()) return "相場通信オフ";
        if (!MarketNetwork.allowed()) return MarketNetwork.waitingForWifi() ? "Wi-Fi待ち" : "通信を一時停止";
        return MarketNetwork.wifiOnly() ? "Wi-Fi接続・通信許可" : "相場通信を許可";
    }
}
