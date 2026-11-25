package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

public final class ValueAlertMeterTest {
    @Test public void defaultsAndCustomBoundariesRespectEvidenceCeilings() {
        assertEquals("60,75,85", ValueAlertMeter.DEFAULT.encode());
        assertEquals(ValueAlertMeter.DEFAULT, ValueAlertMeter.Thresholds.read("70,70,95"));
        var strong = ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 100, 100, 100);
        assertEquals(3, strong.level(ValueAlertMeter.DEFAULT));
        assertEquals(2, strong.level(ValueAlertMeter.Thresholds.read("60,75,100")));
        var noPeers = ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 100, null, 100);
        assertTrue(noPeers.points() >= 85);
        assertEquals(2, noPeers.level(ValueAlertMeter.DEFAULT));
        var unavailable = ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(), null, null, null);
        assertEquals(1, unavailable.level(ValueAlertMeter.DEFAULT));
    }

    @Test public void usSecOnlyStrictValuationCanReachTopTierWithoutInventedPeerEvidence() throws Exception {
        var eps = List.of(number("3"), number("2"), number("1"));
        var strict = ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                eps, 100, null, null);
        assertEquals(3, strict.confirmed());
        assertEquals(3, strict.ceiling());
        assertEquals(3, strict.level(ValueAlertMeter.DEFAULT));
        assertEquals(0, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(number("0.8"), number("2"), number("1")), 100, null, null).ceiling());
        assertEquals(1, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                eps, null, null, null).ceiling());
        assertEquals(2, ValueAlertMeter.assess(number("8"), number("1"), number("12"),
                eps, 100, null, null).ceiling());
        assertEquals(2, ValueAlertMeter.assess(number("6"), number("1"), number("9"),
                eps, 100, null, null).ceiling());
        assertEquals(2, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                eps, 100, 0, null).ceiling());
        assertEquals(0, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                eps, 0, null, null).ceiling());

        // Verify that the same score survives the production US screen's meter serialization.
        var day = LocalDate.of(2026, 11, 19);
        var row = new JSONObject().put("symbol", "TEST").put("exchange", "NYSE").put("cik", 123)
                .put("share_date", "2026-10-31").put("profit", "100")
                .put("equity", "2000").put("shares", "100")
                .put("meter_eps", new JSONArray().put("3").put("2").put("1"))
                .put("meter_cash", 100);
        // Close 6 USD * 100 shares = 600 USD, PER 6, PBR 0.3.
        var ledger = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, "a".repeat(64),
                new JSONArray().put(row), Map.of("TEST", number("6")),
                new UsScreen.Fx(day, 150), Map.of());
        var recorded = ledger.getJSONObject("reference_screen").getJSONObject("meter_rows")
                .getJSONArray("NYSE:123:TEST");
        assertEquals(3, recorded.getInt(1));
        assertTrue(recorded.getInt(0) >= ValueAlertMeter.DEFAULT.third());
    }

    @Test public void profitDeclineOrRepeatedNegativeCashCannotBeOffsetByLowMultiples() {
        assertEquals(0, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(number("0.8"), number("1"), number("1")), 100, 100, 100).ceiling());
        assertEquals(0, ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 0, 100, 100).ceiling());
        assertEquals(0, ValueAlertMeter.assess(number("6"), number("1"), null,
                List.of(), null, null, null).confirmed());
    }

    @Test public void recategorizingBothDaysDoesNotCountSettingsChangesAsNewAlerts() {
        var prior = new ValueAlertMeter.Score(74, 3, 6);
        var latest = new ValueAlertMeter.Score(78, 3, 6);
        assertEquals(2, ValueAlertMeter.promotion(prior, latest, ValueAlertMeter.DEFAULT));
        assertEquals(0, ValueAlertMeter.promotion(prior, latest, ValueAlertMeter.Thresholds.read("60,70,90")));
        assertEquals(0, ValueAlertMeter.promotion(null, latest, ValueAlertMeter.DEFAULT));
        var oldDay = LocalDate.of(2026, 11, 18);
        var newDay = oldDay.plusDays(1);
        var history = new ValueAlertPreview.History(
                new ValueAlertPreview.Session(newDay, "JPX", Map.of("A", new ValueAlertPreview.Row(latest, 100))),
                new ValueAlertPreview.Session(oldDay, "JPX", Map.of("A", new ValueAlertPreview.Row(prior, 100))));
        assertTrue(ValueAlertPreview.summary(ValueAlertPreview.Market.JPX, history, ValueAlertMeter.DEFAULT)
                .contains("新規・昇格の試算（比較可能 1銘柄）\n100株枠 割安 0 · かなり割安 1"));
        var gap = new ValueAlertPreview.History(history.latest(),
                new ValueAlertPreview.Session(oldDay.minusDays(1), "JPX", history.previous().rows()));
        assertTrue(ValueAlertPreview.summary(ValueAlertPreview.Market.JPX, gap, ValueAlertMeter.DEFAULT)
                .contains("前取引日の照合待ち"));
    }

    @Test public void secEvidenceUsesOnlyComparableYearsInAnAvailableFiling() throws Exception {
        var eps = new JSONArray();
        var cash = new JSONArray();
        for (int year = 2023; year <= 2025; year++) {
            eps.put(fact(year, year - 2022, "2026-02-05"));
            cash.put(fact(year, -200, "2026-02-05"));
        }
        eps.put(fact(2025, 40, "2026-03-05"));
        var gaap = new JSONObject()
                .put("EarningsPerShareBasic", new JSONObject().put("units", new JSONObject().put("USD/shares", eps)))
                .put("NetCashProvidedByUsedInOperatingActivities",
                        new JSONObject().put("units", new JSONObject().put("USD", cash)));
        var payload = new JSONObject().put("facts", new JSONObject().put("us-gaap", gaap));
        var history = UsFinancialFacts.meterHistory(payload, LocalDate.of(2026, 3, 1));
        assertEquals(List.of(number("3"), number("2"), number("1")), history.annualEps());
        assertEquals(Integer.valueOf(0), history.cash());
        assertTrue(UsFinancialFacts.meterHistory(payload, LocalDate.of(2026, 2, 5)).annualEps().isEmpty());
    }

    @Test public void malformedOptionalMeterFieldsLeaveUsFinanceAndNotificationEvidenceUsable() throws Exception {
        var day = LocalDate.of(2026, 11, 19);
        var row = new JSONObject().put("symbol", "TEST").put("exchange", "NYSE").put("cik", 123)
                .put("share_date", "2026-10-31").put("profit", "100").put("equity", "1000").put("shares", "100");
        var prices = Map.of("TEST", number("5"));
        var fx = new UsScreen.Fx(day, 150);
        var hash = "a".repeat(64);
        var normal = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, hash, new JSONArray().put(row),
                prices, fx, Map.of());
        row.put("meter_eps", new JSONArray().put("1.5").put("broken")).put("meter_cash", "invalid");
        var repaired = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, hash, new JSONArray().put(row),
                prices, fx, Map.of());
        assertEquals(UsReferenceAlerts.read(normal), UsReferenceAlerts.read(repaired));
        var meter = repaired.getJSONObject("reference_screen").getJSONObject("meter_rows")
                .getJSONArray("NYSE:123:TEST");
        assertEquals(1, meter.getInt(1));
        assertEquals(3, meter.getInt(2));
    }

    private static JSONObject fact(int year, int value, String filed) throws Exception {
        return new JSONObject().put("start", year + "-01-01").put("end", year + "-12-31")
                .put("val", value).put("filed", filed).put("form", "10-K")
                .put("accn", "0000000123-26-000001");
    }

    private static BigDecimal number(String text) { return new BigDecimal(text); }
}
