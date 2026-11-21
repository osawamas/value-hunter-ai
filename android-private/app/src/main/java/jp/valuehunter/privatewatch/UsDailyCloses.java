package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

final class UsDailyCloses {
    static final ZoneId NEW_YORK = ZoneId.of("America/New_York");
    static final String MASSIVE_SOURCE = "massive-grouped-daily";
    static final int MAX_BYTES = 16 * 1024 * 1024;

    // Scheduled full-day closures for NYSE and Nasdaq. Early closes are trading days.
    // https://www.nyse.com/trade/hours-calendars
    // https://www.nasdaqtrader.com/Trader.aspx?id=Calendar
    private static final Set<LocalDate> HOLIDAYS = Set.of(
            LocalDate.of(2026, 1, 1), LocalDate.of(2026, 1, 19), LocalDate.of(2026, 2, 16),
            LocalDate.of(2026, 4, 3), LocalDate.of(2026, 5, 25), LocalDate.of(2026, 6, 19),
            LocalDate.of(2026, 7, 3), LocalDate.of(2026, 9, 7), LocalDate.of(2026, 11, 26),
            LocalDate.of(2026, 12, 25),
            LocalDate.of(2027, 1, 1), LocalDate.of(2027, 1, 18), LocalDate.of(2027, 2, 15),
            LocalDate.of(2027, 3, 26), LocalDate.of(2027, 5, 31), LocalDate.of(2027, 6, 18),
            LocalDate.of(2027, 7, 5), LocalDate.of(2027, 9, 6), LocalDate.of(2027, 11, 25),
            LocalDate.of(2027, 12, 24),
            LocalDate.of(2028, 1, 17), LocalDate.of(2028, 2, 21), LocalDate.of(2028, 4, 14),
            LocalDate.of(2028, 5, 29), LocalDate.of(2028, 6, 19), LocalDate.of(2028, 7, 4),
            LocalDate.of(2028, 9, 4), LocalDate.of(2028, 11, 23), LocalDate.of(2028, 12, 25));

    static boolean tradingDay(LocalDate day) {
        return day.getDayOfWeek() != DayOfWeek.SATURDAY && day.getDayOfWeek() != DayOfWeek.SUNDAY
                && !HOLIDAYS.contains(day);
    }

    static LocalDate onOrBeforeTradingDay(LocalDate day) {
        while (!tradingDay(day)) day = day.minusDays(1);
        return day;
    }

    static LocalDate mostRecentEligibleDay(Instant now) {
        return now.atZone(NEW_YORK).toLocalDate().minusDays(1);
    }

    static JSONArray parse(JSONObject payload, LocalDate day) throws JSONException {
        if (!"OK".equals(payload.optString("status"))
                || !Boolean.FALSE.equals(payload.opt("adjusted"))) {
            throw new JSONException("Expected an unadjusted daily summary");
        }
        Object count = payload.opt("resultsCount");
        JSONArray rows = payload.optJSONArray("results");
        if (rows == null && !payload.has("results") && Integer.valueOf(0).equals(count)) {
            return new JSONArray();
        }
        if (rows == null || !(count instanceof Number)
                || ((Number) count).doubleValue() != rows.length() || rows.length() > 50_000) {
            throw new JSONException("Unexpected daily summary row count");
        }
        var seen = new HashSet<String>();
        var closes = new JSONArray();
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.getJSONObject(i);
            String symbol = row.getString("T").toUpperCase(Locale.ROOT);
            Object close = row.opt("c");
            Object timestamp = row.opt("t");
            if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || !seen.add(symbol)
                    || !(timestamp instanceof Number)) {
                throw new JSONException("Invalid or duplicate daily bar");
            }
            long millis = ((Number) timestamp).longValue();
            if (((Number) timestamp).doubleValue() != millis
                    || !Instant.ofEpochMilli(millis).atZone(NEW_YORK).toLocalDate().equals(day)) {
                throw new JSONException("Bar date differs from the requested New York date");
            }
            if (!Boolean.TRUE.equals(row.opt("otc")) && close instanceof Number) {
                double price = ((Number) close).doubleValue();
                if (Double.isFinite(price) && price > 0) {
                    closes.put(new JSONObject().put("symbol", symbol).put("close_usd", close));
                }
            }
        }
        if (rows.length() > 0 && closes.length() == 0) {
            throw new JSONException("Daily summary contains no usable closes");
        }
        return closes;
    }
}
