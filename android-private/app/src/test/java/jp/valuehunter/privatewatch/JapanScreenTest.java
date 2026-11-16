package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

public class JapanScreenTest {
    private static final LocalDate SESSION = LocalDate.parse("2026-08-21");

    @Test public void screensOrdinarySharesAndDetectsOnlyNewEntrants() throws JSONException {
        var bars = new JSONArray();
        var metrics = new JSONArray();
        var master = new JSONArray();
        add(bars, metrics, master, "10010", 1000, 15, 1, 30, "011");
        add(bars, metrics, master, "186A0", 700, 8, 0.5, 30, "011");
        add(bars, metrics, master, "10020", 1000.1, 9, 0.5, 30, "011");
        add(bars, metrics, master, "10030", 999, -1, 0.5, 30, "011");
        add(bars, metrics, master, "10040", 999, 10, 1.1, 30, "011");
        add(bars, metrics, master, "10050", 999, 10, 0.5, 0, "011");
        add(bars, metrics, master, "10060", 999, 10, 0.5, 30, "014");
        add(bars, metrics, master, "10069", 999, 10, 0.5, 30, "011");
        var candidates = JapanScreen.find(SESSION, bars, metrics, master);
        assertEquals(Arrays.asList("186A", "1001"), candidates.stream()
                .map(JapanScreen.Candidate::code).collect(Collectors.toList()));
        assertEquals(100_000, candidates.get(1).cost(), 0);
        assertEquals(List.of(candidates.get(1)),
                JapanScreen.newlyQualified(candidates, Collections.singleton("186A")));
    }

    @Test public void rejectsMismatchedOrDuplicateSessions() throws JSONException {
        var bars = new JSONArray();
        var metrics = new JSONArray();
        var master = new JSONArray();
        add(bars, metrics, master, "10010", 999, 9, 0.5, 30, "011");
        metrics.getJSONObject(0).put("Date", SESSION.minusDays(1).toString());
        assertThrows(JSONException.class, () -> JapanScreen.find(SESSION, bars, metrics, master));
        metrics.getJSONObject(0).put("Date", SESSION.toString());
        bars.put(bars.getJSONObject(0));
        assertThrows(JSONException.class, () -> JapanScreen.find(SESSION, bars, metrics, master));
    }

    private static void add(JSONArray bars, JSONArray metrics, JSONArray master, String code,
                            double close, double per, double pbr, int volume, String product)
            throws JSONException {
        bars.put(row(code).put("C", close).put("Vo", volume));
        metrics.put(row(code).put("PER", per).put("PBR", pbr));
        master.put(row(code).put("Mkt", "0112").put("ProdCat", product).put("CoName", "テスト銘柄"));
    }

    private static JSONObject row(String code) throws JSONException {
        return new JSONObject().put("Date", SESSION.toString()).put("Code", code);
    }
}
