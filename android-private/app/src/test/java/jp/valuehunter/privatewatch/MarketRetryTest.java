package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.*;

public final class MarketRetryTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 19);

    @Test public void repairsOnlyMissingOrSplitHeldFinancialsAndRetainsConfirmedRows() throws Exception {
        var rows = new JSONArray(List.of(ticker("READY"), ticker("SPLIT")));
        var targets = new JSONArray(List.of(ticker("READY"), ticker("MISSING")));
        var ledger = new JSONObject().put("split_holds", new JSONArray(List.of("SPLIT")));
        var scan = new JSONObject().put("results", rows).put("targets", targets).put("ledger", ledger);
        assertTrue(UsSecFinanceWorker.prepareRepair(scan));
        assertEquals(2, scan.getJSONArray("targets").length());
        assertEquals("SPLIT", scan.getJSONArray("targets").getJSONObject(0).getString("symbol"));
        assertEquals("MISSING", scan.getJSONArray("targets").getJSONObject(1).getString("symbol"));
        assertEquals(1, scan.getInt("reused"));
        assertEquals("READY", scan.getJSONArray("results").getJSONObject(0).getString("symbol"));
        assertEquals(ledger, scan.getJSONObject("retained_ledger"));
    }

    @Test public void closeRepairRequestsOnlyMissingSymbolsAndRejectsUnexpectedQuotes() throws Exception {
        var found = UsDoltCloses.supplement(DAY, Set.of("MISSING", "OTHER"), address -> {
            String sql = URLDecoder.decode(address, StandardCharsets.UTF_8);
            assertTrue(sql.contains("act_symbol IN ('MISSING','OTHER')"));
            assertFalse(sql.contains("READY"));
            return reply("MISSING");
        });
        assertEquals(1, found.length());
        assertEquals("MISSING", found.getJSONObject(0).getString("symbol"));
        assertThrows(JSONException.class, () -> UsDoltCloses.supplement(DAY, Set.of("MISSING"),
                address -> reply("READY")));
    }

    private static JSONObject ticker(String ticker) throws JSONException {
        return new JSONObject().put("symbol", ticker);
    }

    private static JSONObject reply(String ticker) throws JSONException {
        return new JSONObject().put("query_execution_status", "Success")
                .put("rows", new JSONArray(List.of(ticker(ticker).put("trading_date", DAY.toString()).put("close", 5))));
    }
}
