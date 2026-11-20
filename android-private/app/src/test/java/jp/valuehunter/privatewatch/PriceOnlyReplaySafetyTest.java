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

    @Test public void recordedTapIsAvailableAfterRestartAndScopedToTheExactAlert() {
        String exact = ScanWorker.notificationReceipt("予算入り", "2026-11-17 ABC");
        String other = ScanWorker.notificationReceipt("予算入り", "2026-11-17 DEF");
        long now = java.util.concurrent.TimeUnit.DAYS.toMillis(8);
        var disk = new java.util.HashMap<String, Long>();
        disk.put("expired", 1000L);
        var state = (android.content.SharedPreferences) java.lang.reflect.Proxy.newProxyInstance(
                getClass().getClassLoader(), new Class<?>[]{android.content.SharedPreferences.class},
                (prefs, method, args) -> switch (method.getName()) {
                    case "getAll" -> Map.copyOf(disk);
                    case "edit" -> java.lang.reflect.Proxy.newProxyInstance(getClass().getClassLoader(),
                            new Class<?>[]{android.content.SharedPreferences.Editor.class}, (editor, change, values) -> {
                                switch (change.getName()) {
                                    case "putLong" -> disk.put((String) values[0], (Long) values[1]);
                                    case "remove" -> disk.remove((String) values[0]);
                                    case "commit" -> { return true; }
                                    default -> throw new AssertionError(change);
                                }
                                return editor;
                            });
                    default -> throw new AssertionError(method);
                });
        NotificationDismissal.remember(state, "8-" + exact, now);
        var restored = Map.copyOf(disk);
        assertFalse(restored.containsKey("expired"));
        assertTrue(NotificationDismissal.isRecent(restored.getOrDefault("8-" + exact, 0L), now + 1));
        assertFalse(NotificationDismissal.isRecent(restored.getOrDefault("8-" + other, 0L), now + 1));
        assertFalse(NotificationDismissal.isRecent(now, now + java.util.concurrent.TimeUnit.DAYS.toMillis(7)));
        assertFalse(NotificationDismissal.isRecent(now, now - 1));
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
