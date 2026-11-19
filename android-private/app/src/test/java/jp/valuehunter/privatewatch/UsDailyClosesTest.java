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

    @Test public void backfillDoesNotReuseADifferentDateProviderOrEmptySnapshot() throws Exception {
        var source = UsDoltCloses.SOURCE;
        var quote = new JSONObject().put("source", source).put("trading_date_et", DAY.toString())
                .put("closes", new JSONArray().put(new JSONObject().put("symbol", "XYZ")));
        assertTrue(UsDailyWorker.matchesPriorSnapshot(quote, DAY, source));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote, DAY.minusDays(1), source));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote, DAY, UsDailyCloses.MASSIVE_SOURCE));
        assertFalse(UsDailyWorker.matchesPriorSnapshot(quote.put("closes", new JSONArray()), DAY, source));
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
