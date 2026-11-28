package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

public class UsDeviceFinancialBreakdownTest {
    @Test public void eachIssuerHasExactlyOneExclusionReason() throws Exception {
        var rows = new JSONArray();
        rows.put(financial("AAA",1,1000,5000,6000));     // 100 shares affordable, priority
        rows.put(financial("BBB",2,100000,100,100));     // expensive one share, budget excluded
        rows.put(financial("CCC",3,1000,-200,3000));    // negative profit => held
        rows.put(financial("DDD",4,1000,5000,6000));    // missing price
        rows.put(financial("EEE",5,1000,5000,6000));    // split hold
        rows.put(financial("FFF",6,1000,5,5));          // expensive valuation
        var closes=Map.of("AAA",new BigDecimal("5"),"BBB",new BigDecimal("1000"),
                "CCC",new BigDecimal("10"),"EEE",new BigDecimal("5"),"FFF",new BigDecimal("10"));
        var ledger=UsDeviceFinancials.screen(LocalDate.parse("2026-11-23"),UsDoltCloses.SOURCE,
                "a".repeat(64),rows,closes,new UsScreen.Fx(LocalDate.parse("2026-11-23"),150),
                Map.of("EEE",LocalDate.parse("2026-10-01")));
        JSONObject d=ledger.getJSONObject("reference_screen").getJSONObject("diagnostics");
        assertEquals(6,d.getInt("financial_records"));
        assertEquals(1,d.getInt("missing_close"));
        assertEquals(1,d.getInt("split_hold"));
        assertEquals(1,d.getInt("unusable_financials"));
        assertEquals(1,d.getInt("outside_budget"));
        assertEquals(1,d.getInt("outside_valuation"));
        assertEquals(1,d.getInt("priority"));
        assertEquals(0,d.getInt("reference"));
        assertEquals(1,d.getInt("affordable_100"));
        assertEquals(1,d.getInt("single_share"));
        assertEquals(1,d.getInt("non_positive_profit_only"));
        assertEquals(0,d.getInt("non_positive_equity_only"));
        assertEquals(0,d.getInt("non_positive_both"));
        assertEquals(0,d.getInt("other_financial_hold"));
        assertEquals(3,ledger.getJSONObject("reference_screen").getJSONArray("observations").length());
    }
    @Test public void nonPositiveFinancialReasonsAndBudgetBoundaryReconcile() throws Exception {
        var day = LocalDate.parse("2026-11-23");
        var rows = new JSONArray().put(financial("LOSS",1,1000,-1,1000))
                .put(financial("EQUITY",2,1000,1000,0))
                .put(financial("BOTH",3,1000,0,-1))
                .put(financial("LIMIT",4,1000,1000,1000))
                .put(financial("OVER",5,1000,1000,1000));
        var prices = Map.of("LOSS",BigDecimal.ONE,"EQUITY",BigDecimal.ONE,"BOTH",BigDecimal.ONE,
                "LIMIT",new BigDecimal("1000"),"OVER",new BigDecimal("1000.01"));
        var ledger = UsDeviceFinancials.screen(day,UsDoltCloses.SOURCE,"b".repeat(64),rows,prices,
                new UsScreen.Fx(day,100),Map.of());
        var diag = ledger.getJSONObject("reference_screen").getJSONObject("diagnostics");
        assertEquals(3,diag.getInt("unusable_financials"));
        assertEquals(1,diag.getInt("non_positive_profit_only"));
        assertEquals(1,diag.getInt("non_positive_equity_only"));
        assertEquals(1,diag.getInt("non_positive_both"));
        assertEquals(1,diag.getInt("single_share"));
        assertEquals(1,diag.getInt("outside_budget"));
    }

    @Test public void strictAndPartialCoverageAreSeparateAndBudgetFiltered() throws Exception {
        var day=LocalDate.parse("2026-11-23");
        var rows=new JSONArray().put(financial("AAA",1,1000,5000,6000));
        for(String code:java.util.List.of("PART","OVER","SPLIT")) {
            rows.put(new JSONObject().put("symbol",code).put("exchange","NYSE").put("cik",rows.length()+1)
                .put("partial_value",true).put("share_date","2026-09-30")
                .put("meter_eps",new JSONArray().put("2").put("1.9").put("1.8"))
                .put("meter_cash",100).put("meter_balance",100));
        }
        var d=UsDeviceFinancials.screen(day,UsDoltCloses.SOURCE,"a".repeat(64),rows,
            Map.of("AAA",new BigDecimal("5"),"PART",new BigDecimal("10"),
                "OVER",new BigDecimal("1000"),"SPLIT",new BigDecimal("10")),
            new UsScreen.Fx(day,150),Map.of("SPLIT",day))
            .getJSONObject("reference_screen").getJSONObject("diagnostics");
        assertEquals(1,d.getInt("strict_assessed"));
        assertEquals(2,d.getInt("partial_assessed"));
        assertEquals(3,d.getInt("total_assessed"));
        assertEquals(1,d.getInt("partial_eligible_default"));
        assertEquals(1,d.getJSONArray("flexible_tiers").getInt(2));
        assertEquals(1,d.getInt("split_hold"));
    }

