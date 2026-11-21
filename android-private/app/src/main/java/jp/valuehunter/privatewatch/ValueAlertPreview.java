package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Set;
import java.util.function.Function;
import java.util.Map;

final class ValueAlertPreview {
    static final String SETTINGS = "value_alert_thresholds";
    static final String LIVE = "value_alert_live";

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
    record Entry(String code, int shares, int level, int points) {
        String key() { return receiptKey(code, level); }
        String summary() {
            return code + " · " + shares + "株 · " + ValueAlertMeter.LABELS.get(level) + " · " + points + "点";
        }
    }

    private static String receiptKey(String code, int level) { return "meter:" + level + ":" + code; }

    static Map<String, Entry> entries(SharedPreferences state, Market market, LocalDate day, String source,
                                      JSONObject rows, Set<String> sent, Function<String, String> verifiedCode) throws JSONException {
        var history = history(state, market);
        var prior = history.latest();
        if (prior != null && day.equals(prior.day())) prior = history.previous();
        return entries(state, market, day, source, rows, prior, sent, verifiedCode);
    }

    static Map<String, Entry> entries(SharedPreferences state, Market market, LocalDate day, String source,
                                      JSONObject rows, Session prior, Set<String> sent,
                                      Function<String, String> verifiedCode) throws JSONException {
        if (prior == null || !source.equals(prior.source()) || !market.expectedPrior(day).equals(prior.day())) {
            return Map.of();
        }
        var current = session(day, source, rows);
        if (current == null) return Map.of();
        var thresholds = ValueAlertMeter.Thresholds.read(state.getString(SETTINGS, ""));
        var entries = new java.util.ArrayList<Entry>();
        for (var candidate : current.rows().entrySet()) {
            var identity = candidate.getKey();
            var row = candidate.getValue();
            var before = prior.rows().get(identity);
            if (before == null || row.shares() == 0) continue;
            // Match the stored identity across sessions before choosing the notification symbol.
            String code = verifiedCode.apply(identity);
            if (code == null) continue;
            int level = promotion(before, row, thresholds);
            if (level == 0 || sent.contains(code)) continue;
            boolean alreadySent = false;
            for (int rank = level; rank <= 3; rank++) alreadySent |= sent.contains(receiptKey(code, rank));
            if (!alreadySent) entries.add(new Entry(code, row.shares(), level, row.score().points()));
        }
        entries.sort(java.util.Comparator.comparingInt(Entry::shares).reversed()
                .thenComparing(java.util.Comparator.comparingInt(Entry::level).reversed()).thenComparing(Entry::code));
        var ordered = new LinkedHashMap<String, Entry>();
        for (var entry : entries) ordered.put(entry.key(), entry);
        return ordered;
    }

    static Set<String> previouslyNotified(Set<String> sent) {
        var codes = new java.util.HashSet<>(sent);
        for (var key : sent) {
            if (key.startsWith("meter:") && key.length() > 8) codes.add(key.substring(8));
        }
        return codes;
    }

    static String title(String market, Map<String, Entry> entries) {
        int strongest = entries.values().stream().mapToInt(Entry::level).max().orElseThrow();
        return market + " · " + ValueAlertMeter.LABELS.get(strongest)
                + " · 割安度の新規・昇格 " + entries.size() + "銘柄";
    }

    private static int promotion(Row prior, Row current, ValueAlertMeter.Thresholds thresholds) {
        var priorScore = prior.shares() == 0 ? new ValueAlertMeter.Score(0, 0, 0) : prior.score();
        return ValueAlertMeter.promotion(priorScore, current.score(), thresholds);
    }

    static void save(SharedPreferences state, SharedPreferences.Editor edit, Market market,
                     LocalDate day, String source, JSONObject rows) throws JSONException {
        save(state, edit, market, day, source, rows, null);
    }

    static void save(SharedPreferences state, SharedPreferences.Editor edit, Market market, LocalDate day,
                     String source, JSONObject rows, JSONObject verifiedPriorRows) throws JSONException {
        var saved = read(state, market);
        var latest = saved.optJSONObject("latest");
        var version = snapshot(day, source, rows);
        if (latest != null) {
            try {
                LocalDate oldDay = LocalDate.parse(latest.getString("day"));
                if (latest.getString("source").isBlank()) throw new JSONException("Missing meter source");
                latest.getJSONObject("rows");
                if (oldDay.isAfter(day)) return;
                if (oldDay.isBefore(day)) saved.put("previous", latest);
            } catch (JSONException | java.time.DateTimeException invalid) {
                // Replace invalid metadata while retaining any separately stored previous session.
            }
        }
        if (verifiedPriorRows != null) {
            saved.put("previous", snapshot(market.expectedPrior(day), source, verifiedPriorRows));
        }
        edit.putString(market.key, saved.put("latest", version).toString());
    }

    static Session session(LocalDate day, String source, JSONObject rows) throws JSONException {
        return decode(snapshot(day, source, rows));
    }

    private static JSONObject snapshot(LocalDate day, String source, JSONObject rows) throws JSONException {
        return new JSONObject().put("day", day.toString()).put("source", source).put("rows", rows);
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
                changes[lot][promotion(prior, row, thresholds)]++;
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
