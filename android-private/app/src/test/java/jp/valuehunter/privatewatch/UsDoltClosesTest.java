package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.net.SocketTimeoutException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

public class UsDoltClosesTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);
    private static final String REVISION = "0123456789abcdefghijklmnopqrstuv";

    @Test public void scopedFallbackPinsRevisionAndQueriesEveryListingBatch() throws Exception {
        var calls = new AtomicInteger();
        var scope = new java.util.TreeSet<String>();
        for (int i = 0; i <= 100; i++) scope.add(String.format(java.util.Locale.ROOT, "S%03d", i));
        var closes = UsDoltCloses.fetchScoped(DAY, scope, address -> {
            int call = calls.getAndIncrement();
            String query = URLDecoder.decode(address, StandardCharsets.UTF_8);
            if (call == 0) {
                assertTrue(query.endsWith("SELECT DOLT_HASHOF('HEAD') AS revision"));
                return response(new JSONArray().put(new JSONObject().put("revision", REVISION)));
            }
            assertTrue(query.contains("ohlcv AS OF '" + REVISION + "'"));
            assertTrue(query.contains("date = '" + DAY + "'"));
            if (call == 1) assertTrue(query.contains("'S000'") && query.contains("'S099'"));
            else assertTrue(query.endsWith("IN ('S100')"));
            return response(new JSONArray().put(row(call == 1 ? "S099" : "S100", DAY)));
        });
        assertEquals(3, calls.get());
        assertEquals(2, closes.length());
    }

    @Test public void readsAllPagesAtThePinnedRevision() throws Exception {
        var calls = new AtomicInteger();
        var closes = UsDoltCloses.fetch(DAY, address -> {
            int call = calls.getAndIncrement();
            String query = URLDecoder.decode(address, StandardCharsets.UTF_8.name());
            assertTrue(query.contains("date = '2026-11-17'"));
            if (call == 0) return manifest(1001);
            assertTrue(query.contains("ohlcv AS OF '" + REVISION + "'"));
            if (call == 2) {
                assertTrue(query.endsWith("LIMIT 1000 OFFSET 1000"));
                return response(new JSONArray().put(row("LAST", DAY)));
            }
            assertTrue(query.endsWith("LIMIT 1000 OFFSET 0"));
            var rows = new JSONArray();
            for (int i = 0; i < 1000; i++) rows.put(row("T" + i, DAY));
            return response(rows);
        });
        assertEquals(3, calls.get());
        assertEquals(1001, closes.length());
        assertEquals("LAST", closes.getJSONObject(1000).getString("symbol"));
    }

    @Test public void recoversATimedOutLastPageFromAnOverlappingPinnedSuffix() throws Exception {
        var calls = new AtomicInteger();
        var closes = UsDoltCloses.fetch(DAY, address -> recoveryResponse(address, calls, false));
        assertEquals(4, calls.get());
        assertEquals(1002, closes.length());
        assertEquals("T1000", closes.getJSONObject(1000).getString("symbol"));
        assertEquals("T1001", closes.getJSONObject(1001).getString("symbol"));
    }

    @Test public void retriesAnEarlyTimeoutWithSmallerPinnedCursorPages() throws Exception {
        var calls = new AtomicInteger();
        var closes = UsDoltCloses.fetch(DAY, address -> {
            int call = calls.getAndIncrement();
            String query = URLDecoder.decode(address, StandardCharsets.UTF_8);
            if (call == 0) return manifest(501);
            assertTrue(query.contains("ohlcv AS OF '" + REVISION + "'"));
            if (call == 1) throw new SocketTimeoutException("first page timed out");
            assertTrue(query.endsWith("ORDER BY act_symbol LIMIT 500"));
            var rows = new JSONArray();
            if (call == 2) {
                for (int i = 0; i < 500; i++) {
                    rows.put(row(String.format(java.util.Locale.ROOT, "T%04d", i), DAY));
                }
            } else {
                assertTrue(query.contains("AND act_symbol > 'T0499'"));
                rows.put(row("T0500", DAY));
            }
            return response(rows);
        });
        assertEquals(4, calls.get());
        assertEquals(501, closes.length());
        assertEquals("T0500", closes.getJSONObject(500).getString("symbol"));
    }

    @Test public void rejectsAReversePageThatDoesNotMatchThePreviouslyReadRows() {
        var calls = new AtomicInteger();
        assertThrows(JSONException.class, () ->
                UsDoltCloses.fetch(DAY, address -> recoveryResponse(address, calls, true)));
        assertEquals(4, calls.get());
    }

    private static JSONObject recoveryResponse(String address, AtomicInteger calls, boolean conflicting)
            throws SocketTimeoutException, JSONException {
        String query = URLDecoder.decode(address, StandardCharsets.UTF_8);
        int call = calls.getAndIncrement();
        if (call == 0) return manifest(1002);
        assertTrue(query.contains("ohlcv AS OF '" + REVISION + "'"));
        if (call == 2) {
            assertTrue(query.endsWith("OFFSET 1000"));
            throw new SocketTimeoutException("offset timed out");
        }
        var rows = new JSONArray();
        if (call == 1) {
            for (int i = 0; i < 1000; i++) rows.put(row(String.format(java.util.Locale.ROOT, "T%04d", i), DAY));
        } else {
            assertTrue(query.endsWith("ORDER BY act_symbol DESC LIMIT 1000"));
            for (int i = 1001; i >= 2; i--) rows.put(row(String.format(java.util.Locale.ROOT, "T%04d", i), DAY));
            if (conflicting) rows.getJSONObject(2).put("close", "0.01");
        }
        return response(rows);
    }

    @Test public void rejectsTruncatedDuplicateAndMismatchedRows() throws Exception {
        assertRejected(manifest(2), response(new JSONArray().put(row("X", DAY))));
        assertRejected(manifest(2), response(new JSONArray().put(row("X", DAY)).put(row("X", DAY))));
        assertRejected(manifest(1), response(new JSONArray().put(row("X", DAY.minusDays(1)))));
        assertRejected(manifest(1), response(new JSONArray()).put("query_execution_status", "RowLimit"));
    }

    private static void assertRejected(JSONObject manifest, JSONObject page) {
        var calls = new AtomicInteger();
        assertThrows(JSONException.class, () ->
                UsDoltCloses.fetch(DAY, address -> calls.getAndIncrement() == 0 ? manifest : page));
    }

    private static JSONObject row(String symbol, LocalDate day) throws JSONException {
        return new JSONObject().put("symbol", symbol).put("trading_date", day.toString()).put("close", "42.2500");
    }

    private static JSONObject manifest(int n) throws JSONException {
        return response(new JSONArray().put(new JSONObject().put("revision", REVISION).put("n", Integer.toString(n))));
    }

    private static JSONObject response(JSONArray rows) throws JSONException {
        return new JSONObject().put("query_execution_status", "Success").put("rows", rows);
    }
}
