package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import org.junit.Test;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertNotNull;

public class SgWatchTest {
    @Test public void alertsOnlyOnEntryFromTheImmediatelyPreviousSession() {
        var previous = new SgCloseCheck.Close(LocalDate.of(2026, 11, 13), 10);
        var current = new SgCloseCheck.Close(LocalDate.of(2026, 11, 16), 8);
        var pair = new SgCloseCheck.Pair(previous, current);
        assertTrue(SgValuation.shouldAlert(pair, "2026-11-13", false, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "", false, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-12", false, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-16", false, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-13", true, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-13", false, false, null));
    }

    @Test public void usesLatePreviousEvidenceWithoutSendingAFirstRunOrDuplicateAlert() {
        var previous = new SgCloseCheck.Close(LocalDate.of(2026, 11, 13), 10);
        var current = new SgCloseCheck.Close(LocalDate.of(2026, 11, 16), 8);
        var pair = new SgCloseCheck.Pair(previous, current);
        String older = "2026-11-12";
        assertTrue(SgValuation.needsPreviousEvaluation(pair, older, true));
        assertFalse(SgValuation.needsPreviousEvaluation(pair, "", true));
        assertFalse(SgValuation.needsPreviousEvaluation(pair, older, false));
        assertTrue(SgValuation.shouldAlert(pair, older, true, true, false));
        assertFalse(SgValuation.shouldAlert(pair, older, false, true, true));
        assertFalse(SgValuation.shouldAlert(pair, older, false, true, null));
        assertFalse(SgValuation.shouldAlert(pair, "", false, true, false));
        assertFalse(SgValuation.shouldAlert(pair, "2026-11-16", true, true, false));
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
