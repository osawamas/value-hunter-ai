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

    @Test public void unchangedSetNeverNotifiesButReentryDoes() {
        LocalDate day = LocalDate.parse("2026-08-21");
        assertTrue(WatchTransitions.newEntrants(day.minusDays(1).toString(), day,
                List.of(A), Set.of("1001")).isEmpty());
        assertEquals(List.of(A), WatchTransitions.newEntrants(day.minusDays(1).toString(), day,
                List.of(A), Set.of()));
    }
}