    @Test public void incompletePartialRowsCannotAnchorLegacyEntrants() throws Exception {
        var day = LocalDate.parse("2026-11-23");
        var partial = new JSONObject().put("symbol", "AAA").put("exchange", "NYSE").put("cik", 1)
                .put("partial_value", true).put("share_date", "2026-09-30")
                .put("meter_eps", new JSONArray().put("2"));
        var prices = Map.of("AAA", BigDecimal.valueOf(5));
        var hash = "a".repeat(64);
        var incomplete = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, hash,
                new JSONArray().put(partial), prices, new UsScreen.Fx(day, 150), Map.of());
        assertTrue(UsReferenceAlerts.read(incomplete).rows().isEmpty());
        assertEquals(1, incomplete.getJSONObject("reference_screen").getJSONObject("diagnostics")
                .getInt("partial_insufficient"));

        partial.put("meter_eps", new JSONArray().put("2").put("1.9"));
        var complete = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, hash,
                new JSONArray().put(partial), prices, new UsScreen.Fx(day, 150), Map.of());
        var prior = UsReferenceAlerts.read(complete);
        assertEquals("partial_assessed", prior.rows().get("AAA").status());
        assertEquals(1, complete.getJSONObject("reference_screen").getJSONObject("meter_rows").length());

        var next = day.plusDays(1);
        var strict = UsDeviceFinancials.screen(next, UsDoltCloses.SOURCE, hash,
                new JSONArray().put(financial("AAA", 1, 1000, 5000, 6000)),
                prices, new UsScreen.Fx(next, 150), Map.of());
        assertTrue(UsReferenceAlerts.entrants(prior, UsReferenceAlerts.read(strict)).isEmpty());
    }

    @Test public void currentLossUsesBookAndCashOnlyWithGrowingAnnualEarnings() throws Exception {
        var day = LocalDate.parse("2026-11-23");
        var row = financial("LOSS", 1, 1000, -10, 4000)
                .put("meter_eps", new JSONArray().put("2").put("1"))
                .put("meter_cash", 100);
        var prices = Map.of("LOSS", BigDecimal.ONE);
        var fx = new UsScreen.Fx(day, 150);
        var records = new JSONArray().put(row);
        var ledger = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, "a".repeat(64), records,
                prices, fx, Map.of());
        var meter = ledger.getJSONObject("reference_screen").getJSONObject("meter_rows");
        assertEquals(1, meter.getJSONArray(UsReferenceAlerts.meterKey("NYSE", 1, "LOSS")).getInt(1));
        row.put("meter_cash", 50);
        ledger = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, "a".repeat(64), records,
                prices, fx, Map.of());
        assertEquals(0, ledger.getJSONObject("reference_screen").getJSONArray("observations").length());
    }

    @Test public void deepValueScoreDifferentiatesMultiplesAndFilingAge() throws Exception {
        var day = LocalDate.parse("2026-11-27");
        var row = new JSONObject().put("meter_eps", new JSONArray().put("2").put("2").put("2"))
                .put("meter_cash", 100).put("meter_balance", 100).put("filed", "2026-10-01");
        var fresh = UsDeviceFinancials.flexibleUsScore(row, new BigDecimal("6"), day);
        assertTrue(fresh.points() > UsDeviceFinancials.flexibleUsScore(row, new BigDecimal("12"), day).points());
        row.put("filed", "2026-04-01");
        assertTrue(fresh.points() > UsDeviceFinancials.flexibleUsScore(row, new BigDecimal("6"), day).points());
        assertEquals(3, fresh.ceiling());
    }

    @Test public void increasingCashAndSalesRecoverACompanyWithoutPositiveEarnings() throws Exception {
        var day = LocalDate.parse("2026-11-23");
        var row = financial("LOSS", 1, 1000, -10, 4000)
                .put("meter_balance", 100)
                .put("operating_recovery", new JSONObject().put("end", "2025-12-31")
                        .put("cash", "250").put("prior_cash", "200").put("sales", "2200").put("prior_sales", "2100"));
        var prices = Map.of("LOSS", BigDecimal.ONE);
        var fx = new UsScreen.Fx(day, 150);
        var ledger = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, "a".repeat(64),
                new JSONArray().put(row), prices, fx, Map.of());
        var screen = ledger.getJSONObject("reference_screen");
        assertEquals(1, screen.getJSONObject("diagnostics").getInt("operating_recovery_assessed"));
        assertEquals(2, screen.getJSONObject("meter_rows").getJSONArray(
                UsReferenceAlerts.meterKey("NYSE", 1, "LOSS")).getInt(1));
        assertEquals(0, UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, "a".repeat(64),
                new JSONArray().put(row), prices, fx, Map.of("LOSS", day))
                .getJSONObject("reference_screen").getJSONObject("diagnostics").getInt("operating_recovery_assessed"));
    }

    private static JSONObject financial(String symbol,int cik,int shares,int profit,int equity)throws Exception {
        return new JSONObject().put("symbol",symbol).put("exchange","NYSE").put("cik",cik)
                .put("shares",String.valueOf(shares)).put("profit",String.valueOf(profit))
                .put("equity",String.valueOf(equity)).put("share_date","2026-09-30")
                .put("meter_eps",new JSONArray()).put("meter_cash",new JSONArray());
    }
}
