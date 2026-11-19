package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/** Checks candidate closes against Nasdaq's public history, which can be split-adjusted. */
final class UsNasdaqCloseCheck {
    private static final Pattern SYMBOL = Pattern.compile("[A-Z0-9.-]{1,24}");
    private static final Pattern EVENT_SYMBOL = Pattern.compile("[A-Z0-9.$+^=/_-]{1,24}");
    private static final Pattern SHARE_CLASS = Pattern.compile("([A-Z0-9]+)[.-]([A-Z])");
    private static final Pattern PRICE = Pattern.compile("\\$([0-9]{1,12}(?:\\.[0-9]{1,8})?)");
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("MM/dd/uuuu", Locale.ROOT)
            .withResolverStyle(ResolverStyle.STRICT);

    private static final DateTimeFormatter AS_OF = DateTimeFormatter.ofPattern("EEE, MMM d, uuuu", Locale.US)
            .withResolverStyle(ResolverStyle.STRICT);

    private UsNasdaqCloseCheck() {}

    static String splitCalendarUrl(LocalDate from) {
        return "https://api.nasdaq.com/api/calendar/splits?date=" + from;
    }

    static Set<String> splits(JSONObject response, LocalDate from, LocalDate through) throws JSONException {
        var status = response.optJSONObject("status");
        var data = response.optJSONObject("data");
        if (status == null || status.optInt("rCode") != 200 || data == null || from.isAfter(through)) {
            throw new JSONException("Nasdaq split calendar unavailable");
        }
        var rows = data.optJSONArray("rows");
        var headers = data.optJSONObject("headers");
        if (rows == null || rows.length() > 5000 || headers == null
                || !headers.has("symbol") || !headers.has("executionDate")) {
            throw new JSONException("Unexpected Nasdaq split calendar");
        }
        var symbols = new HashSet<String>();
        try {
            if (!LocalDate.parse(data.getString("asOf"), AS_OF).equals(through)) {
                throw new JSONException("Nasdaq split calendar date differs from the check date");
            }
            for (int i = 0; i < rows.length(); i++) {
                var row = rows.getJSONObject(i);
                var day = LocalDate.parse(row.getString("executionDate"), DATE);
                String symbol = row.getString("symbol");
                if (day.isBefore(from) || !EVENT_SYMBOL.matcher(symbol).matches()) {
                    throw new JSONException("Invalid Nasdaq split calendar row");
                }
                if (!day.isAfter(through)) symbols.add(symbol);
            }
        } catch (DateTimeParseException invalid) {
            throw new JSONException("Invalid Nasdaq split calendar date");
        }
        return symbols;
    }

    static boolean hasSplit(Set<String> symbols, String ticker) {
        if (symbols.contains(ticker)) return true;
        var shareClass = SHARE_CLASS.matcher(ticker);
        if (!shareClass.matches()) return false;
        String separator = ticker.contains(".") ? "-" : ".";
        return symbols.contains(shareClass.group(1) + separator + shareClass.group(2));
    }

    static String url(String symbol, LocalDate previousDay, LocalDate day) {
        if (!SYMBOL.matcher(symbol).matches()) return null;
        return "https://api.nasdaq.com/api/quote/" + symbol + "/historical?assetclass=stocks"
                + "&fromdate=" + previousDay + "&todate=" + day + "&limit=8";
    }

    static boolean matches(JSONObject response, String symbol, LocalDate previousDay, BigDecimal previousClose,
                           LocalDate day, BigDecimal close) throws JSONException {
        var status = response.optJSONObject("status");
        var data = response.optJSONObject("data");
        if (status == null || status.optInt("rCode") != 200 || data == null
                || !symbol.equals(data.optString("symbol")) || data.optInt("totalRecords") != 2
                || previousClose == null || close == null) return false;
        var table = data.optJSONObject("tradesTable");
        var rows = table == null ? null : table.optJSONArray("rows");
        if (rows == null || rows.length() != 2) return false;
        boolean previousMatched = false;
        boolean latestMatched = false;
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            LocalDate found;
            try {
                found = LocalDate.parse(row.getString("date"), DATE);
            } catch (DateTimeParseException invalid) {
                return false;
            }
            var money = PRICE.matcher(row.getString("close"));
            if (!money.matches()) return false;
            var price = new BigDecimal(money.group(1));
            if (price.signum() <= 0) return false;
            if (found.equals(previousDay) && !previousMatched && price.compareTo(previousClose) == 0) {
                previousMatched = true;
            } else if (found.equals(day) && !latestMatched && price.compareTo(close) == 0) {
                latestMatched = true;
            } else {
                return false;
            }
        }
        return previousMatched && latestMatched;
    }
}
