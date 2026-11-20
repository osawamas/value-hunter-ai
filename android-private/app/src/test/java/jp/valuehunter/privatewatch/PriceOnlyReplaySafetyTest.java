package jp.valuehunter.privatewatch;

import org.junit.Test;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import static org.junit.Assert.*;

/** Regression checks for replay and retry gates; no network or notifications are sent. */
public class PriceOnlyReplaySafetyTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);
    private static final LocalDate PREVIOUS = DAY.minusDays(1);

    @Test public void crashAfterPostingBeforeSavingDoesNotPostAnAlreadyActiveNoticeAgain() {
        var active = new java.util.concurrent.atomic.AtomicReference<String>();
        var posts = new java.util.concurrent.atomic.AtomicInteger();
        var receipt = ScanWorker.notificationReceipt("予算入り", "2026-11-17 ABC");
        ScanWorker.submitNotification(receipt, () -> false, active::get, () -> {
            posts.incrementAndGet();
            active.set(receipt);
        });
        // Recreate the receipt exactly as a restarting Worker would, with the Android notification still active.
        ScanWorker.submitNotification(ScanWorker.notificationReceipt("予算入り", "2026-11-17 ABC"),
                () -> false, active::get, () -> { throw new AssertionError("Duplicate post"); });
        assertEquals(1, posts.get());
        var newDay = ScanWorker.notificationReceipt("予算入り", "2026-11-18 ABC");
        ScanWorker.submitNotification(newDay, () -> false, active::get, posts::incrementAndGet);
        assertEquals(2, posts.get());
    }

    @Test public void recordedDismissalSurvivesRestartButAbsentEvidenceAllowsRetry() {
        long dismissed = 1000L;
        var receipt = ScanWorker.notificationReceipt("予算入り", "2026-11-17 ABC");
        ScanWorker.submitNotification(receipt, () -> NotificationDismissal.isRecent(dismissed, dismissed + 1),
                () -> null, () -> { throw new AssertionError("Displayed alert was already dismissed"); });
        var posts = new java.util.concurrent.atomic.AtomicInteger();
        ScanWorker.submitNotification(receipt, () -> NotificationDismissal.isRecent(0, dismissed + 1),
                () -> null, posts::incrementAndGet);
        assertEquals(1, posts.get());
        assertFalse(NotificationDismissal.isRecent(dismissed, dismissed + java.util.concurrent.TimeUnit.DAYS.toMillis(7)));
        assertFalse(NotificationDismissal.isRecent(dismissed, dismissed - 1));
    }

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

    @Test public void trackerUsesOnlyEvidenceForTheExactQuotePair() throws Exception {
        var original = """
                {"intervals":[{"previousDay":"2026-11-16","latestDay":"2026-11-17",
                "sources":{"2026-11-16":{"url":"https://www.jpx.co.jp/listing/others/ex-rights/jpx-att/20261116.xls","sha256":"%s"},
                           "2026-11-17":{"url":"https://www.jpx.co.jp/listing/others/ex-rights/jpx-att/20261117.xls","sha256":"%s"}},
                "excludedCodes":["1002"]}]}
                """.formatted("a".repeat(64), "b".repeat(64));
        var evidence = JpxRapidEvidence.parse(original);
        var before = new JpxCloseTable.Sessions(null, new BigDecimal("100"));
        var after = new JpxCloseTable.Sessions(null, new BigDecimal("108"));
        var comparison = new JpxDailyCheck.Comparison(
                new JpxDailyCheck.Report(DAY, "", Map.of("1001", after, "1002", after), Set.of()),
                new JpxDailyCheck.Report(PREVIOUS, "", Map.of("1001", before, "1002", before), Set.of()));
        var screen = new JpxDailyCheck.Screening(List.of(), List.of(), List.of(), Set.of());
        var finance = JpxAutomaticFinance.Batch.empty();
        var rapid = JpxWatchWorker.rapidCandidates(comparison, screen, finance, evidence.excluded(PREVIOUS, DAY));
        assertEquals(List.of("1001"), rapid.stream().map(PriceOnlyScreen.RapidMove::code).toList());
        assertTrue(JpxWatchWorker.rapidCandidates(comparison, screen, finance,
                evidence.excluded(PREVIOUS, DAY.plusDays(1))).isEmpty());
        assertThrows(org.json.JSONException.class, () -> JpxRapidEvidence.parse(original.replace("20261117.xls", "20261118.xls")));
        assertThrows(org.json.JSONException.class, () -> JpxRapidEvidence.parse(original.replace("www.jpx.co.jp", "example.com")));
        assertTrue(JpxWatchWorker.pendingRapid(PREVIOUS, DAY, DAY, rapid, Set.of("price-rapid:1001")).isEmpty());
    }
}
