package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

final class ValueAlertPreview {
    static final String SETTINGS = "value_alert_thresholds";

    enum Market {
        JPX("東証", "value_alert_preview_jpx"), US("米国株", "value_alert_preview_us");
        final String label;
        final String key;
        Market(String label, String key) {
            this.label = label;
            this.key = key;
        }
        LocalDate expectedPrior(LocalDate day) {
            return this == JPX ? JpxTradingDays.onOrBefore(day.minusDays(1)) : UsPriceOnlyBudget.previousSession(day);
        }
    }

    record Row(ValueAlertMeter.Score score, int shares) {}
    record Session(LocalDate day, String source, Map<String, Row> rows) {}
    record History(Session latest, Session previous) {}

    static void save(SharedPreferences state, SharedPreferences.Editor edit, Market market,
                     LocalDate day, String source, JSONObject rows) throws JSONException {
        var saved = read(state, market);
        var latest = saved.optJSONObject("latest");
        var version = new JSONObject().put("day", day.toString()).put("source", source).put("rows", rows);
        if (latest != null) {
            String oldDay = latest.optString("day");
            if (oldDay.compareTo(day.toString()) > 0) return;
            if (oldDay.compareTo(day.toString()) < 0) saved.put("previous", latest);
        }
        edit.putString(market.key, saved.put("latest", version).toString());
    }

    static JSONArray encode(ValueAlertMeter.Score score, int shares) {
        return new JSONArray().put(score.points()).put(score.ceiling()).put(score.confirmed()).put(shares);
    }

    static History history(SharedPreferences state, Market market) {
        var snapshot = read(state, market);
        return new History(decode(snapshot.optJSONObject("latest")), decode(snapshot.optJSONObject("previous")));
    }

    static String summary(Market market, History history, ValueAlertMeter.Thresholds thresholds) {
        var latest = history.latest();
        if (latest == null || latest.rows().isEmpty()) return market.label + " · 財務付きの判定データ待ち";
        var previous = history.previous();
        boolean comparable = previous != null && latest.source().equals(previous.source())
                && previous.day().equals(market.expectedPrior(latest.day()));
        int[][] current = new int[2][4];
        int[][] changes = new int[2][4];
        int comparableRows = 0;
        for (var entry : latest.rows().entrySet()) {
            var row = entry.getValue();
            if (row.shares() == 0) continue;
            int lot = row.shares() == 100 ? 0 : 1;
            current[lot][row.score().level(thresholds)]++;
            var prior = comparable ? previous.rows().get(entry.getKey()) : null;
            if (prior != null) {
                comparableRows++;
                var priorScore = prior.shares() == 0 ? new ValueAlertMeter.Score(0, 0, 0) : prior.score();
                changes[lot][ValueAlertMeter.promotion(priorScore, row.score(), thresholds)]++;
            }
        }
        var text = new StringBuilder(market.label).append(" · ").append(latest.day())
                .append("\n100株枠 ").append(counts(current[0]))
                .append("\n1株枠（参考） ").append(counts(current[1]));
        if (!comparable || comparableRows == 0) return text.append("\n新規・昇格の試算は前取引日の照合待ち").toString();
        return text.append("\n新規・昇格の試算（比較可能 ").append(comparableRows).append("銘柄）")
                .append("\n100株枠 ").append(counts(changes[0]))
                .append("\n1株枠（参考） ").append(counts(changes[1])).toString();
    }

    private static String counts(int[] levels) {
        return "割安 " + levels[1] + " · かなり割安 " + levels[2] + " · 超割安 " + levels[3];
    }

    private static JSONObject read(SharedPreferences state, Market market) {
        try {
            return new JSONObject(state.getString(market.key, "{}"));
        } catch (JSONException invalid) {
            return new JSONObject();
        }
    }

    private static Session decode(JSONObject object) {
        if (object == null) return null;
        try {
            var day = LocalDate.parse(object.getString("day"));
            var source = object.getString("source");
            var data = object.getJSONObject("rows");
            var rows = new HashMap<String, Row>();
            var keys = data.keys();
            while (keys.hasNext()) {
                var key = keys.next();
                var values = data.optJSONArray(key);
                if (values == null || values.length() != 4) continue;
                int points = values.optInt(0, -1);
                int cap = values.optInt(1, -1);
                int confirmed = values.optInt(2, -1);
                int shares = values.optInt(3, -1);
                if (points < 0 || points > 100 || cap < 0 || cap > 3 || confirmed < 0 || confirmed > 6
                        || (shares != 0 && shares != 1 && shares != 100)) continue;
                rows.put(key, new Row(new ValueAlertMeter.Score(points, cap, confirmed), shares));
            }
            return new Session(day, source, Map.copyOf(rows));
        } catch (JSONException | java.time.DateTimeException invalid) {
            return null;
        }
    }
}
