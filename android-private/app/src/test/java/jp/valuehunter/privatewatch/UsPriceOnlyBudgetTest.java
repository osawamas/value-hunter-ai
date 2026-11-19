package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

public class UsPriceOnlyBudgetTest {
    private static final LocalDate FRIDAY = LocalDate.of(2026, 11, 13);
    private static final LocalDate MONDAY = FRIDAY.plusDays(3);
    private static final String VERIFIED = UsDailyCloses.MASSIVE_SOURCE;
    private static final Set<String> LISTED = Set.of("ABC", "FIN", "UNCHANGED");

    @Test public void usesEachDaysExchangeRateAndExcludesFinanciallyScreenedStocks() throws Exception {
        var result = UsPriceOnlyBudget.compare(closes(FRIDAY, VERIFIED), closes(MONDAY, VERIFIED), rates(),
                LISTED, finance(VERIFIED), MONDAY);
        assertTrue(result.verifiedPriceBasis());
        assertEquals(2, result.screen().assessed());
        assertEquals(1, result.financialAssessed());
        assertEquals(3, result.combinedAssessed());
        assertEquals(3, result.listed());
        assertEquals(List.of("ABC"), result.screen().entered().stream().map(PriceOnlyScreen.BudgetEntry::code).toList());
        assertEquals(0, new BigDecimal("98000").compareTo(result.screen().entered().get(0).yen()));
    }

    @Test public void unverifiedDailyFeedProvidesAComparisonButIsIneligibleForAlerts() throws Exception {
        var provider = UsDoltCloses.SOURCE;
        var result = UsPriceOnlyBudget.compare(closes(FRIDAY, provider), closes(MONDAY, provider), rates(),
                LISTED, finance(provider), MONDAY);
        assertEquals(1, result.screen().entered().size());
        assertFalse(result.verifiedPriceBasis());
    }

    @Test public void rejectsMixedSourcesMissingSessionsStaleCacheAndPriorDayFx() throws Exception {
        var latest = closes(MONDAY, VERIFIED);
        var validPrevious = closes(FRIDAY, VERIFIED);
        var financial = finance(VERIFIED);
        assertEquals(0, UsPriceOnlyBudget.compare(closes(FRIDAY, UsDoltCloses.SOURCE), latest, rates(),
                LISTED, financial, MONDAY).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(closes(FRIDAY.minusDays(1), VERIFIED), latest, rates(),
                LISTED, financial, MONDAY).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(validPrevious, latest, rates(),
                LISTED, financial, MONDAY.plusDays(1)).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(validPrevious, latest,
                new JSONArray().put(rate(FRIDAY, 150)), LISTED, financial, MONDAY).screen().assessed());
    }

    @Test public void rejectsAdjustedOrUnspecifiedPriceBasisForNotification() throws Exception {
        var prior = closes(FRIDAY, VERIFIED);
        var latest = closes(MONDAY, VERIFIED);
        assertTrue(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());

        prior.put("adjusted", true);
        assertFalse(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());

        prior.put("adjusted", false);
        latest.remove("adjusted");
        assertFalse(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());
    }

    @Test public void onlyIndividuallyCorroboratedDoltCandidatesCanReachNotification() throws Exception {
        var source = UsDoltCloses.SOURCE;
        var previous = closes(FRIDAY, source);
        var latest = closes(MONDAY, source);
        assertTrue(UsPriceOnlyBudget.canCorroborateDolt(previous, latest));
        assertFalse(UsPriceOnlyBudget.canCorroborateDolt(previous, closes(MONDAY, source).put("adjusted", true)));
        var budget = UsPriceOnlyBudget.compare(previous, latest, rates(),
                LISTED, finance(source), MONDAY);
        assertTrue(budget.notificationEntries().isEmpty());
        assertEquals(budget.screen().entered(), budget.corroborated(Set.of("ABC")).notificationEntries());
        assertTrue(budget.corroborated(Set.of("FIN")).notificationEntries().isEmpty());
        assertFalse(budget.corroborated(Set.of("ABC")).verifiedPriceBasis());
    }

    @Test public void secondSourceRequiresTheSameSymbolDatesAndExactCloses() throws Exception {
        var data = new JSONObject().put("status", new JSONObject().put("rCode", 200))
                .put("data", new JSONObject().put("symbol", "ABC").put("totalRecords", 2)
                        .put("tradesTable", new JSONObject().put("rows", new JSONArray()
                                .put(new JSONObject().put("date", "11/16/2026").put("close", "$7.00"))
                                .put(new JSONObject().put("date", "11/13/2026").put("close", "$7")))));
        assertTrue(UsNasdaqCloseCheck.matches(data, "ABC", FRIDAY, new BigDecimal("7.0000"),
                MONDAY, new BigDecimal("7")));
        assertFalse(UsNasdaqCloseCheck.matches(data, "ABC", FRIDAY, new BigDecimal("0.7"),
                MONDAY, new BigDecimal("7")));
        assertFalse(UsNasdaqCloseCheck.matches(data, "OTHER", FRIDAY, new BigDecimal("7"),
                MONDAY, new BigDecimal("7")));
        data.getJSONObject("data").getJSONObject("tradesTable").getJSONArray("rows")
                .getJSONObject(1).put("date", "11/16/2026");
        assertFalse(UsNasdaqCloseCheck.matches(data, "ABC", FRIDAY, new BigDecimal("7"),
                MONDAY, new BigDecimal("7")));
    }

