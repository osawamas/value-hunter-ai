package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.junit.Test;

public class JpxRapidPendingTest {
    private static final LocalDate PREVIOUS = LocalDate.of(2026, 11, 16);
    private static final LocalDate CURRENT = LocalDate.of(2026, 11, 17);
    private static final List<PriceOnlyScreen.RapidMove> MOVES =
            List.of(new PriceOnlyScreen.RapidMove("1001", new BigDecimal("12.5")));

    @Test public void sameDaySameReasonDoesNotRepeat() {
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS, CURRENT, CURRENT, MOVES,
                Set.of("price-rapid:1001")).isEmpty());
    }

    @Test public void budgetAlertDoesNotSuppressRapidMove() {
        assertEquals(1, JpxWatchWorker.pendingRapid(PREVIOUS, CURRENT, CURRENT, MOVES,
                Set.of("price-budget:1001")).size());
    }

    @Test public void firstDayAndStaleDataNeverAlert() {
        assertTrue(JpxWatchWorker.pendingRapid(null, CURRENT, CURRENT, MOVES, Set.of()).isEmpty());
        assertTrue(JpxWatchWorker.pendingRapid(CURRENT, CURRENT, CURRENT, MOVES, Set.of()).isEmpty());
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS, CURRENT, PREVIOUS, MOVES, Set.of()).isEmpty());
    }

    @Test public void newTradingDayAllowsNewReasonKey() {
        assertEquals(1, JpxWatchWorker.pendingRapid(PREVIOUS, PREVIOUS, CURRENT, MOVES,
                Set.of("price-rapid:1001")).size());
    }
}
