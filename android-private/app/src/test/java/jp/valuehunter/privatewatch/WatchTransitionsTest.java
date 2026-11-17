package jp.valuehunter.privatewatch;

import org.junit.Test;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class WatchTransitionsTest {
    private static final JapanScreen.Candidate A = new JapanScreen.Candidate("1001", "A", 800, 10, 0.8);
    private static final JapanScreen.Candidate B = new JapanScreen.Candidate("1002", "B", 1500, 12, 0.9);

    @Test public void firstScanIsBaselineSecondScanOnlyNotifiesNewEntrant() {
        LocalDate first = LocalDate.parse("2026-08-20");
        LocalDate second = first.plusDays(1);
        assertTrue(WatchTransitions.newEntrants("", first, List.of(A), Set.of()).isEmpty());
        assertEquals(List.of(B), WatchTransitions.newEntrants(first.toString(), second,
                List.of(A, B), Set.of("1001")));
    }

    @Test public void sameDayRetryAndOlderSnapshotNeverNotify() {
        LocalDate first = LocalDate.parse("2026-08-20");
        assertTrue(WatchTransitions.newEntrants(first.toString(), first,
                List.of(B), Set.of("1001")).isEmpty());
        assertTrue(WatchTransitions.newEntrants(first.toString(), first.minusDays(1),
                List.of(B), Set.of("1001")).isEmpty());
    }

    @Test public void corruptBaselineNeverCreatesFalseAlerts() {
        LocalDate day = LocalDate.parse("2026-08-21");
        assertTrue(WatchTransitions.newEntrants("damaged-local-date", day,
                List.of(A, B), Set.of()).isEmpty());
        assertTrue(WatchTransitions.newEntrants("2026-02-30", day,
                List.of(A, B), Set.of()).isEmpty());
    }

    @Test public void olderOrSameSessionCannotReplaceNewerBaseline() {
        LocalDate latest = LocalDate.parse("2026-08-21");
        assertTrue(!WatchTransitions.shouldStoreSnapshot(latest.toString(), latest));
        assertTrue(!WatchTransitions.shouldStoreSnapshot(latest.toString(), latest.minusDays(1)));
        assertTrue(WatchTransitions.shouldStoreSnapshot(latest.toString(), latest.plusDays(1)));
    }

    @Test public void damagedStoredDateCannotPermanentlyBlockJQuantsRequests() {
        LocalDate day = LocalDate.parse("2026-08-21");
        assertTrue(WatchTransitions.shouldRequestSession("", day));
        assertTrue(WatchTransitions.shouldRequestSession("invalid", day));
        assertTrue(WatchTransitions.shouldRequestSession("2026-02-30", day));
        assertTrue(!WatchTransitions.shouldRequestSession(day.toString(), day));
        assertTrue(!WatchTransitions.shouldRequestSession(day.plusDays(1).toString(), day));
        assertTrue(WatchTransitions.shouldRequestSession(day.minusDays(1).toString(), day));
        assertTrue(WatchTransitions.newEntrants("invalid", day, List.of(A), Set.of()).isEmpty());
    }

    @Test public void missingOrDamagedBaselineCanBeRebuiltWithoutFalseNotification() {
        LocalDate day = LocalDate.parse("2026-08-21");
        assertTrue(WatchTransitions.shouldStoreSnapshot("", day));
        assertTrue(WatchTransitions.shouldStoreSnapshot("invalid", day));
        assertTrue(WatchTransitions.newEntrants("invalid", day, List.of(A), Set.of()).isEmpty());
    }

    @Test public void unchangedSetNeverNotifiesButReentryDoes() {
        LocalDate day = LocalDate.parse("2026-08-21");
        assertTrue(WatchTransitions.newEntrants(day.minusDays(1).toString(), day,
                List.of(A), Set.of("1001")).isEmpty());
        assertEquals(List.of(A), WatchTransitions.newEntrants(day.minusDays(1).toString(), day,
                List.of(A), Set.of()));
    }
}
