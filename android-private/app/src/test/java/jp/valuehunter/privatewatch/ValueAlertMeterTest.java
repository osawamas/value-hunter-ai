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
        assertEquals(3, ValueAlertMeter.assessUs(number("6"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 100, null, 100)
                .level(ValueAlertMeter.DEFAULT));
        var insufficientAbsolute = ValueAlertMeter.assessUs(number("8"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 100, null, 100);
        assertEquals(2, insufficientAbsolute.level(ValueAlertMeter.DEFAULT));
        assertEquals(2, ValueAlertMeter.assessUs(number("6"), number("1"), number("12"),
                List.of(number("3"), number("2"), number("1")), 100, null, null)
                .level(ValueAlertMeter.DEFAULT));
        var unavailable = ValueAlertMeter.assess(number("6"), number("1"), number("12"),
                List.of(), null, null, null);
        assertEquals(1, unavailable.level(ValueAlertMeter.DEFAULT));
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

    @Test public void secAnnualAssetsAndEquityEnableHighestTierOnlyWhenVerified() throws Exception {
        var eps = new JSONArray();
        var cash = new JSONArray();
        for(int year=2023;year<=2025;year++){
            eps.put(fact(year,year-2022,"2026-02-05"));
            cash.put(fact(year,100,"2026-02-05"));
        }
        JSONObject assets=new JSONObject().put("end","2025-12-31").put("val",1000)
                .put("filed","2026-02-05").put("form","10-K")
                .put("accn","0000000123-26-000001");
        JSONObject equity=new JSONObject(assets.toString()).put("val",500);
        JSONObject gaap=new JSONObject()
                .put("EarningsPerShareBasic",new JSONObject().put("units",new JSONObject().put("USD/shares",eps)))
                .put("NetCashProvidedByUsedInOperatingActivities",
                        new JSONObject().put("units",new JSONObject().put("USD",cash)))
                .put("Assets",new JSONObject().put("units",new JSONObject().put("USD",new JSONArray().put(assets))))
                .put("StockholdersEquity",new JSONObject().put("units",new JSONObject().put("USD",new JSONArray().put(equity))));
        var payload=new JSONObject().put("facts",new JSONObject().put("us-gaap",gaap));
        var evidence=UsFinancialFacts.meterHistory(payload,LocalDate.of(2026,3,1));
        assertEquals(Integer.valueOf(100),evidence.cash());
        assertEquals(Integer.valueOf(100),evidence.balance());
        var top=ValueAlertMeter.assessUs(number("6"),number("1"),number("12"),
                evidence.annualEps(),evidence.cash(),null,evidence.balance());
        assertEquals(3,top.level(ValueAlertMeter.DEFAULT));
        assertTrue(top.points()>=85);
        gaap.getJSONObject("Assets").getJSONObject("units").getJSONArray("USD").getJSONObject(0)
                .put("filed","2026-03-05");
        var missing=UsFinancialFacts.meterHistory(payload,LocalDate.of(2026,3,1));
        assertEquals(null,missing.balance());
        assertEquals(2,ValueAlertMeter.assessUs(number("6"),number("1"),number("12"),
                missing.annualEps(),missing.cash(),null,missing.balance()).level(ValueAlertMeter.DEFAULT));
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
