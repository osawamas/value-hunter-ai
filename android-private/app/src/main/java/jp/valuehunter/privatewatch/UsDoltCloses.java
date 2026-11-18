package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;

final class UsDoltCloses {
    static final String SOURCE = "dolthub-post-no-preference-stocks";
    private static final String URL =
            "https://www.dolthub.com/api/v1alpha1/post-no-preference/stocks";
    private static final int PAGE_SIZE = 1000;

    interface Download {
        JSONObject get(String address) throws IOException, JSONException;
    }

    static JSONArray fetch(LocalDate day, Download download) throws IOException, JSONException {
        String filter = " FROM ohlcv WHERE date = '" + day + "' AND close > 0";
        JSONArray manifest = query(download, "SELECT DOLT_HASHOF('HEAD') AS revision, COUNT(*) AS n" + filter);
        if (manifest.length() != 1) {
            throw new JSONException("Unexpected Dolt close manifest");
        }
        JSONObject summary = manifest.getJSONObject(0);
        String revision = summary.getString("revision");
        String countText = summary.getString("n");
        if (!revision.matches("[0-9a-v]{32}") || !countText.matches("[0-9]{1,5}")) {
            throw new JSONException("Invalid Dolt revision or row count");
        }
        int total = Integer.parseInt(countText);
        if (total > 50_000) throw new JSONException("Dolt close manifest exceeds the row limit");

        String pinnedFilter = " FROM ohlcv AS OF '" + revision + "' WHERE date = '" + day + "' AND close > 0";
        var closes = new JSONArray();
        var seen = new HashSet<String>();
        for (int offset = 0; offset < total; offset += PAGE_SIZE) {
            JSONArray rows = query(download, "SELECT act_symbol AS symbol, date AS trading_date, close"
                    + pinnedFilter + " ORDER BY act_symbol LIMIT " + PAGE_SIZE + " OFFSET " + offset);
            if (rows.length() != Math.min(PAGE_SIZE, total - offset)) {
                throw new JSONException("Incomplete Dolt close page");
            }
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.getJSONObject(i);
                String symbol = row.getString("symbol");
                double price = row.getDouble("close");
                if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || !seen.add(symbol)
                        || !day.toString().equals(row.getString("trading_date"))
                        || !Double.isFinite(price) || price <= 0) {
                    throw new JSONException("Invalid or duplicate Dolt close");
                }
                closes.put(new JSONObject().put("symbol", symbol).put("close_usd", price));
            }
        }
        return closes;
    }

    static Map<String, LocalDate> pilotSplits(LocalDate from, LocalDate to, Download download)
            throws IOException, JSONException {
        var rows = query(download, "SELECT act_symbol AS symbol, CAST(MAX(ex_date) AS CHAR) AS split_date"
                + " FROM split WHERE ex_date BETWEEN '" + from + "' AND '" + to + "'"
                + " AND act_symbol IN " + UsDailyValuation.pilotSymbolsSql() + " GROUP BY act_symbol");
        var dates = new HashMap<String, LocalDate>();
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            try {
                var date = LocalDate.parse(row.getString("split_date"));
                if (date.isBefore(from) || date.isAfter(to) || dates.put(row.getString("symbol"), date) != null) {
                    throw new JSONException("Unexpected split records");
                }
            } catch (DateTimeParseException e) {
                throw new JSONException("Invalid split date");
            }
        }
        return dates;
    }

    private static JSONArray query(Download download, String sql)
            throws IOException, JSONException {
        var data = download.get(URL + "?q=" + URLEncoder.encode(sql, StandardCharsets.UTF_8.name()));
        if (!"Success".equals(data.optString("query_execution_status"))) {
            if ("Timeout".equals(data.optString("query_execution_status"))) {
                throw new IOException("Dolt close query timed out");
            }
            throw new JSONException("Dolt close query did not succeed");
        }
        return data.getJSONArray("rows");
    }
}
