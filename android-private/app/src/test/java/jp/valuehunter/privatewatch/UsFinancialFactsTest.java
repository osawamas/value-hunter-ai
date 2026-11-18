package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertThrows;
import org.json.JSONException;

public class UsFinancialFactsTest {
    private static final String Q = "0000000001-26-000001";
    private static final String K = "0000000001-26-000002";
    private static final LocalDate SESSION = LocalDate.parse("2026-11-17");

    @Test public void usesMatchingFiscalYearToDateWindowsAndCoverShares() throws Exception {
        var facts = UsFinancialFacts.read(payload(), 1, SESSION);
        assertEquals(new BigDecimal("110"), facts.profit());
        assertEquals(new BigDecimal("350"), facts.equity());
        assertEquals(new BigDecimal("40"), facts.shares());
        assertEquals(LocalDate.parse("2026-10-13"), facts.shareDate());
        assertEquals(Q, facts.accession());
    }

    @Test public void sameDayFilingAndDuplicateShareCountsHold() throws Exception {
        assertNull(UsFinancialFacts.read(payload(), 1, LocalDate.parse("2026-10-20")));
        var duplicate = payload();
        duplicate.getJSONObject("facts").getJSONObject("dei").getJSONObject("EntityCommonStockSharesOutstanding")
                .getJSONObject("units").getJSONArray("shares")
                .put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 41));
        assertNull(UsFinancialFacts.read(duplicate, 1, SESSION));
        assertThrows(JSONException.class, () -> UsFinancialFacts.read(payload(), 42, SESSION));
    }

    private static JSONObject payload() throws JSONException {
        var equity = new JSONArray().put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 350));
        var profit = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "10-K", 100))
                .put(row("2025-01-01", "2025-09-30", "2026-10-20", Q, "10-Q", 60))
                .put(row("2026-01-01", "2026-09-30", "2026-10-20", Q, "10-Q", 70))
                .put(row("2026-07-01", "2026-09-30", "2026-10-20", Q, "10-Q", 20));
        var shares = new JSONArray().put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 40));
        return new JSONObject().put("cik", 1).put("facts", new JSONObject()
                .put("us-gaap", new JSONObject().put("StockholdersEquity", units("USD", equity))
                        .put("NetIncomeLoss", units("USD", profit)))
                .put("dei", new JSONObject().put("EntityCommonStockSharesOutstanding", units("shares", shares))));
    }

    private static JSONObject units(String unit, JSONArray facts) throws JSONException {
        return new JSONObject().put("units", new JSONObject().put(unit, facts));
    }

    private static JSONObject row(String start, String end, String filed, String accn, String form, int value)
            throws JSONException {
        var row = new JSONObject().put("end", end).put("filed", filed).put("accn", accn)
                .put("form", form).put("val", value);
        if (start != null) row.put("start", start);
        return row;
    }
}
