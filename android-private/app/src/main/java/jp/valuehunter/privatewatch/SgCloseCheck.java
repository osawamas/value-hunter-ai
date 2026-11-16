package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.time.DateTimeException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.TreeMap;

final class SgCloseCheck {
    static final ZoneId SINGAPORE = ZoneId.of("Asia/Singapore");
    static final String SYMBOL = "sgx:S63";

    record Close(LocalDate session, double sgd) {}
    record Pair(Close previous, Close latest) {}

    static Pair read(JSONObject payload, LocalDate cutoff) throws JSONException {
        var meta = payload.getJSONObject("meta");
        if (!SYMBOL.equals(meta.getString("sid")) || !"SGD".equals(meta.getString("currency"))
                || !SINGAPORE.getId().equals(meta.getString("timezone"))) {
            throw new JSONException("S63の銘柄・通貨・時間帯が一致しない");
        }
        var sessions = new TreeMap<LocalDate, Close>();
        var data = payload.getJSONArray("data");
        for (int i = 0; i < data.length(); i++) {
            var bar = data.getJSONObject(i);
            if (!SYMBOL.equals(bar.getString("sid")) || !"1Day".equals(bar.getString("timeframe"))
                    || !"raw".equals(bar.getString("adjustment"))) {
                throw new JSONException("S63の未調整日足を確認できなかった");
            }
            LocalDate session;
            try {
                session = Instant.ofEpochMilli(Long.parseLong(bar.getString("ts_ms")))
                        .atZone(SINGAPORE).toLocalDate();
            } catch (NumberFormatException | DateTimeException error) {
                throw new JSONException("取引日が不正");
            }
            if (session.isAfter(cutoff)) continue;
            double price = bar.optDouble("close");
            if (!Double.isFinite(price) || price <= 0 || sessions.putIfAbsent(session, new Close(session, price)) != null) {
                throw new JSONException("終値が不正か取引日が重複している");
            }
        }
        if (sessions.size() < 2 || sessions.lastKey().isBefore(cutoff.minusDays(7))) {
            throw new JSONException("直近2取引日の終値がそろわなかった");
        }
        return new Pair(sessions.lowerEntry(sessions.lastKey()).getValue(), sessions.lastEntry().getValue());
    }
}
