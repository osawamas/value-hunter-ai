package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.ResolverStyle;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.regex.Pattern;

/** Nasdaq's market-specific official close. Never mix this with a consolidated close. */
final class UsNasdaqOfficialClose {
    private static final Pattern SYMBOL = Pattern.compile("[A-Z0-9.-]{1,24}");
    private static final Pattern PRICE = Pattern.compile("\\$([0-9]{1,12}(?:\\.[0-9]{1,8})?)");
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("MM/dd/uuuu", Locale.ROOT)
            .withResolverStyle(ResolverStyle.STRICT);

    record Pair(BigDecimal before, BigDecimal after) {}

    private UsNasdaqOfficialClose() {}

    static String url(String symbol) {
        return SYMBOL.matcher(symbol).matches()
                ? "https://api.nasdaq.com/api/company/" + symbol + "/historical-nocp?timeframe=d5"
                : null;
    }

    static Pair read(JSONObject root, String symbol, LocalDate previous, LocalDate latest) throws JSONException {
        var status = root.getJSONObject("status");
        if (status.optInt("rCode") != 200 || !status.isNull("bCodeMessage"))
            throw new JSONException("Nasdaq official close unavailable");
        var data = root.getJSONObject("data");
        var headers = data.getJSONObject("headers");
        if (!"Trade Date".equals(headers.optString("date"))
                || !"Nasdaq Closing Price".equals(headers.optString("price")))
            throw new JSONException("Unexpected Nasdaq official close table");
        var nocp = data.getJSONObject("nocp");
        var table = nocp.getJSONArray("nocpTable");
        var chart = nocp.getJSONArray("nocpChart");
        if (table.length() != chart.length() || table.length() > 40)
            throw new JSONException("Incomplete Nasdaq official close data");
        var prices = new HashMap<LocalDate, BigDecimal>();
        try {
            for (int i = 0; i < table.length(); i++) {
                var row = table.getJSONObject(i);
                var day = LocalDate.parse(row.getString("date"), DATE);
                if (prices.putIfAbsent(day, dollar(row.getString("price"))) != null)
                    throw new JSONException("Duplicate Nasdaq official close date");
            }
            var verified = new HashSet<LocalDate>();
            for (int i = 0; i < chart.length(); i++) {
                var point = chart.getJSONObject(i);
                var day = Instant.ofEpochSecond(point.getLong("x")).atZone(ZoneOffset.UTC).toLocalDate();
                var detail = point.getJSONObject("z").getString("details").split(" Close Price: ", -1);
                var price = prices.get(day);
                if (price == null || detail.length != 2 || !symbol.equalsIgnoreCase(detail[0])
                        || price.compareTo(dollar(detail[1])) != 0
                        || price.compareTo(dollar("$" + point.getString("y"))) != 0 || !verified.add(day))
                    throw new JSONException("Nasdaq official close identity or price mismatch");
            }
        } catch (java.time.DateTimeException invalid) {
            throw new JSONException("Invalid Nasdaq official close date");
        }
        var before = prices.get(previous);
        var after = prices.get(latest);
        return before == null || after == null ? null : new Pair(before, after);
    }

    private static BigDecimal dollar(String value) throws JSONException {
        var price = PRICE.matcher(value);
        if (!price.matches()) throw new JSONException("Invalid Nasdaq official close price");
        var amount = new BigDecimal(price.group(1));
        if (amount.signum() <= 0) throw new JSONException("Nonpositive Nasdaq official close price");
        return amount;
    }
}
