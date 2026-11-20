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

    private static JSONObject response(String symbol) {
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
