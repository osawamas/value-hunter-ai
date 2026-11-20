package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.Locale;

public final class UsScanWorker extends Worker {
    private static final Object LOCK = new Object();
    private static final ZoneId NEW_YORK = ZoneId.of("America/New_York");

    public UsScanWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    @NonNull @Override public Result doWork() {
        if (!MarketNetwork.allowed()) return Result.success();
        if (!getInputData().getBoolean(ScanWorker.LEGACY_API_REQUEST, false)) return Result.success();
        synchronized (LOCK) {
            return scan();
        }
    }

    private Result scan() {
        var context = getApplicationContext();
        SharedPreferences state = ScanWorker.prefs(context);
        String key = state.getString("us_key", "");
        if (key.isEmpty()) return Result.success();
        state.edit().putString("us_status", "IBMの終値と為替を確認中…").apply();
        try {
            var now = ZonedDateTime.now(NEW_YORK);
            LocalDate cutoff = now.toLocalTime().isBefore(LocalTime.of(18, 0))
                    ? now.toLocalDate().minusDays(1) : now.toLocalDate();
            var payload = new JSONObject(get("https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
                    + "&symbol=IBM&apikey=" + URLEncoder.encode(key, StandardCharsets.UTF_8.name())));
            var close = UsScreen.readClose(payload, cutoff);
            String latest = state.getString("us_date", "");
            if (!latest.isEmpty() && close.date().toString().compareTo(latest) <= 0) {
                if (key.equals(state.getString("us_key", ""))) {
                    state.edit().putString("us_status", "新しい取引日の終値はまだない").apply();
                }
                return Result.success();
            }
            var fx = UsScreen.readFx(new JSONArray(get("https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY"
                    + "&from=" + close.date().minusDays(4) + "&to=" + close.date())), close.date());
            var trial = UsScreen.trial(close, fx);
            if (isStopped() || !key.equals(state.getString("us_key", ""))) return Result.success();
            boolean alert = trial != null && UsScreen.shouldAlert(state.contains("us_qualified"),
                    state.getBoolean("us_qualified", false), trial.qualifies());
            String result = String.format(Locale.JAPAN, "IBM · %s 終値 %.2f USD\n為替基準日 %s · 1 USD = %.2f円",
                    close.date(), close.usd(), fx.date(), fx.yenPerDollar());
            var editor = state.edit().putString("us_date", close.date().toString());
            if (trial == null) {
                result += "\n利用できる開示期間外。割安判定は保留";
            } else {
                result += String.format(Locale.JAPAN, "\n%d株 約%,.0f円 · 参考PER %.2f倍 · 参考PBR %.2f倍"
                                + "\n株数基準日 %s（直近の同梱SEC開示） · %s",
                        trial.quantity(), trial.yen(), trial.per(), trial.pbr(), UsScreen.SHARES_DATE,
                        trial.qualifies() ? "条件に該当" : "条件外");
                editor.putBoolean("us_qualified", trial.qualifies());
            }
            if (!editor.putString("us_status", "取得完了").putString("us_result", result).commit()) {
                return Result.retry();
            }
            if (alert) ScanWorker.postNotification(context, 3, "米国株の新しい割安候補（試験）", result);
            return Result.success();
        } catch (IOException | JSONException error) {
            if (key.equals(state.getString("us_key", ""))) {
                String message = error instanceof JSONException && error.getMessage() != null
                        && error.getMessage().startsWith("IBMの日足")
                        ? error.getMessage() : "米国株の終値か為替を取得・照合できなかった";
                state.edit().putString("us_status", message).apply();
            }
            return getRunAttemptCount() == 0 ? Result.retry() : Result.failure();
        }
    }

    private static String get(String address) throws IOException {
        return get(address, null);
    }

    static String get(String address, String bearer) throws IOException {
        var connection = MarketNetwork.open(new URL(address));
        connection.setConnectTimeout(15_000);
        connection.setReadTimeout(20_000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Accept", "application/json");
        if (bearer != null) connection.setRequestProperty("Authorization", "Bearer " + bearer);
        try {
            int status = MarketNetwork.response(connection);
            if (status != 200) throw new HttpFailure(status);
            try (var stream = MarketNetwork.input(connection); var buffer = new ByteArrayOutputStream()) {
                byte[] bytes = new byte[8192];
                for (int read; (read = stream.read(bytes)) != -1;) {
                    if (buffer.size() + read > 1_048_576) throw new IOException("Market data response too large");
                    buffer.write(bytes, 0, read);
                }
                return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
            }
        } finally {
            MarketNetwork.close(connection);
        }
    }

    static final class HttpFailure extends IOException {
        final int status;
        HttpFailure(int status) { this.status = status; }
    }
}