    @Test public void workerHoldsSplitListedOnlyByNasdaqAndRejectsAnOldCalendar() throws Exception {
        var source = UsDoltCloses.SOURCE;
        var before = closes(FRIDAY, source);
        var after = closes(MONDAY, source);
        var budget = UsPriceOnlyBudget.compare(before, after, rates(), LISTED, finance(source), MONDAY);
        var response = new JSONObject().put("status", new JSONObject().put("rCode", 200))
                .put("data", new JSONObject().put("asOf", "Mon, Nov 16, 2026")
                        .put("headers", new JSONObject().put("symbol", "SYMBOL").put("executionDate", "EFFECTIVE DATE"))
                        .put("rows", new JSONArray()
                                .put(new JSONObject().put("symbol", "ABC").put("executionDate", "11/16/2026"))));
        var screened = UsSecFinanceWorker.corroborateBudget(before, after, FRIDAY, MONDAY, MONDAY, budget, url -> {
            if (url.contains("DOLT_HASHOF")) {
                return new JSONObject().put("query_execution_status", "Success").put("rows",
                        new JSONArray().put(new JSONObject().put("revision", "a".repeat(32)))).toString();
            }
            if (url.contains("FROM+split")) {
                return new JSONObject().put("query_execution_status", "Success").put("rows", new JSONArray()).toString();
            }
            if (url.contains("/calendar/splits")) return response.toString();
            throw new AssertionError("A split candidate should not be sent for price corroboration");
        }, () -> false, Set.of(), "");
        assertTrue(screened.result().notificationEntries().isEmpty());
        assertEquals(1, screened.result().screen().entered().size());
        assertEquals(Set.of("ABC"), UsNasdaqCloseCheck.splits(response, FRIDAY, MONDAY));
        assertThrows(org.json.JSONException.class, () -> UsNasdaqCloseCheck.splits(response, FRIDAY, MONDAY.plusDays(1)));
    }

    @Test public void retriesRotatePastAnInterruptedBatchAndSkipAlreadySentSymbols() throws Exception {
        var source = UsDoltCloses.SOURCE;
        var before = closes(FRIDAY, source);
        var after = closes(MONDAY, source);
        var listed = new java.util.HashSet<String>();
        for (int i = 0; i < 30; i++) {
            String symbol = String.format(java.util.Locale.ROOT, "T%02d", i);
            listed.add(symbol);
            before.getJSONArray("closes").put(row(symbol, 7));
            after.getJSONArray("closes").put(row(symbol, 7));
        }
        var budget = UsPriceOnlyBudget.compare(before, after, rates(), listed, finance(source), MONDAY);
        var calls = new java.util.ArrayList<String>();
        UsSecFinanceWorker.Download download = url -> {
            if (url.contains("DOLT_HASHOF")) return """
                    {"query_execution_status":"Success","rows":[{"revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]}
                    """;
            if (url.contains("FROM+split")) return "{\"query_execution_status\":\"Success\",\"rows\":[]}";
            if (url.contains("/calendar/splits")) return """
                    {"status":{"rCode":200},"data":{"asOf":"Mon, Nov 16, 2026",
                    "headers":{"symbol":"SYMBOL","executionDate":"EFFECTIVE DATE"},"rows":[]}}
                    """;
            String symbol = java.net.URI.create(url).getPath().split("/")[3];
            calls.add(symbol);
            if (calls.size() == 3) throw new UsDailyWorker.HttpStatus(429);
            if (calls.size() == 4) throw new java.net.SocketTimeoutException("temporary timeout");
            return """
                    {"status":{"rCode":200},"data":{"symbol":"%s","totalRecords":2,"tradesTable":{"rows":[
                    {"date":"11/16/2026","close":"$7"},{"date":"11/13/2026","close":"$7"}]}}}
                    """.formatted(symbol);
        };
        var sent = new java.util.HashSet<String>();
        String cursor = "";
        for (int attempt = 0; attempt < 3; attempt++) {
            var checked = UsSecFinanceWorker.corroborateBudget(before, after, FRIDAY, MONDAY, MONDAY,
                    budget, download, () -> false, sent, cursor);
            assertEquals(attempt < 2, checked.retry());
            checked.result().notificationEntries().forEach(entry -> sent.add(entry.code()));
            cursor = checked.cursor();
        }
        assertEquals(listed, sent);
        assertEquals(List.of("T00", "T01", "T02", "T03"), calls.subList(0, 4));
        assertEquals(32, calls.size());
        assertEquals(1, java.util.Collections.frequency(calls, "T00"));
        assertEquals(2, java.util.Collections.frequency(calls, "T02"));
        assertEquals(2, java.util.Collections.frequency(calls, "T03"));
    }

    private static JSONObject closes(LocalDate day, String provider) throws Exception {
        return new JSONObject().put("trading_date_et", day.toString()).put("source", provider)
                .put("adjusted", VERIFIED.equals(provider) ? Boolean.FALSE : JSONObject.NULL)
                .put("closes", new JSONArray().put(row("ABC", 7)).put(row("FIN", 7))
                        .put(row("UNCHANGED", 5)).put(row("NOT_LISTED", 7)));
    }

    private static JSONObject row(String symbol, int price) throws Exception {
        return new JSONObject().put("symbol", symbol).put("close_usd", price);
    }

    private static JSONArray rates() throws Exception {
        return new JSONArray().put(rate(FRIDAY, 150)).put(rate(MONDAY, 140));
    }

    private static JSONObject rate(LocalDate date, int rate) throws Exception {
        return new JSONObject().put("date", date.toString()).put("base", "USD").put("quote", "JPY").put("rate", rate);
    }

    private static UsReferenceAlerts.Screen finance(String provider) {
        return new UsReferenceAlerts.Screen(MONDAY, provider, "a".repeat(64),
                Map.of("FIN", new UsReferenceAlerts.Observation(1, "NYSE", "outside_valuation", 1)));
    }
}
