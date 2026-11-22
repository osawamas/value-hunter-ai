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
import java.util.function.Supplier;

/** Bounded, on-device diagnostics. Callers provide statuses and counts, never payloads. */
final class DiagnosticLog {
    private static final String PREFS = "diagnostic-log";
    private static final String EVENTS = "events";
    private static final int LIMIT = 240;
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss", Locale.JAPAN)
            .withZone(ZoneId.of("Asia/Tokyo"));

    enum Area {
        NETWORK("通信"), JPX("東証更新"), US_CLOSE("米国株終値"), US_FINANCE("米国株財務"),
        US_LISTING("米国株上場一覧"), US_BUDGET("米国株予算チェック"), ALERT("通知"), WAKE("画面点灯");

        final String label;
        Area(String label) { this.label = label; }
    }

    static synchronized void record(Context context, Area area, String event) {
        var row = CLOCK.format(Instant.now()) + "  " + area.label + "  " + event;
        Log.i("ValueHunterDiag", row);
        try {
            var state = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            state.edit().putString(EVENTS, append(state.getString(EVENTS, ""), row)).apply();
        } catch (RuntimeException unavailable) {
            // Local diagnostics must never stop market work or a notification.
        }
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
            record(context, area, "実行例外: " + failure.getClass().getSimpleName());
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
