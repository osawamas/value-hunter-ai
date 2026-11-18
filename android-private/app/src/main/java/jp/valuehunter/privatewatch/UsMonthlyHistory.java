package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

final class UsMonthlyHistory {
    static final int MONTHS = 60;

    // Restrict Dolt's date-first index to the last three weekdays of each month.
    static Set<LocalDate> monthEndDates(YearMonth start, int months) {
        var dates = new TreeSet<LocalDate>();
        for (int offset = 0; offset < months; offset++) {
            LocalDate day = start.plusMonths(offset).atEndOfMonth();
            int weekdays = 0;
            while (weekdays != 3) {
                if (day.getDayOfWeek() != DayOfWeek.SATURDAY && day.getDayOfWeek() != DayOfWeek.SUNDAY) {
                    dates.add(day);
                    weekdays++;
                }
                day = day.minusDays(1);
            }
        }
        return dates;
    }

    private record Close(LocalDate date, double price) {}

    static String summarize(List<JSONArray> batches, YearMonth first, Map<String, LocalDate> splits,
                            Set<String> symbols) throws JSONException {
        var selectedDays = monthEndDates(first, MONTHS);
        var bySymbol = new HashMap<String, TreeMap<YearMonth, Close>>();
        var seen = new HashMap<String, Set<LocalDate>>();
        for (var batch : batches) {
            for (int i = 0; i < batch.length(); i++) {
                var row = batch.getJSONObject(i);
                String symbol = row.getString("symbol");
                LocalDate date;
                try {
                    date = LocalDate.parse(row.getString("trading_date"));
                } catch (DateTimeParseException e) {
                    throw new JSONException("Invalid monthly close date");
                }
                double price = row.getDouble("close");
                if (!symbols.contains(symbol) || !selectedDays.contains(date)
                        || !Double.isFinite(price) || price <= 0
                        || !seen.computeIfAbsent(symbol, key -> new TreeSet<>()).add(date)) {
                    throw new JSONException("Unexpected or duplicate monthly close");
                }
                var monthly = bySymbol.computeIfAbsent(symbol, key -> new TreeMap<>());
                var month = YearMonth.from(date);
                var previous = monthly.get(month);
                if (previous == null || date.isAfter(previous.date)) monthly.put(month, new Close(date, price));
            }
        }

        var text = new ArrayList<String>();
        for (String symbol : symbols) {
            var history = bySymbol.get(symbol);
            int count = history == null ? 0 : history.size();
            if (splits.containsKey(symbol)) {
                text.add(symbol + " · 株式分割の調整を確認するまで保留");
            } else if (count != MONTHS) {
                text.add(symbol + " · " + count + "/" + MONTHS + "か月。範囲は保留");
            } else {
                var summary = history.values().stream().mapToDouble(Close::price).summaryStatistics();
                text.add(String.format(Locale.JAPAN, "%s · %.2f〜%.2f USD",
                        symbol, summary.getMin(), summary.getMax()));
            }
        }
        return "過去5年の月末近くの終値（DoltHub参考値）\n" + first + "〜" + first.plusMonths(MONTHS - 1)
                + "\n" + String.join("\n", text);
    }
}
