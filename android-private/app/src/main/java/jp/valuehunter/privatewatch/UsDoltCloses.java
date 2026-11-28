package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.SocketTimeoutException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;
import java.util.Map;
import java.util.stream.Collectors;

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
        String manifestQuery = "SELECT DOLT_HASHOF('HEAD') AS revision, COUNT(*) AS n" + filter;
        JSONArray manifest;
        try {
            manifest = query(download, manifestQuery);
        } catch (SocketTimeoutException timeout) {
            manifest = query(download, manifestQuery);
        }
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
        String select = "SELECT act_symbol AS symbol, date AS trading_date, close" + pinnedFilter;
        int pageSize = PAGE_SIZE;
        String lastSymbol = null;
        boolean useCursor = false;
        for (int offset = 0; offset < total;) {
            int expected = Math.min(pageSize, total - offset);
            JSONArray rows;
            try {
                String cursor = useCursor && lastSymbol != null ? " AND act_symbol > '" + lastSymbol + "'" : "";
                String position = useCursor ? "" : " OFFSET " + offset;
                rows = query(download, select + cursor + " ORDER BY act_symbol LIMIT " + pageSize + position);
            } catch (SocketTimeoutException timeout) {
                if (!useCursor && offset > 0 && total - offset <= PAGE_SIZE) {
                    try {
                        rows = recoverLastPage(download, select, closes, day, expected);
                    } catch (SocketTimeoutException reverseTimeout) {
                        useCursor = true;
                        pageSize = PAGE_SIZE / 2;
                        continue;
                    }
                } else {
                    if (pageSize <= 125) throw timeout;
                    useCursor = true;
                    pageSize /= 2;
                    continue;
                }
            }
            if (rows.length() != expected) {
                throw new JSONException("Incomplete Dolt close page");
            }
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.getJSONObject(i);
                String symbol = row.getString("symbol");
                double price = row.getDouble("close");
                if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || !seen.add(symbol)
                        || (useCursor && lastSymbol != null && symbol.compareTo(lastSymbol) <= 0)
                        || !day.toString().equals(row.getString("trading_date"))
                        || !Double.isFinite(price) || price <= 0) {
                    throw new JSONException("Invalid or duplicate Dolt close");
                }
                closes.put(new JSONObject().put("symbol", symbol).put("close_usd", price));
                lastSymbol = symbol;
            }
            offset += rows.length();
        }
        return closes;
    }

    record ScopedCloses(JSONArray rows, int queriedSymbols, boolean timedOut) {}

    static ScopedCloses fetchScoped(LocalDate day, Set<String> scope, Download download)
            throws IOException, JSONException {
        if (scope.isEmpty() || scope.size() > 12_000) throw new JSONException("Invalid Dolt listing scope");
        var manifest = query(download, "SELECT DOLT_HASHOF('HEAD') AS revision");
        if (manifest.length() != 1) throw new JSONException("Unexpected Dolt revision response");
        String revision = manifest.getJSONObject(0).getString("revision");
        if (!revision.matches("[0-9a-v]{32}")) throw new JSONException("Invalid Dolt revision");
        var symbols = new java.util.ArrayList<>(new java.util.TreeSet<>(scope));
        var all = new JSONArray();
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.MINUTES.toNanos(2);
        for (int offset = 0; offset < symbols.size(); offset += 100) {
            if (System.nanoTime() - deadline >= 0) return new ScopedCloses(all, offset, true);
            int end = Math.min(offset + 100, symbols.size());
            try {
                var rows = supplement(day, Set.copyOf(symbols.subList(offset, end)), revision, download);
                for (int i = 0; i < rows.length(); i++) all.put(rows.getJSONObject(i));
            } catch (SocketTimeoutException timedOut) {
                return new ScopedCloses(all, offset, true);
            }
        }
        return new ScopedCloses(all, symbols.size(), false);
    }

    static JSONArray supplement(LocalDate day, Set<String> symbols, Download download)
            throws IOException, JSONException {
        return supplement(day, symbols, "", download);
    }

    private static JSONArray supplement(LocalDate day, Set<String> symbols, String revision, Download download)
            throws IOException, JSONException {
        if (symbols.isEmpty() || symbols.size() > 100) throw new JSONException("Invalid quote repair size");
        var codes = new java.util.ArrayList<String>();
        for (String symbol : new java.util.TreeSet<>(symbols)) {
            if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}")) throw new JSONException("Invalid quote repair ticker");
            codes.add("'" + symbol + "'");
        }
        String asOf = revision.isEmpty() ? "" : " AS OF '" + revision + "'";
        var rows = query(download, "SELECT act_symbol AS symbol, date AS trading_date, close FROM ohlcv" + asOf
                + " WHERE date = '" + day + "' AND close > 0 AND act_symbol IN (" + String.join(",", codes) + ")");
        var closes = new JSONArray();
        var remaining = new HashSet<>(symbols);
        for (int index = 0; index < rows.length(); index++) {
            var row = rows.getJSONObject(index);
            String symbol = row.getString("symbol");
            double close = row.getDouble("close");
            if (!remaining.remove(symbol) || !day.toString().equals(row.getString("trading_date"))
                    || !Double.isFinite(close) || close <= 0) throw new JSONException("Invalid quote repair response");
            closes.put(new JSONObject().put("symbol", symbol).put("close_usd", close));
        }
        return closes;
    }

    private static JSONArray recoverLastPage(Download download, String select, JSONArray previous,
                                              LocalDate day, int remaining) throws IOException, JSONException {
        // Read the suffix without a large OFFSET. Match the overlap with the already validated pages.
        var reverse = query(download, select + " ORDER BY act_symbol DESC LIMIT " + PAGE_SIZE);
        if (reverse.length() != PAGE_SIZE) throw new JSONException("Incomplete reverse Dolt close page");
        int overlap = PAGE_SIZE - remaining;
        for (int i = 0; i < overlap; i++) {
            var recovered = reverse.getJSONObject(PAGE_SIZE - 1 - i);
            var original = previous.getJSONObject(previous.length() - overlap + i);
            if (!day.toString().equals(recovered.getString("trading_date"))
                    || !original.getString("symbol").equals(recovered.getString("symbol"))
                    || original.getDouble("close_usd") != recovered.getDouble("close")) {
                throw new JSONException("Dolt reverse close page does not match the pinned prefix");
            }
        }
        var suffix = new JSONArray();
        String last = previous.getJSONObject(previous.length() - 1).getString("symbol");
        for (int i = remaining - 1; i >= 0; i--) {
            var row = reverse.getJSONObject(i);
            var symbol = row.getString("symbol");
            if (symbol.compareTo(last) <= 0) throw new JSONException("Unordered Dolt close suffix");
            suffix.put(row);
            last = symbol;
        }
        return suffix;
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

    static Map<String, LocalDate> allSplits(LocalDate from, LocalDate to, Download download)
            throws IOException, JSONException {
        var manifest = query(download, "SELECT DOLT_HASHOF('HEAD') AS revision");
        if (manifest.length() != 1) throw new JSONException("Missing split revision");
        String revision = manifest.getJSONObject(0).getString("revision");
        if (!revision.matches("[0-9a-v]{32}")) throw new JSONException("Invalid split revision");
        var dates = new HashMap<String, LocalDate>();
        for (int offset = 0; offset < 12_000; offset += PAGE_SIZE) {
            var rows = query(download, "SELECT act_symbol AS symbol, CAST(MAX(ex_date) AS CHAR) AS split_date"
                    + " FROM split AS OF '" + revision + "' WHERE ex_date BETWEEN '" + from + "' AND '" + to + "'"
                    + " GROUP BY act_symbol ORDER BY act_symbol LIMIT " + PAGE_SIZE
                    + (offset == 0 ? "" : " OFFSET " + offset));
            if (rows.length() > PAGE_SIZE) throw new JSONException("Oversized split result");
            for (int index = 0; index < rows.length(); index++) {
                var row = rows.getJSONObject(index);
                var symbol = row.getString("symbol");
                try {
                    var date = LocalDate.parse(row.getString("split_date"));
                    if (!symbol.matches("[A-Z0-9.$+^=/_-]{1,24}") || date.isBefore(from) || date.isAfter(to)
                            || dates.put(symbol, date) != null) throw new JSONException("Invalid split page");
                } catch (DateTimeParseException invalid) {
                    throw new JSONException("Invalid split date");
                }
            }
            if (rows.length() < PAGE_SIZE) return dates;
        }
        throw new JSONException("Incomplete split result");
    }

    static JSONArray monthlyRows(YearMonth first, Download download) throws IOException, JSONException {
        String dates = UsMonthlyHistory.monthEndDates(first, 12).stream()
                .map(day -> "'" + day + "'").collect(Collectors.joining(",", "(", ")"));
        return query(download, "SELECT act_symbol AS symbol, date AS trading_date, close FROM ohlcv"
                + " WHERE date IN " + dates + " AND act_symbol IN " + UsDailyValuation.pilotSymbolsSql()
                + " AND close > 0 ORDER BY act_symbol,date");
    }

    static Map<String, AlertOutcomes.Prices> outcomePrices(AlertOutcomes.Window window, Set<String> symbols,
                                                          Download download) throws IOException, JSONException {
        if (symbols.isEmpty() || symbols.size() > AlertOutcomes.MAX_BATCH
                || !symbols.stream().allMatch(AlertOutcomes::validSymbol)) throw new JSONException("Invalid comparison symbols");
        String in = new java.util.TreeSet<>(symbols).stream().map(symbol -> "'" + symbol + "'")
                .collect(Collectors.joining(",", "(", ")"));
        String entry = window.entry().toString();
        String exit = window.exit().toString();
        var rows = query(download, "SELECT q.act_symbol AS symbol, q.date AS trading_date, q.close FROM ohlcv q"
                + " WHERE q.date IN ('" + entry + "','" + exit + "') AND q.act_symbol IN " + in
                + " AND q.close > 0 AND NOT EXISTS (SELECT 1 FROM split s WHERE s.act_symbol = q.act_symbol"
                + " AND s.ex_date > '" + entry + "' AND s.ex_date <= '" + exit + "')");
        if (rows.length() > 2 * symbols.size()) throw new JSONException("Oversized comparison result");
        var starts = new HashMap<String, Double>();
        var ends = new HashMap<String, Double>();
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            String symbol = row.getString("symbol");
            String date = row.getString("trading_date");
            double close = row.getDouble("close");
            if (!symbols.contains(symbol) || (!entry.equals(date) && !exit.equals(date))
                    || !Double.isFinite(close) || close <= 0
                    || (entry.equals(date) ? starts : ends).put(symbol, close) != null) {
                throw new JSONException("Invalid comparison close");
            }
        }
        var result = new HashMap<String, AlertOutcomes.Prices>();
        starts.forEach((symbol, close) -> {
            Double end = ends.get(symbol);
            if (end != null) result.put(symbol, new AlertOutcomes.Prices(close, end));
        });
        return result;
    }

    private static JSONArray query(Download download, String sql)
            throws IOException, JSONException {
        var data = download.get(URL + "?q=" + URLEncoder.encode(sql, StandardCharsets.UTF_8.name()));
        if (!"Success".equals(data.optString("query_execution_status"))) {
            if ("Timeout".equals(data.optString("query_execution_status"))) {
                throw new SocketTimeoutException("Dolt close query timed out");
            }
            throw new JSONException("Dolt close query did not succeed");
        }
        return data.getJSONArray("rows");
    }
}
