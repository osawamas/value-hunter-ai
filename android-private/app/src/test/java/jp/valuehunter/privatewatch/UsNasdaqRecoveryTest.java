package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.*;

public class UsNasdaqRecoveryTest {
    private static final LocalDate OLD = LocalDate.of(2026, 11, 16);
    private static final LocalDate NEW = OLD.plusDays(1);
    private static final UsScreen.Fx OLD_FX = new UsScreen.Fx(OLD, 150);
    private static final UsScreen.Fx NEW_FX = new UsScreen.Fx(NEW, 150);

    @Test public void corroboratesOfficialTableAndSymbolAndRequiresBothDays() throws Exception {
        var response = response("ABC");
        var pair = UsNasdaqOfficialClose.read(response, "ABC", OLD, NEW);
        assertEquals(new BigDecimal("7"), pair.before());
        assertEquals(new BigDecimal("6"), pair.after());
        assertNull(UsNasdaqOfficialClose.read(response, "ABC", OLD, NEW.plusDays(1)));
        assertThrows(JSONException.class, () -> UsNasdaqOfficialClose.read(response, "XYZ", OLD, NEW));
        response.getJSONObject("data").getJSONObject("nocp").getJSONArray("nocpChart")
                .getJSONObject(0).put("y", "8");
        assertThrows(JSONException.class, () -> UsNasdaqOfficialClose.read(response, "ABC", OLD, NEW));
    }

    @Test public void recoversOnlyMissingNasdaqPairsAndNeverMixesProvidersOrSplitDates() throws Exception {
        var missing = UsNasdaqRecovery.missing(Set.of("PRIOR", "CURRENT", "BOTH", "FIN", "COMPLETE", "SPLIT"),
                Set.of("FIN"), Set.of("PRIOR", "COMPLETE", "NYSE"), Set.of("CURRENT", "COMPLETE"));
        assertEquals(Set.of("PRIOR", "CURRENT", "BOTH", "SPLIT"), missing);
        var receipts = new JSONObject();
        var result = UsNasdaqRecovery.check(missing, OLD, NEW, OLD_FX, NEW_FX, Set.of("SPLIT"), Set.of(),
                receipts, address -> response(address.split("/")[5]).toString(), () -> false);
        assertEquals(3, result.screen().assessed());
        assertEquals(3, result.screen().entered().size());
        assertFalse(receipts.has("SPLIT"));
        assertEquals(0, UsNasdaqRecovery.check(missing, OLD, NEW, OLD_FX, OLD_FX, Set.of(), Set.of(),
                receipts, address -> { throw new AssertionError(); }, () -> false).screen().assessed());
    }

    @Test public void resumesRateLimitedAndLongBatchesFromSavedReceipts() throws Exception {
        var symbols = new HashSet<String>();
        for (int i = 0; i < 30; i++) symbols.add("N" + i);
        var receipts = new JSONObject();
        var calls = new java.util.ArrayList<String>();
        UsSecFinanceWorker.Download fetch = address -> {
            var symbol = address.split("/")[5];
            calls.add(symbol);
            if (calls.size() == 3) throw new UsDailyWorker.HttpStatus(429);
            return response(symbol).toString();
        };
        var first = UsNasdaqRecovery.check(symbols, OLD, NEW, OLD_FX, NEW_FX, Set.of(), Set.of(), receipts, fetch, () -> false);
        assertTrue(first.retry());
        assertEquals(2, first.screen().assessed());
        receipts = new JSONObject(receipts.toString());
        var second = UsNasdaqRecovery.check(symbols, OLD, NEW, OLD_FX, NEW_FX, Set.of(), Set.of(), receipts, fetch, () -> false);
        assertTrue(second.more());
        var third = UsNasdaqRecovery.check(symbols, OLD, NEW, OLD_FX, NEW_FX, Set.of(), Set.of(), receipts, fetch, () -> false);
        assertEquals(30, third.screen().assessed());
        assertFalse(third.more());
        assertEquals(31, calls.size());
    }

