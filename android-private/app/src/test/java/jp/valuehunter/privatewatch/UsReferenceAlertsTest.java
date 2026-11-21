package jp.valuehunter.privatewatch;

import org.json.JSONObject;
import org.json.JSONArray;
import org.junit.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;

public final class UsReferenceAlertsTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);
    private static final String SOURCE = UsDoltCloses.SOURCE;

    private static UsReferenceAlerts.Observation row(int cik, String status, int quantity) {
        return new UsReferenceAlerts.Observation(cik, "NYSE", status, quantity);
    }

    private static UsReferenceAlerts.Screen screen(LocalDate day, String provider,
                                                    Map<String, UsReferenceAlerts.Observation> rows) {
        return new UsReferenceAlerts.Screen(day, provider, "", rows);
    }

    @Test public void queuedAlertIsInvalidatedBySameDayCloseCorrection() {
        String original = "a".repeat(64);
        String corrected = "b".repeat(64);
        assertEquals(true, UsReferenceAlerts.pendingMatchesClose(original, original));
        assertFalse(UsReferenceAlerts.pendingMatchesClose(original, corrected));
        assertFalse(UsReferenceAlerts.pendingMatchesClose("", corrected));
        assertFalse(UsReferenceAlerts.pendingMatchesClose(null, corrected));
        assertFalse(UsReferenceAlerts.pendingMatchesClose("invalid", "invalid"));
    }

    @Test public void reportsOnlyComparableEntriesAndPrioritizesPurchaseLots() {
        var previous = screen(DAY, SOURCE, Map.of(
                "AAA", row(1, "reference", 1), "BBB", row(2, "outside_budget", 1),
                "CCC", row(3, "outside_valuation", 100), "DDD", row(4, "priority", 100)));
        var next = screen(DAY.plusDays(1), SOURCE, Map.of(
                "AAA", row(1, "priority", 1), "BBB", row(2, "reference", 100),
                "CCC", row(13, "priority", 100), "DDD", row(4, "priority", 100),
                "NEW", row(5, "priority", 100)));
        assertEquals(List.of("BBB · 100株 · 参考候補", "AAA · 1株 · 優先候補"),
                UsReferenceAlerts.entrants(previous, next));
        assertEquals(List.of(), UsReferenceAlerts.entrants(null, next));
        assertEquals(List.of(), UsReferenceAlerts.entrants(next, next));
        assertEquals(List.of(), UsReferenceAlerts.entrants(previous,
                screen(DAY.plusDays(1), UsDailyCloses.MASSIVE_SOURCE, next.rows())));
        assertEquals(List.of(), UsReferenceAlerts.entrants(previous,
                screen(DAY.plusDays(8), SOURCE, next.rows())));
    }

    @Test public void rejectsDuplicateObservationsAndOutdatedFx() throws Exception {
        var ledger = new JSONObject("""
                {"trading_date_et":"2026-11-17","reference_screen":{
                    "provider":"dolthub-post-no-preference-stocks",
                    "close_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "fx_date":"2026-11-17",
                    "observations":[{"symbol":"ABC","exchange":"NYSE","cik":1,"status":"priority","quantity":100}]
                }}
                """);
        assertEquals(row(1, "priority", 100), UsReferenceAlerts.read(ledger).rows().get("ABC"));
        var screen = ledger.getJSONObject("reference_screen");
        screen.put("fx_date", "2026-11-16");
        assertFalse(UsReferenceAlerts.hasTradeDateFx(ledger, DAY));
        assertThrows(org.json.JSONException.class, () -> UsReferenceAlerts.read(ledger));
        screen.put("fx_date", "2026-11-17");
        var rows = screen.getJSONArray("observations");
        rows.put(rows.getJSONObject(0));
        assertThrows(org.json.JSONException.class, () -> UsReferenceAlerts.read(ledger));
    }

    @Test public void screenCanBeRebuiltWhenTheMatchingFxArrivesAfterAnOutage() throws Exception {
        var rates = new JSONArray("""
                [{"date":"2026-11-16","base":"USD","quote":"JPY","rate":159.77}]
                """);
        assertThrows(org.json.JSONException.class, () -> UsSecFinanceWorker.tradeDateFx(rates, DAY));
        rates.put(new JSONObject("""
                {"date":"2026-11-17","base":"USD","quote":"JPY","rate":159.46}
                """));
        assertEquals(DAY, UsSecFinanceWorker.tradeDateFx(rates, DAY).date());
    }
}
