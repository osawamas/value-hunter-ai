package jp.valuehunter.privatewatch;

import org.junit.Test;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import static org.junit.Assert.*;

/** Regression checks for replay and retry gates; no network or notifications are sent. */
public class PriceOnlyReplaySafetyTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);
    private static final LocalDate PREVIOUS = DAY.minusDays(1);

    @Test public void rapidAndBudgetReasonsAreIndependentOnSameTradingDay() {
        var rapid = List.of(new PriceOnlyScreen.RapidMove("1001", new BigDecimal("-8")));
        var budget = List.of(new PriceOnlyScreen.BudgetEntry("1001", new BigDecimal("90000")));
        assertEquals(1, JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, DAY,
                rapid, Set.of("price-budget:1001")).size());
        assertEquals(1, JpxWatchWorker.pendingBudget(PREVIOUS.minusDays(1), DAY, DAY,
                budget, Set.of("price-rapid:1001")).size());
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, DAY,
                rapid, Set.of("price-rapid:1001")).isEmpty());
        assertTrue(JpxWatchWorker.pendingBudget(PREVIOUS.minusDays(1), DAY, DAY,
                budget, Set.of("price-budget:1001")).isEmpty());
    }

    @Test public void failedDeliveryMayRetryButAcknowledgedDeliveryCannotRepeat() {
        var rapid = List.of(new PriceOnlyScreen.RapidMove("1001", new BigDecimal("10")));
        assertEquals(1, JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, DAY,
                rapid, Set.of()).size());
        assertEquals(1, JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, DAY,
                rapid, Set.of()).size());
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, DAY,
                rapid, Set.of("price-rapid:1001")).isEmpty());
    }

    @Test public void firstObservationAndStaleReportNeverNotify() {
        var rapid = List.of(new PriceOnlyScreen.RapidMove("1001", new BigDecimal("10")));
        assertTrue(JpxWatchWorker.pendingRapid(null, null, DAY, rapid, Set.of()).isEmpty());
        assertTrue(JpxWatchWorker.pendingRapid(DAY, DAY, DAY, rapid, Set.of()).isEmpty());
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS.minusDays(1), DAY, PREVIOUS,
                rapid, Set.of()).isEmpty());
    }
}