    @Test public void restoredDeliveryHistoryAlsoDeduplicatesAChangeOfPriceSource() {
        var fromPrimary = new PriceOnlyScreen.BudgetEntry("ABC", new BigDecimal("99000"));
        var fromOfficial = new PriceOnlyScreen.BudgetEntry("ABC", new BigDecimal("98000"));
        var next = new PriceOnlyScreen.BudgetEntry("XYZ", new BigDecimal("97000"));
        assertEquals(java.util.List.of(fromPrimary, next), UsSecFinanceWorker.pendingBudgetEntries(
                java.util.List.of(fromPrimary, fromOfficial, next), Set.of()));
        assertEquals(java.util.List.of(next), UsSecFinanceWorker.pendingBudgetEntries(
                java.util.List.of(fromOfficial, next), Set.of("ABC")));
    }

    @Test public void rechecksAClosingPairPublishedAfterTheFirstAttempt() throws Exception {
        var receipts = new JSONObject();
        var first = UsNasdaqRecovery.check(Set.of("ABC", "DEF"), OLD, NEW, OLD_FX, NEW_FX, Set.of(),
                Set.of(), receipts, url -> {
                    if (url.contains("/DEF/")) return response("DEF").toString();
                    var payload = response("ABC");
                    var partial = payload.getJSONObject("data").getJSONObject("nocp");
                    partial.getJSONArray("nocpTable").remove(1);
                    partial.getJSONArray("nocpChart").remove(1);
                    return payload.toString();
                }, () -> false, () -> 1);
        assertEquals(1, first.screen().assessed());
        assertFalse(first.more());
        var saved = new JSONObject(receipts.toString());
        var early = UsNasdaqRecovery.check(Set.of("ABC", "DEF"), OLD, NEW, OLD_FX, NEW_FX, Set.of(),
                Set.of(), saved, url -> { throw new AssertionError(url); }, () -> false, () -> 30_000);
        assertEquals(1, early.screen().assessed());
        var result = UsNasdaqRecovery.check(Set.of("ABC", "DEF"), OLD, NEW, OLD_FX, NEW_FX, Set.of(),
                Set.of(), saved, url -> {
                    assertTrue(url.contains("/ABC/"));
                    return response("ABC").toString();
                }, () -> false, () -> 3_600_001);
        assertEquals(2, result.screen().assessed());
        assertEquals(java.util.List.of("ABC"), UsSecFinanceWorker.pendingBudgetEntries(
                result.screen().entered(), Set.of("DEF")).stream().map(PriceOnlyScreen.BudgetEntry::code).toList());
    }

    @Test public void corruptOrLegacyReceiptsCanBeRecovered() throws Exception {
        var receipts = new JSONObject("{\"ABC\":[\"7\"],\"DEF\":false,\"XYZ\":[\"0\",\"6\"]}");
        var symbols = Set.of("ABC", "DEF", "XYZ");
        UsSecFinanceWorker.Download load = url -> response(url.split("/")[5]).toString();
        var recovered = UsNasdaqRecovery.check(symbols, OLD, NEW, OLD_FX, NEW_FX, Set.of(), Set.of(),
                receipts, load, () -> false);
        assertEquals(1, recovered.screen().assessed());
        assertTrue(recovered.more());
        assertEquals(3, UsNasdaqRecovery.check(symbols, OLD, NEW, OLD_FX, NEW_FX, Set.of(), Set.of(),
                receipts, load, () -> false).screen().assessed());
    }

    private static JSONObject response(String symbol) throws JSONException {
        var table = new JSONArray();
        var chart = new JSONArray();
        var format = java.time.format.DateTimeFormatter.ofPattern("MM/dd/uuuu", java.util.Locale.ROOT);
        int price = 7;
        for (var day : java.util.List.of(OLD, NEW)) {
            table.put(new JSONObject().put("date", day.format(format)).put("price", "$" + price));
            chart.put(new JSONObject().put("x", day.atStartOfDay().toEpochSecond(ZoneOffset.UTC))
                    .put("y", Integer.toString(price)).put("z", new JSONObject().put("details", symbol + " Close Price: $" + price)));
            price--;
        }
        return new JSONObject().put("status", new JSONObject().put("rCode", 200).put("bCodeMessage", JSONObject.NULL))
                .put("data", new JSONObject().put("headers", new JSONObject().put("date", "Trade Date")
                        .put("price", "Nasdaq Closing Price"))
                        .put("nocp", new JSONObject().put("nocpTable", table).put("nocpChart", chart)));
    }
}
