package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertThrows;
import org.json.JSONException;

public class UsFinancialFactsTest {
    private static final String Q = "0000000001-26-000001";
    private static final String K = "0000000001-26-000002";
    private static final LocalDate SESSION = LocalDate.parse("2026-11-17");

    @Test public void usesMatchingFiscalYearToDateWindowsAndCoverShares() throws Exception {
        var facts = UsFinancialFacts.read(payload(), 1, SESSION);
        assertEquals(new BigDecimal("110"), facts.profit());
        assertEquals(new BigDecimal("350"), facts.equity());
        assertEquals(new BigDecimal("40"), facts.shares());
        assertEquals(LocalDate.parse("2026-10-13"), facts.shareDate());
        assertEquals(Q, facts.accession());
    }

    @Test public void usesLatestCoverDateWithoutMixingConflictingShareClasses() throws Exception {
        var document = payload();
        var cover = document.getJSONObject("facts").getJSONObject("dei").getJSONObject("EntityCommonStockSharesOutstanding")
                .getJSONObject("units").getJSONArray("shares");
        cover.put(row(null, "2026-10-01", "2026-10-20", Q, "10-Q", 39));
        assertEquals(new BigDecimal("40"), UsFinancialFacts.read(document, 1, SESSION).shares());
        cover.put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 41));
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void sameDayFilingAndDuplicateShareCountsHold() throws Exception {
        assertNull(UsFinancialFacts.read(payload(), 1, LocalDate.parse("2026-10-20")));
        var duplicate = payload();
        duplicate.getJSONObject("facts").getJSONObject("dei").getJSONObject("EntityCommonStockSharesOutstanding")
                .getJSONObject("units").getJSONArray("shares")
                .put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 41));
        assertNull(UsFinancialFacts.read(duplicate, 1, SESSION));
        assertEquals("shares_for_filing_ambiguous", UsFinancialFacts.assess(duplicate, 1, SESSION).hold());
        assertEquals("parent_equity_stale", UsFinancialFacts.assess(payload(), 1, SESSION.plusDays(151)).hold());
        assertThrows(JSONException.class, () -> UsFinancialFacts.read(payload(), 42, SESSION));
    }

    @Test public void usesBalanceSheetSharesOnlyWithMatchingAccessionAndPeriod() throws Exception {
        var document = payload();
        var sections = document.getJSONObject("facts");
        var gaap = sections.getJSONObject("us-gaap");
        var shares = new JSONArray().put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 38));
        gaap.put("CommonStockSharesOutstanding", units("shares", shares));

        assertEquals("cover", UsFinancialFacts.read(document, 1, SESSION).sharesBasis());
        var cover = sections.getJSONObject("dei").getJSONObject("EntityCommonStockSharesOutstanding")
                .getJSONObject("units").getJSONArray("shares");
        cover.put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 41));
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
        sections.remove("dei");
        var facts = UsFinancialFacts.read(document, 1, SESSION);
        assertEquals("balance_sheet", facts.sharesBasis());
        assertEquals(LocalDate.parse("2026-09-30"), facts.shareDate());
        assertEquals(new BigDecimal("38"), facts.shares());

        shares.getJSONObject(0).put("accn", K);
        var held = UsFinancialFacts.assess(document, 1, SESSION);
        assertEquals("shares_for_filing_missing", held.hold());
        assertEquals(Q, held.filing().accession());
        assertEquals(LocalDate.parse("2026-09-30"), held.filing().periodEnd());
    }

    @Test public void acceptsMatchingDollarFactsFromAForeignAnnualReport() throws Exception {
        var document = payload();
        var sections = document.getJSONObject("facts");
        var gaap = sections.getJSONObject("us-gaap");
        var equity = row(null, "2026-08-31", "2026-10-20", K, "20-F", 350);
        var profit = row("2025-09-01", "2026-08-31", "2026-10-20", K, "20-F", 75);
        var shares = row(null, "2026-10-13", "2026-10-20", K, "20-F", 40);
        gaap.put("StockholdersEquity", units("USD", new JSONArray().put(equity)));
        gaap.put("NetIncomeLoss", units("USD", new JSONArray().put(profit)));
        sections.getJSONObject("dei").put("EntityCommonStockSharesOutstanding", units("shares", new JSONArray().put(shares)));
        var result = UsFinancialFacts.read(document, 1, SESSION);
        assertEquals(new BigDecimal("75"), result.profit());
        assertEquals(new BigDecimal("350"), result.equity());
        assertEquals(new BigDecimal("40"), result.shares());
        assertNull(UsFinancialFacts.read(document, 1, LocalDate.parse("2026-10-20")));

        shares.put("form", "6-K");
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
        shares.put("form", "40-F"); equity.put("form", "40-F"); profit.put("form", "40-F");
        assertEquals(new BigDecimal("40"), UsFinancialFacts.read(document, 1, SESSION).shares());
        profit.put("start", "2026-01-01");
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void reconcilesParentEquityAndProfitOnlyFromMatchedComponents() throws Exception {
        var document = payload();
        var gaap = document.getJSONObject("facts").getJSONObject("us-gaap");
        gaap.remove("StockholdersEquity");
        gaap.put("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", units("USD",
                new JSONArray().put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 380))));
        var minority = new JSONArray().put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 30));
        gaap.put("MinorityInterest", units("USD", minority));
        var profits = gaap.getJSONObject("NetIncomeLoss").getJSONObject("units").getJSONArray("USD");
        profits.remove(2);
        gaap.put("ProfitLoss", units("USD", new JSONArray()
                .put(row("2026-01-01", "2026-09-30", "2026-10-20", Q, "10-Q", 75))));
        var minorityProfit = new JSONArray()
                .put(row("2026-01-01", "2026-09-30", "2026-10-20", Q, "10-Q", 5));
        gaap.put("NetIncomeLossAttributableToNoncontrollingInterest", units("USD", minorityProfit));

        var facts = UsFinancialFacts.read(document, 1, SESSION);
        assertEquals(new BigDecimal("350"), facts.equity());
        assertEquals(new BigDecimal("110"), facts.profit());
        assertTrue(facts.reconciledParentAmounts());

        minorityProfit.getJSONObject(0).put("start", "2026-07-01");
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
        minorityProfit.getJSONObject(0).put("start", "2026-01-01");
        minority.put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 31));
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void usesCommonStockholderIncomeOnlyWhenAllPeriodsMatch() throws Exception {
        var document = payload();
        var gaap = document.getJSONObject("facts").getJSONObject("us-gaap");
        var direct = gaap.remove("NetIncomeLoss");
        var alternate = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "10-K", 92))
                .put(row("2025-01-01", "2025-09-30", "2026-10-20", Q, "10-Q", 54))
                .put(row("2026-01-01", "2026-09-30", "2026-10-20", Q, "10-Q", 61));
        gaap.put("NetIncomeLossAvailableToCommonStockholdersBasic", units("USD", alternate));
        var facts = UsFinancialFacts.read(document, 1, SESSION);
        assertEquals(new BigDecimal("99"), facts.profit());
        assertEquals("income_available_to_common", facts.profitBasis());

        gaap.put("NetIncomeLoss", direct);
        assertEquals(new BigDecimal("110"), UsFinancialFacts.read(document, 1, SESSION).profit());

        var net = gaap.getJSONObject("NetIncomeLoss").getJSONObject("units").getJSONArray("USD");
        net.remove(2);
        alternate.remove(1);
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void addsOnlyFourConsecutiveFiscalQuarters() throws Exception {
        var document = payload();
        var gaap = document.getJSONObject("facts").getJSONObject("us-gaap");
        var quarters = new JSONArray()
                .put(row("2025-10-01", "2025-12-31", "2026-02-01", K, "10-K", 10))
                .put(row("2026-01-01", "2026-03-31", "2026-05-01", "0000000001-26-000003", "10-Q", 20))
                .put(row("2026-04-01", "2026-06-30", "2026-08-01", "0000000001-26-000004", "10-Q", 30))
                .put(row("2026-07-01", "2026-09-30", "2026-10-20", Q, "10-Q", 40));
        gaap.put("NetIncomeLoss", units("USD", quarters));
        var result = UsFinancialFacts.read(document, 1, SESSION);
        assertEquals(new BigDecimal("100"), result.profit());
        assertEquals("parent_four_quarters", result.profitBasis());

        quarters.getJSONObject(2).put("start", "2026-04-02");
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
        quarters.getJSONObject(2).put("start", "2026-04-01");
        quarters.put(row("2026-04-01", "2026-06-30", "2026-08-01", "0000000001-26-000004", "10-Q", 31));
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void derivesFourthQuarterFromMatchingAnnualAndNineMonthPeriods() throws Exception {
        var document = payload();
        var gaap = document.getJSONObject("facts").getJSONObject("us-gaap");
        var quarters = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "10-K", 90))
                .put(row("2025-01-01", "2025-09-30", "2025-10-20", "0000000001-25-000002", "10-Q", 80))
                .put(row("2026-01-01", "2026-03-31", "2026-05-01", "0000000001-26-000003", "10-Q", 20))
                .put(row("2026-04-01", "2026-06-30", "2026-08-01", "0000000001-26-000004", "10-Q", 30))
                .put(row("2026-07-01", "2026-09-30", "2026-10-20", Q, "10-Q", 40));
        gaap.put("NetIncomeLoss", units("USD", quarters));
        assertEquals(new BigDecimal("100"), UsFinancialFacts.read(document, 1, SESSION).profit());
        quarters.getJSONObject(1).put("start", "2025-01-02");
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void numericallyIdenticalRepeatedSharesDoNotBlockFinancials() throws Exception {
        var document = payload();
        var shares = document.getJSONObject("facts").getJSONObject("dei")
                .getJSONObject("EntityCommonStockSharesOutstanding").getJSONObject("units").getJSONArray("shares");
        shares.put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 40)
                .put("val", new BigDecimal("40.00")));
        assertEquals(0, new BigDecimal("40").compareTo(UsFinancialFacts.read(document, 1, SESSION).shares()));
        shares.put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 41));
        assertNull(UsFinancialFacts.read(document, 1, SESSION));
    }

    @Test public void independentCashAndBalanceEvidenceSurvivesMissingEps() throws Exception {
        var document = payload();
        var gaap = document.getJSONObject("facts").getJSONObject("us-gaap");
        gaap.put("StockholdersEquity", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "10-K", 350))));
        gaap.put("Assets", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "10-K", 700))));
        gaap.put("NetCashProvidedByUsedInOperatingActivities", units("USD", new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "10-K", 50))
                .put(row("2024-01-01", "2024-12-31", "2026-02-01", K, "10-K", 40))));
        var history = UsFinancialFacts.meterHistory(document, SESSION);
        assertTrue(history.annualEps().isEmpty());
        assertEquals(Integer.valueOf(100), history.cash());
        assertEquals(Integer.valueOf(100), history.balance());
        gaap.remove("Assets");
        assertNull(UsFinancialFacts.meterHistory(document, SESSION).balance());
    }

    @Test public void foreignAnnualMeterUsesOnlyMatchingDollarEvidence() throws Exception {
        var document = new JSONObject().put("cik", 1).put("facts", new JSONObject());
        var gaap = new JSONObject();
        document.getJSONObject("facts").put("us-gaap", gaap);
        var eps = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "20-F", 5))
                .put(row("2024-01-01", "2024-12-31", "2026-02-01", K, "20-F", 4))
                .put(row("2023-01-01", "2023-12-31", "2026-02-01", K, "20-F", 3));
        gaap.put("EarningsPerShareBasic", units("USD/shares", eps));
        gaap.put("StockholdersEquity", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "20-F", 350))));
        gaap.put("Assets", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "20-F", 700))));
        var cash = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "20-F", 50))
                .put(row("2024-01-01", "2024-12-31", "2026-02-01", K, "20-F", 40));
        gaap.put("NetCashProvidedByUsedInOperatingActivities", units("USD", cash));
        var result = UsFinancialFacts.meterHistory(document, SESSION);
        assertEquals(3, result.annualEps().size());
        assertEquals(Integer.valueOf(100), result.cash());
        assertEquals(Integer.valueOf(100), result.balance());
        cash.getJSONObject(1).put("form", "10-K");
        assertNull(UsFinancialFacts.meterHistory(document, SESSION).cash());
        assertTrue(UsFinancialFacts.meterHistory(document, LocalDate.parse("2026-02-01")).annualEps().isEmpty());
    }

    @Test public void independentIfrsAnnualEvidenceCanReachTheHighestFlexibleTier() throws Exception {
        var document = new JSONObject().put("cik", 1).put("facts", new JSONObject());
        var ifrs = new JSONObject();
        document.getJSONObject("facts").put("ifrs-full", ifrs);
        var eps = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "20-F", 5))
                .put(row("2024-01-01", "2024-12-31", "2026-02-01", K, "20-F", 4))
                .put(row("2023-01-01", "2023-12-31", "2026-02-01", K, "20-F", 3));
        ifrs.put("BasicEarningsLossPerShare", units("USD/shares", eps));
        ifrs.put("CashFlowsFromUsedInOperatingActivities", units("USD", new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "20-F", 50))
                .put(row("2024-01-01", "2024-12-31", "2026-02-01", K, "20-F", 40))));
        ifrs.put("Assets", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "20-F", 700))));
        ifrs.put("EquityAttributableToOwnersOfParent", units("USD", new JSONArray()
                .put(row(null, "2025-12-31", "2026-02-01", K, "20-F", 350))));
        var result = UsFinancialFacts.partialValue(document, 1, SESSION);
        org.junit.Assert.assertNotNull(result);
        assertEquals(3, FlexibleValueMeter.assess(java.math.BigDecimal.TEN,
                result.eps(), result.cash(), result.balance()).level(ValueAlertMeter.DEFAULT));
        assertNull(UsFinancialFacts.partialValue(document, 2, SESSION));
        assertNull(UsFinancialFacts.partialValue(document, 1, LocalDate.parse("2026-02-01")));
        ifrs.put("BasicEarningsLossPerShare", units("EUR/shares", eps));
        assertNull(UsFinancialFacts.partialValue(document, 1, SESSION));
    }

    private static JSONObject payload() throws JSONException {
        var equity = new JSONArray().put(row(null, "2026-09-30", "2026-10-20", Q, "10-Q", 350));
        var profit = new JSONArray()
                .put(row("2025-01-01", "2025-12-31", "2026-02-01", K, "10-K", 100))
                .put(row("2025-01-01", "2025-09-30", "2026-10-20", Q, "10-Q", 60))
                .put(row("2026-01-01", "2026-09-30", "2026-10-20", Q, "10-Q", 70))
                .put(row("2026-07-01", "2026-09-30", "2026-10-20", Q, "10-Q", 20));
        var shares = new JSONArray().put(row(null, "2026-10-13", "2026-10-20", Q, "10-Q", 40));
        return new JSONObject().put("cik", 1).put("facts", new JSONObject()
                .put("us-gaap", new JSONObject().put("StockholdersEquity", units("USD", equity))
                        .put("NetIncomeLoss", units("USD", profit)))
                .put("dei", new JSONObject().put("EntityCommonStockSharesOutstanding", units("shares", shares))));
    }

    private static JSONObject units(String unit, JSONArray facts) throws JSONException {
        return new JSONObject().put("units", new JSONObject().put(unit, facts));
    }

    private static JSONObject row(String start, String end, String filed, String accn, String form, int value)
            throws JSONException {
        var row = new JSONObject().put("end", end).put("filed", filed).put("accn", accn)
                .put("form", form).put("val", value);
        if (start != null) row.put("start", start);
        return row;
    }
}
