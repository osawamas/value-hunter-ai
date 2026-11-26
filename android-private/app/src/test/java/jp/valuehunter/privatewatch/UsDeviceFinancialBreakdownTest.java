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

    private static JSONObject financial(String symbol,int cik,int shares,int profit,int equity)throws Exception {
        return new JSONObject().put("symbol",symbol).put("exchange","NYSE").put("cik",cik)
                .put("shares",String.valueOf(shares)).put("profit",String.valueOf(profit))
                .put("equity",String.valueOf(equity)).put("share_date","2026-09-30")
                .put("meter_eps",new JSONArray()).put("meter_cash",new JSONArray());
    }
}
