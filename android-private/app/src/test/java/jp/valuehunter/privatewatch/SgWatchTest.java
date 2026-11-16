package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import org.junit.Test;
import static jp.valuehunter.privatewatch.SgValuation.WatchDecision.*;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertNotNull;

public class SgWatchTest {
    private final SgCloseCheck.Close previous = new SgCloseCheck.Close(LocalDate.of(2026, 11, 13), 10);
    private final SgCloseCheck.Close current = new SgCloseCheck.Close(LocalDate.of(2026, 11, 16), 8);
    private final SgCloseCheck.Pair pair = new SgCloseCheck.Pair(previous, current);

    @Test public void alertsOnlyOnEntryFromTheImmediatelyPreviousSession() {
        assertEquals(ALERT, SgValuation.watchDecision(pair, "2026-11-13", false, true, null));
        assertEquals(SAVE, SgValuation.watchDecision(pair, "", false, true, null));
        assertEquals(UNCHANGED, SgValuation.watchDecision(pair, "2026-11-16", false, true, null));
        assertEquals(SAVE, SgValuation.watchDecision(pair, "2026-11-13", true, true, null));
        assertEquals(SAVE, SgValuation.watchDecision(pair, "2026-11-13", false, false, null));
        assertEquals(UNCHANGED, SgValuation.watchDecision(pair, "2026-11-13", false, null, null));
    }

    @Test public void retainsBaselineUntilLateEvidenceResolvesTheCurrentPair() {
        String older = "2026-11-12";
        assertTrue(SgValuation.needsPreviousEvaluation(pair, older, true));
        assertFalse(SgValuation.needsPreviousEvaluation(pair, "", true));
        assertFalse(SgValuation.needsPreviousEvaluation(pair, older, false));

        assertEquals(WAIT_FOR_PREVIOUS, SgValuation.watchDecision(pair, older, false, true, null));
        assertEquals(ALERT, SgValuation.watchDecision(pair, older, false, true, false));
        assertEquals(SAVE, SgValuation.watchDecision(pair, older, false, true, true));
        assertEquals(UNCHANGED, SgValuation.watchDecision(pair, "2026-11-16", true, true, false));

        var next = new SgCloseCheck.Close(LocalDate.of(2026, 11, 17), 9);
        var nextPair = new SgCloseCheck.Pair(current, next);
        assertEquals(SAVE, SgValuation.watchDecision(nextPair, older, false, true, true));
        assertEquals(SAVE, SgValuation.watchDecision(nextPair, older, false, false, null));
    }

    @Test public void distinguishesTemporaryFailuresAndLimitsRetries() {
        for (int status : new int[]{0, 408, 429, 503}) {
            assertTrue(SgCheckWorker.shouldRetry(status, 0));
            assertTrue(SgCheckWorker.shouldRetry(status, 1));
            assertFalse(SgCheckWorker.shouldRetry(status, 2));
        }
        for (int status : new int[]{400, 401, 403, 404}) {
            assertFalse(SgCheckWorker.shouldRetry(status, 0));
        }
    }

    @Test public void doesNotApplyFinancialsBeforeTheyWerePublished() {
        assertNull(SgValuation.forClose(new SgCloseCheck.Close(LocalDate.of(2026, 8, 13), 9), 100));
        assertNotNull(SgValuation.forClose(new SgCloseCheck.Close(LocalDate.of(2026, 8, 14), 9), 100));
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
