package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class PriceOnlyScreenTest {
    @Test public void budgetCrossingIncludesTheLimitAndExcludesMissingPricesAndFinanciallyAssessedStocks() {
        Map<String, BigDecimal> previous = Map.of(
                "1001", new BigDecimal("1000.01"), "1002", new BigDecimal("1150"),
                "1003", new BigDecimal("995"), "1004", new BigDecimal("1100"),
                "1005", new BigDecimal("1100"), "1006", new BigDecimal("1100"));
        Map<String, BigDecimal> latest = Map.of(
                "1001", new BigDecimal("1000.00"), "1002", new BigDecimal("950"),
                "1003", new BigDecimal("995"), "1004", new BigDecimal("1000.01"),
                "1006", BigDecimal.ZERO);
        var result = PriceOnlyScreen.budgetEntries(previous.keySet(), Set.of("1002"), previous::get, latest::get);
        assertEquals(3, result.assessed());
        assertEquals(List.of("1001"), result.entered().stream().map(PriceOnlyScreen.BudgetEntry::code).toList());
        assertEquals(0, result.entered().get(0).yen().compareTo(new BigDecimal("100000")));
    }

    @Test public void priceAlertsHaveTheirOwnSameSessionDeduplicationAndSkipTheInitialBaseline() {
        var today = LocalDate.of(2026, 11, 17);
        var previous = today.minusDays(1);
        var entrants = List.of(new PriceOnlyScreen.BudgetEntry("1001", new BigDecimal("98000")));
        assertTrue(JpxWatchWorker.pendingBudget(null, null, today, entrants, Set.of()).isEmpty());
        assertEquals(entrants, JpxWatchWorker.pendingBudget(previous, previous, today, entrants, Set.of()));
        assertEquals(entrants, JpxWatchWorker.pendingBudget(previous, today, today, entrants, Set.of("1001")));
        assertTrue(JpxWatchWorker.pendingBudget(previous, today, today, entrants, Set.of("price-budget:1001")).isEmpty());
    }
    @Test public void rapidThresholdUsesExactMoveNotRoundedDisplayPercent() {
        Map<String, BigDecimal> before = Map.of("below", new BigDecimal("100"),
                "exact", new BigDecimal("100"), "above", new BigDecimal("100"));
        Map<String, BigDecimal> after = Map.of("below", new BigDecimal("107.99996"),
                "exact", new BigDecimal("108"), "above", new BigDecimal("108.00001"));
        var found = PriceOnlyScreen.rapidMoves(before.keySet(), Set.of(), before::get, after::get,
                code -> true, code -> true, new BigDecimal("8"));
        assertEquals(List.of("above", "exact"),
                found.stream().map(PriceOnlyScreen.RapidMove::code).toList());
    }

    @Test public void rapidMoveRequiresBothIndependentEventChecksAndSkipsFinancialStocks() {
        Map<String, BigDecimal> before = Map.of(
                "2001", new BigDecimal("100"), "2002", new BigDecimal("100"),
                "2003", new BigDecimal("100"), "2004", new BigDecimal("100"),
                "2005", new BigDecimal("100"), "2006", new BigDecimal("100"));
        Map<String, BigDecimal> after = Map.of(
                "2001", new BigDecimal("108"), "2002", new BigDecimal("92"),
                "2003", new BigDecimal("115"), "2004", new BigDecimal("115"),
                "2005", new BigDecimal("115"), "2006", new BigDecimal("107.99"));
        var result = PriceOnlyScreen.rapidMoves(before.keySet(), Set.of("2005"),
                before::get, after::get,
                code -> !code.equals("2003"),
                code -> !code.equals("2004"),
                new BigDecimal("8"));
        assertEquals(List.of("2001", "2002"),
                result.stream().map(PriceOnlyScreen.RapidMove::code).toList());
        assertEquals(0, result.get(0).percent().compareTo(new BigDecimal("8")));
        assertEquals(0, result.get(1).percent().compareTo(new BigDecimal("-8")));
    }
}
