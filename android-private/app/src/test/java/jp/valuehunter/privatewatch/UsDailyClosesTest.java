package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.time.Instant;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertThrows;

public class UsDailyClosesTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 16);
    private static final long BAR = Instant.parse("2026-11-16T05:00:00Z").toEpochMilli();

    @Test public void onlyPriorNewYorkDatesAreEligible() {
        assertEquals(DAY.minusDays(1),
                UsDailyCloses.mostRecentEligibleDay(Instant.parse("2026-11-17T04:59:59Z")));
        assertEquals(DAY,
                UsDailyCloses.mostRecentEligibleDay(Instant.parse("2026-11-17T05:00:00Z")));
        assertEquals(LocalDate.of(2026, 7, 13),
                UsDailyCloses.mostRecentEligibleDay(Instant.parse("2026-07-14T04:00:00Z")));
    }

    @Test public void thanksgivingIsSkippedButTheEarlyCloseIsStillASession() {
        var thanksgiving = LocalDate.of(2026, 11, 26);
        var friday = thanksgiving.plusDays(1);
        assertFalse(UsDailyCloses.tradingDay(thanksgiving));
        assertTrue(UsDailyCloses.tradingDay(friday));
        assertEquals(thanksgiving.minusDays(1), UsPriceOnlyBudget.previousSession(friday));
        assertEquals(friday, UsDailyCloses.onOrBeforeTradingDay(friday.plusDays(2)));
    }

    @Test public void followingYearsHandleObservedHolidaysAndShortSessions() {
        assertEquals(LocalDate.of(2026, 12, 31), UsPriceOnlyBudget.previousSession(LocalDate.of(2027, 1, 4)));
        assertEquals(LocalDate.of(2027, 3, 25), UsPriceOnlyBudget.previousSession(LocalDate.of(2027, 3, 29)));
        assertEquals(LocalDate.of(2027, 12, 23), UsPriceOnlyBudget.previousSession(LocalDate.of(2027, 12, 27)));
        assertTrue(UsDailyCloses.tradingDay(LocalDate.of(2027, 12, 31)));
        assertTrue(UsDailyCloses.tradingDay(LocalDate.of(2028, 7, 3)));
        assertEquals(LocalDate.of(2028, 7, 3), UsPriceOnlyBudget.previousSession(LocalDate.of(2028, 7, 5)));
    }

    @Test public void backfillDoesNotReuseADifferentDateProviderOrEmptySnapshot() throws Exception {
        var source = UsDoltCloses.SOURCE;
        var quote = new JSONObject().put("source", source).put("trading_date_et", DAY.toString())
                .put("closes", new JSONArray().put(new JSONObject()
                        .put("symbol", "XYZ").put("close_usd", 12.5)));
        assertTrue(UsDailyWorker.matchesPriorSnapshot(quote, DAY, source));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote, DAY.minusDays(1), source));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote, DAY, UsDailyCloses.MASSIVE_SOURCE));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote.put("closes", new JSONArray()), DAY, source));
    }

    @Test public void referenceBudgetCannotUseDamagedPriorClose() throws Exception {
        LocalDate current = LocalDate.of(2026, 11, 17);
        var prior = new JSONObject().put("source", UsDoltCloses.SOURCE)
                .put("trading_date_et", DAY.toString())
                .put("closes", new JSONArray().put(new JSONObject()
                        .put("symbol", "AAPL").put("close_usd", 125.5)));
        assertEquals(java.util.Set.of("AAPL"),
                UsSingleSessionBudgetCheck.verifiedPriorSymbols(prior, current));
        assertTrue(UsSingleSessionBudgetCheck.verifiedPriorSymbols(
                new JSONObject(prior.toString()).put("trading_date_et", "2026-11-13"),
                current).isEmpty());
        assertTrue(UsSingleSessionBudgetCheck.verifiedPriorSymbols(
                new JSONObject(prior.toString()).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "AAPL"))),
                current).isEmpty());
        assertTrue(UsSingleSessionBudgetCheck.verifiedPriorSymbols(
                new JSONObject(prior.toString()).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "AAPL").put("close_usd", -3))),
                current).isEmpty());
    }

    @Test public void corruptCurrentSnapshotMustNotSuppressNewFetch() throws Exception {
        var valid = new JSONObject().put("source", UsDoltCloses.SOURCE)
                .put("trading_date_et", DAY.toString())
                .put("closes", new JSONArray().put(new JSONObject()
                        .put("symbol", "AAPL").put("close_usd", 125.5)));
        assertEquals(DAY, UsDailyWorker.validatedSnapshotDate(valid));
        assertThrows(JSONException.class, () -> UsDailyWorker.validatedSnapshotDate(
                new JSONObject(valid.toString()).put("closes", new JSONArray())));
        assertThrows(JSONException.class, () -> UsDailyWorker.validatedSnapshotDate(
                new JSONObject(valid.toString()).put("closes", new JSONArray()
                        .put(new JSONObject().put("symbol", "AAPL")))));
        assertThrows(java.time.format.DateTimeParseException.class,
                () -> UsDailyWorker.validatedSnapshotDate(
                        new JSONObject(valid.toString()).put("trading_date_et", "2026-02-30")));
    }

    @Test public void malformedPriorClosesRequireFreshBackfill() throws JSONException {
        String provider = UsDoltCloses.SOURCE;
        var valid = new JSONObject().put("source", provider).put("trading_date_et", DAY.toString())
                .put("closes", new JSONArray().put(new JSONObject()
                        .put("symbol", "AAPL").put("close_usd", 125.5)));
        assertTrue(UsDailyWorker.matchesPriorSnapshot(valid, DAY, provider));
        for (Object bad : new Object[]{JSONObject.NULL, -1, 0, "12.5", "not a price"}) {
            var corrupted = new JSONObject(valid.toString())
                    .put("closes", new JSONArray().put(new JSONObject()
                            .put("symbol", "AAPL").put("close_usd", bad)));
            assertFalse(UsDailyWorker.matchesPriorSnapshot(corrupted, DAY, provider));
        }
        var absent = new JSONObject(valid.toString())
                .put("closes", new JSONArray().put(new JSONObject().put("symbol", "AAPL")));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(absent, DAY, provider));
        var invalidTicker = new JSONObject(valid.toString())
                .put("closes", new JSONArray().put(new JSONObject()
                        .put("symbol", "BAD TICKER").put("close_usd", 2)));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(invalidTicker, DAY, provider));
        var duplicate = new JSONObject(valid.toString()).put("closes", new JSONArray()
                .put(new JSONObject().put("symbol", "AAPL").put("close_usd", 1))
                .put(new JSONObject().put("symbol", "AAPL").put("close_usd", 2)));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(duplicate, DAY, provider));
        var mixed = new JSONObject(valid.toString()).put("closes", new JSONArray()
                .put(new JSONObject().put("symbol", "AAPL").put("close_usd", 125.5))
                .put(new JSONObject().put("symbol", "MSFT")));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(mixed, DAY, provider));
    }

    @Test public void keepsUnadjustedCloseAndDropsOtcAndMissingPrices() throws JSONException {
        var rows = new JSONArray().put(bar("AAPL", BAR)).put(bar("TEST", BAR).put("otc", true))
                .put(bar("ZERO", BAR).put("c", 0));
        var closes = UsDailyCloses.parse(summary(rows), DAY);
        assertEquals(1, closes.length());
        assertEquals("AAPL", closes.getJSONObject(0).getString("symbol"));
        assertEquals(42.25, closes.getJSONObject(0).getDouble("close_usd"), 0);
    }

    @Test public void rejectsDuplicateStalePartialAndAdjustedBars() throws JSONException {
        assertThrows(JSONException.class, () -> UsDailyCloses.parse(
                summary(new JSONArray().put(bar("AAPL", BAR)).put(bar("AAPL", BAR))), DAY));
        assertThrows(JSONException.class, () -> UsDailyCloses.parse(
                summary(new JSONArray().put(bar("AAPL", BAR - 1))), DAY));
        assertThrows(JSONException.class, () -> UsDailyCloses.parse(
                summary(new JSONArray().put(bar("AAPL", BAR))).put("resultsCount", 2), DAY));
        assertThrows(JSONException.class, () -> UsDailyCloses.parse(
                summary(new JSONArray().put(bar("AAPL", BAR))).put("adjusted", true), DAY));
    }

    @Test public void acceptsAnExplicitEmptyTradingDay() throws JSONException {
        var payload = summary(new JSONArray());
        payload.remove("results");
        assertEquals(0, UsDailyCloses.parse(payload, DAY).length());
    }

    private static JSONObject bar(String ticker, long timestamp) throws JSONException {
        return new JSONObject().put("T", ticker).put("t", timestamp).put("c", 42.25);
    }

    private static JSONObject summary(JSONArray rows) throws JSONException {
        return new JSONObject().put("status", "OK").put("adjusted", false)
                .put("results", rows).put("resultsCount", rows.length());
    }
}
