package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

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
