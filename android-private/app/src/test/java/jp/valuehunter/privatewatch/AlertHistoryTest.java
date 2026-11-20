package jp.valuehunter.privatewatch;

import org.junit.Test;
import static org.junit.Assert.*;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class AlertHistoryTest {
    private static final String A = "a".repeat(64);
    private static final String B = "b".repeat(64);
    private static final long NOW = TimeUnit.DAYS.toMillis(20);

    @Test public void repeatedReceiptDoesNotDuplicateAndSurvivesSerialization() {
        var old = new AlertHistory.Entry(A, NOW - 5000, "日本株", "参考判定");
        var newer = new AlertHistory.Entry(A, NOW - 1000, "日本株", "訂正後");
        var entries = AlertHistory.add(List.of(old), newer, NOW);
        assertEquals(1, entries.size());
        assertEquals("訂正後", AlertHistory.decode(AlertHistory.encode(entries), NOW).get(0).detail());
    }

    @Test public void sevenDayBoundaryAndFutureRecordsAreExcluded() {
        var entries = List.of(
                new AlertHistory.Entry(A, NOW - TimeUnit.DAYS.toMillis(7), "old", ""),
                new AlertHistory.Entry(B, NOW + 1, "future", ""));
        assertTrue(AlertHistory.prune(entries, NOW).isEmpty());
    }

    @Test public void corruptAndLegacyMissingHistoryAreSafe() {
        assertTrue(AlertHistory.decode("not-json", NOW).isEmpty());
        assertTrue(AlertHistory.decode("", NOW).isEmpty());
    }

    @Test public void historyKeepsNewestAndIsBounded() {
        var entries = new java.util.ArrayList<AlertHistory.Entry>();
        for (int i = 0; i < 180; i++)
            entries.add(new AlertHistory.Entry(String.format("%064x", i), NOW - i * 1000L, "US", "reference"));
        var result = AlertHistory.prune(entries, NOW);
        assertEquals(150, result.size());
        assertEquals(NOW, result.get(0).at());
    }
}
