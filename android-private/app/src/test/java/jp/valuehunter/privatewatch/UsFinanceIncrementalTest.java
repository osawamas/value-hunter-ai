package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.time.LocalDate;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertThrows;

public class UsFinanceIncrementalTest {
    private static final LocalDate OLD = LocalDate.of(2026, 11, 16);
    private static final LocalDate NEXT = OLD.plusDays(1);

    @Test public void includesEarlierCorrectionsAndRejectsAnIncompleteIndex() throws Exception {
        String index = """
                Last Data Received: Nov 16, 2026
                CIK|Company Name|Form Type|Date Filed|File Name
                ------
                12|One|10-Q|20261116|edgar/data/12/0000000012-26-000001.txt
                34|Two|8-K|2026-11-13|edgar/data/34/0000000034-26-000001.txt
                """;
        assertEquals(Set.of(12, 34), UsSecFilingIndex.issuers(index, OLD));
        assertThrows(JSONException.class, () -> UsSecFilingIndex.issuers(index, NEXT));
        assertThrows(JSONException.class, () -> UsSecFilingIndex.issuers(index + "34|Two|8-K", OLD));
        assertEquals("https://www.sec.gov/Archives/edgar/daily-index/2027/QTR1/master.20270104.idx",
                UsSecFilingIndex.address(LocalDate.of(2027, 1, 4)));
    }

    @Test public void refreshesChangedExpiredAndRemappedIssuers() throws Exception {
        var prior = new JSONArray().put(cached("UNCHANGED", 1, OLD.minusDays(10)))
                .put(cached("CHANGED", 2, OLD.minusDays(10)))
                .put(cached("EXPIRED", 3, OLD.minusDays(150)))
                .put(cached("REMAPPED", 4, OLD.minusDays(10)));
        var previous = new JSONObject().put("day", OLD.toString()).put("full_refresh_day", OLD.toString())
                .put("targets", new JSONArray().put(target("UNCHANGED", 1)).put(target("CHANGED", 2))
                        .put(target("EXPIRED", 3)).put(target("REMAPPED", 4)))
                .put("cursor", 4).put("results", prior);
        var targets = new JSONArray().put(target("UNCHANGED", 1)).put(target("CHANGED", 2))
                .put(target("EXPIRED", 3)).put(target("REMAPPED", 5)).put(target("NEW", 6));

        assertEquals(OLD, UsDeviceFinancials.reuseFrom(previous, NEXT));
        var incremental = UsDeviceFinancials.startScan("hash", NEXT, targets, previous, Set.of(2));
        assertEquals(1, incremental.getInt("reused"));
        assertEquals("UNCHANGED", incremental.getJSONArray("results").getJSONObject(0).getString("symbol"));
        assertEquals(4, incremental.getJSONArray("targets").length());
        assertEquals(OLD.toString(), incremental.getString("full_refresh_day"));

        var full = UsDeviceFinancials.startScan("hash", NEXT, targets, previous, null);
        assertEquals(0, full.getInt("reused"));
        assertEquals(5, full.getJSONArray("targets").length());
        assertEquals(NEXT.toString(), full.getString("full_refresh_day"));
        assertNull(UsDeviceFinancials.reuseFrom(previous, OLD.plusDays(7)));
        previous.put("targets", targets);
        assertEquals(OLD, UsDeviceFinancials.reuseFrom(previous, NEXT));
        previous.put("cursor", 3);
        assertNull(UsDeviceFinancials.reuseFrom(previous, NEXT));
    }

    @Test public void sameDayReceiptChangesWhenEvidenceOrNotificationSettingsChange() throws Exception {
        var day = OLD;
        var evidence = new JSONObject().put("observations", new JSONObject().put("TEST", 1));
        String first = UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, true, "", true, true, 0, 0);
        assertEquals(first, UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, true, "", true, true, 0, 0));
        org.junit.Assert.assertNotEquals(first, UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, false, "", true, true, 0, 0));
        org.junit.Assert.assertNotEquals(first, UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, true, "", true, false, 0, 0));
        org.junit.Assert.assertNotEquals(first, UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, true, "", true, true, 1, 0));
        evidence.getJSONObject("observations").put("TEST", 2);
        org.junit.Assert.assertNotEquals(first, UsDailyWorker.financialScreenReceipt(
                day, "dolt", "hash", evidence, true, "", true, true, 0, 0));
    }

    private static JSONObject target(String symbol, int cik) throws JSONException {
        return new JSONObject().put("symbol", symbol).put("cik", cik).put("exchange", "NYSE");
    }

    private static JSONObject cached(String symbol, int cik, LocalDate period) throws JSONException {
        return target(symbol, cik).put("equity_date", period.toString()).put("filed", OLD.minusDays(1).toString())
                .put("meter_balance", 80);
    }
}
