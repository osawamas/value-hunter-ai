package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.io.IOException;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;
import org.junit.Test;

public class JpxDailyCheckDateTest {
    @Test public void unreadableEquityTableCannotAdvanceWatchBaseline() {
        assertFalse(JpxDailyCheck.hasUsableSample(Map.of(), Set.of()));
        assertFalse(JpxDailyCheck.hasUsableSample(
                Map.of("1301", new JpxCloseTable.Sessions(null, null)), Set.of()));
        assertFalse(JpxDailyCheck.hasUsableSample(
                Map.of("1301", new JpxCloseTable.Sessions(null, new java.math.BigDecimal("250"))),
                Set.of("1301")));
        assertTrue(JpxDailyCheck.hasUsableSample(
                Map.of("1301", new JpxCloseTable.Sessions(new java.math.BigDecimal("250"), null)),
                Set.of()));
    }

    @Test public void rejectsStaleReportReturnedForNewerRequestedDate() {
        LocalDate today = LocalDate.of(2026, 11, 18);
        assertThrows(IOException.class, () -> JpxDailyCheck.checkRecent(today, requested ->
                new JpxDailyCheck.Report(requested.minusDays(1), "test", Map.of(), Set.of())));
    }

    @Test public void acceptsTwoDistinctOrderedTradingDates() throws Exception {
        LocalDate today = LocalDate.of(2026, 11, 18);
        var result = JpxDailyCheck.checkRecent(today, requested ->
                new JpxDailyCheck.Report(requested, "test", Map.of(), Set.of()));
        assertEquals(LocalDate.of(2026, 11, 18), result.latest().date());
        assertEquals(LocalDate.of(2026, 11, 17), result.previous().date());
    }

    @Test public void includesTodayOnlyWhenPublished() throws Exception {
        LocalDate today = LocalDate.of(2026, 11, 18);
        assertEquals(today, JpxDailyCheck.candidateDays(today).get(0));
        var comparison = JpxDailyCheck.checkRecent(today, requested ->
                requested.equals(today) ? null : new JpxDailyCheck.Report(requested, "test", Map.of(), Set.of()));
        assertEquals(LocalDate.of(2026, 11, 17), comparison.latest().date());
        assertEquals(LocalDate.of(2026, 11, 16), comparison.previous().date());
    }

    @Test public void ignoresUnpublishedDaysWithoutInventingQuotes() throws Exception {
        LocalDate today = LocalDate.of(2026, 11, 18);
        var result = JpxDailyCheck.checkRecent(today, requested ->
                (requested.equals(LocalDate.of(2026, 11, 18)) || requested.equals(LocalDate.of(2026, 11, 17))) ? null
                    : new JpxDailyCheck.Report(requested, "test", Map.of(), Set.of()));
        assertEquals(LocalDate.of(2026, 11, 16), result.latest().date());
        assertEquals(LocalDate.of(2026, 11, 13), result.previous().date());
    }
}
