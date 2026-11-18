package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.AtomicFile;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.concurrent.TimeUnit;

import javax.net.ssl.HttpsURLConnection;

public final class UsDailyWorker extends Worker {
    private static final String WORK = "us-daily-closes";
    private static final String KEY_FILE = "massive-key.txt";
    private static final String STATUS = "us_massive_daily_status";
    private static final String PROVIDER = "us_daily_close_provider";
    private static final String MASSIVE = "massive-grouped-daily";
    private static final String DATE = "us_massive_daily_close_date";
    private static final String COUNT = "us_massive_daily_close_count";
    private static final String ENDPOINT =
            "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/";

    public UsDailyWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    static void schedule(Context context) {
        var workManager = WorkManager.getInstance(context);
        var request = new PeriodicWorkRequest.Builder(UsDailyWorker.class, 6, TimeUnit.HOURS)
                .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .build();
        workManager.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
    }

    static String displayStatus(SharedPreferences state) {
        String status = state.getString(STATUS, "初回の自動更新待ち");
        String day = state.getString(DATE, "");
        if (day.isEmpty()) return status;
        String source = MASSIVE.equals(state.getString(PROVIDER, "")) ? "Massive" : "DoltHub参考値";
        return status + "\n取得済み " + day + "（米東部） · " + source + " "
                + state.getInt(COUNT, 0) + "件";
    }

    @NonNull @Override public Result doWork() {
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        try {
            String key = readKey(context);
            String provider = key.isEmpty() ? UsDoltCloses.SOURCE : MASSIVE;
            var file = new AtomicFile(new File(context.getNoBackupFilesDir(), "us-daily-closes.json"));
            LocalDate previous = cachedDate(file, state, provider);
            LocalDate target = UsDailyCloses.mostRecentEligibleDay(Instant.now());
            for (int offset = 0; offset < 7; offset++) {
                if (isStopped()) return Result.retry();
                LocalDate day = target.minusDays(offset);
                if (previous != null && !day.isAfter(previous)) {
                    report(state, day.equals(target) ? "終値を取得済み" : "新しい終値の公開待ち");
                    return Result.success();
                }
                if (day.getDayOfWeek() == DayOfWeek.SATURDAY || day.getDayOfWeek() == DayOfWeek.SUNDAY) {
                    continue;
                }

                var closes = key.isEmpty()
                        ? UsDoltCloses.fetch(day, address -> {
                            if (isStopped()) throw new IOException("Worker stopped");
                            return fetch(address, "");
                        })
                        : UsDailyCloses.parse(fetch(ENDPOINT + day + "?adjusted=false&include_otc=false", key), day);
                if (closes.length() == 0) continue;
                var snapshot = new JSONObject()
                        .put("source", provider)
                        .put("adjusted", key.isEmpty() ? JSONObject.NULL : Boolean.FALSE)
                        .put("trading_date_et", day.toString())
                        .put("fetched_at_utc", Instant.now().toString())
                        .put("closes", closes);
                if (isStopped()) return Result.retry();
                writeSnapshot(file, snapshot);
                state.edit().putString(DATE, day.toString()).putInt(COUNT, closes.length())
                        .putString(PROVIDER, provider)
                        .putString(STATUS, "終値の自動取得に成功").apply();
                return Result.success();
            }
            report(state, "直近7日間の終値を取得できず");
            return Result.success();
        } catch (HttpStatus e) {
            report(state, "終値を取得できず（HTTP " + e.code + "）");
            return e.code == 429 || e.code >= 500 ? Result.retry() : Result.success();
        } catch (IOException e) {
            report(state, "終値を取得できず（通信または保存エラー）");
            return Result.retry();
        } catch (JSONException e) {
            report(state, "終値を取得できず（配信形式を要確認）");
            return Result.success();
        }
    }

    private static LocalDate cachedDate(AtomicFile file, SharedPreferences state, String provider) {
        try {
            var snapshot = new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
            var date = LocalDate.parse(snapshot.getString("trading_date_et"));
            String storedProvider = snapshot.getString("source");
            state.edit().putString(DATE, date.toString()).putString(PROVIDER, storedProvider)
                    .putInt(COUNT, snapshot.getJSONArray("closes").length()).apply();
            return provider.equals(storedProvider) ? date : null;
        } catch (IOException | JSONException | DateTimeParseException e) {
            state.edit().remove(DATE).remove(COUNT).remove(PROVIDER).apply();
            return null;
        }
    }

    private static void writeSnapshot(AtomicFile file, JSONObject snapshot) throws IOException {
        var stream = file.startWrite();
        try {
            stream.write(snapshot.toString().getBytes(StandardCharsets.UTF_8));
            file.finishWrite(stream);
        } catch (IOException e) {
            file.failWrite(stream);
            throw e;
        }
    }

    private static JSONObject fetch(String address, String key) throws IOException, JSONException {
        var url = new URL(address);
        var connection = (HttpsURLConnection) url.openConnection();
        try {
            connection.setConnectTimeout(15_000);
            connection.setReadTimeout(30_000);
            connection.setInstanceFollowRedirects(false);
            if (!key.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + key);
            int code = connection.getResponseCode();
            if (code != 200) throw new HttpStatus(code);
            try (var input = connection.getInputStream()) {
                var output = new ByteArrayOutputStream();
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    if (output.size() + count > UsDailyCloses.MAX_BYTES) {
                        throw new JSONException("Daily summary exceeds size limit");
                    }
                    output.write(buffer, 0, count);
                }
                return new JSONObject(new String(output.toByteArray(), StandardCharsets.UTF_8));
            }
        } finally {
            connection.disconnect();
        }
    }

    private static String readKey(Context context) throws IOException {
        try (var input = context.getAssets().open(KEY_FILE)) {
            byte[] bytes = new byte[257];
            int length = 0;
            int count;
            while (length < bytes.length && (count = input.read(bytes, length, bytes.length - length)) > 0) {
                length += count;
            }
            if (length == bytes.length) return "";
            String key = new String(bytes, 0, length, StandardCharsets.UTF_8).trim();
            return key.matches("[A-Za-z0-9_-]+") ? key : "";
        } catch (FileNotFoundException e) {
            return "";
        }
    }

    private static void report(SharedPreferences state, String status) {
        state.edit().putString(STATUS, status).apply();
    }

    private static final class HttpStatus extends IOException {
        final int code;

        HttpStatus(int code) {
            this.code = code;
        }
    }
}
