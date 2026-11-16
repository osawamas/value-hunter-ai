package jp.valuehunter.privatewatch;

import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashSet;
import java.util.List;
import javax.net.ssl.HttpsURLConnection;

final class JQuants {
    static final ZoneId TOKYO = ZoneId.of("Asia/Tokyo");
    private static final String BASE = "https://api.jquants.com/v2";
    private final String apiKey;
    private long nextRequest;

    record Snapshot(LocalDate date, List<JapanScreen.Candidate> candidates) {}

    JQuants(String apiKey) { this.apiKey = apiKey; }

    Snapshot scan(boolean delayed, String previousDate) throws IOException, JSONException, InterruptedException {
        LocalDate today = LocalDate.now(TOKYO);
        LocalDate newest = delayed ? today.minusWeeks(12).minusDays(1) : today;
        for (int offset = 0; offset < 10; offset++) {
            LocalDate date = newest.minusDays(offset);
            if (date.toString().compareTo(previousDate) <= 0) return null;
            if (date.getDayOfWeek() == DayOfWeek.SATURDAY || date.getDayOfWeek() == DayOfWeek.SUNDAY) continue;
            JSONArray prices = pages("/equities/bars/daily", date);
            if (prices.length() == 0) continue;
            JSONArray valuation = pages("/equities/valuation", date);
            JSONArray master = pages("/equities/master", date);
            return new Snapshot(date, JapanScreen.find(date, prices, valuation, master));
        }
        throw new IOException("取得対象期間に終値が見つからなかった");
    }

    private JSONArray pages(String path, LocalDate date) throws IOException, JSONException, InterruptedException {
        String query = BASE + path + "?date=" + date;
        String token = null;
        var seen = new HashSet<String>();
        var all = new JSONArray();
        do {
            String url = token == null ? query : query + "&pagination_key="
                    + URLEncoder.encode(token, StandardCharsets.UTF_8.name());
            JSONObject page = get(url);
            JSONArray rows = page.getJSONArray("data");
            for (int i = 0; i < rows.length(); i++) all.put(rows.getJSONObject(i));
            token = page.isNull("pagination_key") ? null : page.getString("pagination_key");
            if (token != null && (token.isEmpty() || !seen.add(token) || seen.size() > 20)) {
                throw new JSONException("ページ分割を確認できなかった");
            }
        } while (token != null);
        return all;
    }

    private JSONObject get(String url) throws IOException, JSONException, InterruptedException {
        long wait = nextRequest - SystemClock.elapsedRealtime();
        if (wait > 0) Thread.sleep(wait);
        nextRequest = SystemClock.elapsedRealtime() + 12_500;
        var connection = (HttpsURLConnection) new URL(url).openConnection();
        connection.setConnectTimeout(15_000);
        connection.setReadTimeout(20_000);
        connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("x-api-key", apiKey);
        connection.setRequestProperty("Accept", "application/json");
        try {
            int status = connection.getResponseCode();
            if (status != 200) throw new HttpFailure(status);
            try (var reader = new BufferedReader(new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                StringBuilder body = new StringBuilder();
                char[] buffer = new char[8192];
                int length;
                while ((length = reader.read(buffer)) != -1) {
                    body.append(buffer, 0, length);
                    if (body.length() > 12_000_000) throw new IOException("応答が大きすぎる");
                }
                return new JSONObject(body.toString());
            }
        } finally {
            connection.disconnect();
        }
    }

    static final class HttpFailure extends IOException {
        final int status;
        HttpFailure(int status) { this.status = status; }
    }
}
