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

    @Test public void reevaluatesThePreviousSessionEvenWhenItWasAlreadyRecorded() {
        String last = "2026-11-13";
        assertTrue(SgValuation.needsPreviousEvaluation(pair, last));
        assertEquals(WAIT_FOR_PREVIOUS, SgValuation.watchDecision(pair, last, true, null));
        assertEquals(ALERT, SgValuation.watchDecision(pair, last, true, false));
        assertEquals(SAVE, SgValuation.watchDecision(pair, last, true, true));
        assertEquals(SAVE, SgValuation.watchDecision(pair, last, false, null));
        assertEquals(UNCHANGED, SgValuation.watchDecision(pair, last, null, null));
    }

    @Test public void retainsBaselineUntilLateEvidenceResolvesTheCurrentPair() {
        String older = "2026-11-12";
        assertTrue(SgValuation.needsPreviousEvaluation(pair, older));
        assertEquals(WAIT_FOR_PREVIOUS, SgValuation.watchDecision(pair, older, true, null));
        assertEquals(ALERT, SgValuation.watchDecision(pair, older, true, false));

        var next = new SgCloseCheck.Close(LocalDate.of(2026, 11, 17), 9);
        var nextPair = new SgCloseCheck.Pair(current, next);
        assertEquals(SAVE, SgValuation.watchDecision(nextPair, older, true, true));
        assertEquals(SAVE, SgValuation.watchDecision(nextPair, older, false, null));
    }

    @Test public void isQuietOnTheFirstAndAlreadyHandledSessions() {
        assertFalse(SgValuation.needsPreviousEvaluation(pair, ""));
        assertEquals(SAVE, SgValuation.watchDecision(pair, "", true, null));
        assertFalse(SgValuation.needsPreviousEvaluation(pair, "2026-11-16"));
        assertEquals(UNCHANGED, SgValuation.watchDecision(pair, "2026-11-16", true, false));
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
