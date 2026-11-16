package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import org.junit.Test;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class SgWatchTest {
    @Test public void alertsOnlyOnEntryFromTheImmediatelyPreviousSession() {
        var previous = new SgCloseCheck.Close(LocalDate.of(2026, 11, 13), 10);
        var current = new SgCloseCheck.Close(LocalDate.of(2026, 11, 16), 8);
        var pair = new SgCloseCheck.Pair(previous, current);
        assertTrue(SgValuation.shouldAlert(pair, "2026-11-13", false, true));
        assertFalse(SgValuation.shouldAlert(pair, "", false, true));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-12", false, true));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-16", false, true));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-13", true, true));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-13", false, false));
    }

    @Test public void checksYenBudgetAndPositiveValuationBounds() {
        var trial = new SgValuation.Trial(10, 100, 15, 1);
        assertTrue(trial.qualifies(100_000));
        assertFalse(trial.qualifies(100_001));
        assertFalse(trial.qualifies(Double.NaN));
        assertFalse(new SgValuation.Trial(10, 100, 15.01, 1).qualifies(100));
        assertFalse(new SgValuation.Trial(10, 100, 15, 0).qualifies(100));
    }
}
