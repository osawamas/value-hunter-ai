package jp.valuehunter.privatewatch;

import android.content.Context;

import org.json.JSONArray;

import java.io.IOException;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.BooleanSupplier;

final class JpxAlertOutcomes {
    private JpxAlertOutcomes() {}

    static void record(Context context, int id, String title, String detail, JSONArray codes) {
        var signals = new HashMap<String, String>();
        for (int i = 0; i < codes.length(); i++) {
            String key = codes.optString(i);
            if (key.matches("meter:[1-3]:[0-9][0-9A-Z]{3}")) {
                signals.put(key.substring(8), ValueAlertMeter.LABELS.get(key.charAt(6) - '0'));
            } else if (key.matches("[0-9][0-9A-Z]{3}")) {
                signals.put(key, "従来条件");
            }
        }
        if (!signals.isEmpty()) AlertOutcomes.record(context, AlertOutcomes.Market.JPX, id, title, detail, signals);
    }

    static void update(Context context, LocalDate latestClose, BooleanSupplier stopped) {
        if (latestClose == null || stopped.getAsBoolean()) return;
        var rights = JpxShareRights.cached(context);
        AlertOutcomes.update(context, AlertOutcomes.Market.JPX, latestClose, stopped,
                range -> rights.splitMonthsCovered(range.entry(), range.exit()),
                (range, codes) -> prices(range, codes, rights, stopped,
                        (day, eligible) -> JpxDailyCheck.outcomeReport(context, day, eligible)));
    }

    @FunctionalInterface
    interface Reports {
        JpxDailyCheck.Report load(LocalDate day, Set<String> codes) throws IOException;
    }

    static Map<String, AlertOutcomes.Prices> prices(AlertOutcomes.Window range, Set<String> codes, JpxShareRights rights,
                                                  BooleanSupplier stopped, Reports reports) throws IOException {
        var eligible = new HashSet<>(codes);
        for (var change : rights.adjustments()) {
            if (change.exDay().isAfter(range.entry()) && !change.exDay().isAfter(range.exit())) {
                eligible.remove(change.code());
            }
        }
        if (!eligible.contains(AlertOutcomes.Market.JPX.benchmark) || eligible.size() < 2) return Map.of();
        var entry = reports.load(range.entry(), eligible);
        if (entry == null || stopped.getAsBoolean()) return Map.of();
        var exit = reports.load(range.exit(), eligible);
        if (exit == null || !range.entry().equals(entry.date()) || !range.exit().equals(exit.date())) return Map.of();
        var result = new HashMap<String, AlertOutcomes.Prices>();
        for (String code : eligible) {
            var first = entry.close(code);
            var last = exit.close(code);
            if (first != null && last != null) result.put(code, new AlertOutcomes.Prices(first.doubleValue(), last.doubleValue()));
        }
        return result;
    }
}
