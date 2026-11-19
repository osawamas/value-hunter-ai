package jp.valuehunter.privatewatch;

import org.junit.Test;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;
import static org.junit.Assert.*;

public class PriceOnlyRapidMoveTest {
    @Test public void onlyUnverifiedFinanceWithCompleteEventFreeIntervalMayPass() {
        var before = Map.of("1001", new BigDecimal("100"), "1002", new BigDecimal("100"),
                "1003", new BigDecimal("100"), "1004", new BigDecimal("100"));
        var after = Map.of("1001", new BigDecimal("110"), "1002", new BigDecimal("80"),
                "1003", new BigDecimal("140"), "1004", new BigDecimal("101"));
        var result = PriceOnlyScreen.rapidMoves(before.keySet(), Set.of("1003"),
                before::get, after::get, code -> code.equals("1001") || code.equals("1004"),
                code -> code.equals("1001") || code.equals("1002"), new BigDecimal("8"));
        assertEquals(1, result.size());
        assertEquals("1001", result.get(0).code());
        assertEquals(0, result.get(0).percent().compareTo(new BigDecimal("10")));
    }

    @Test public void heldFinancialRegistrationMustNotBecomePriceOnlyAlert() {
        var before = Map.of("1001", new BigDecimal("1200"), "1002", new BigDecimal("1200"));
        var after = Map.of("1001", new BigDecimal("900"), "1002", new BigDecimal("900"));
        var result = PriceOnlyScreen.budgetEntries(before.keySet(), Set.of("1001"),
                before::get, after::get);
        assertEquals(1, result.assessed());
        assertEquals(1, result.entered().size());
        assertEquals("1002", result.entered().get(0).code());
    }

    @Test public void unknownDividendCoverageMustHoldEvenWhenSplitsAreCleared() {
        var before = Map.of("1001", new BigDecimal("100"));
        var after = Map.of("1001", new BigDecimal("130"));
        assertTrue(PriceOnlyScreen.rapidMoves(before.keySet(), Set.of(), before::get, after::get,
                code -> true, code -> false, new BigDecimal("8")).isEmpty());
    }

    @Test public void missingOrNonpositivePricesAndUnknownEventsAreHeld() {
        var before = Map.of("1001", new BigDecimal("100"), "1002", BigDecimal.ZERO);
        var after = Map.of("1001", new BigDecimal("200"), "1002", new BigDecimal("50"));
        assertTrue(PriceOnlyScreen.rapidMoves(before.keySet(), Set.of(),
                before::get, after::get, code -> false, code -> true, new BigDecimal("8")).isEmpty());
        assertTrue(PriceOnlyScreen.rapidMoves(before.keySet(), Set.of(),
                before::get, after::get, code -> true, code -> true, new BigDecimal("8"))
                .stream().noneMatch(x -> x.code().equals("1002")));
    }
}
