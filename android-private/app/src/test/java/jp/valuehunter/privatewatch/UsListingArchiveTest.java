package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.time.Instant;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class UsListingArchiveTest {
    @Test public void capturesOnlyInItsNewYorkWindowAcrossStandardAndDaylightTime() {
        assertFalse(UsListingArchiveWorker.captureWindow(Instant.parse("2026-11-17T21:04:00Z")));
        assertTrue(UsListingArchiveWorker.captureWindow(Instant.parse("2026-11-17T21:05:00Z")));
        assertFalse(UsListingArchiveWorker.captureWindow(Instant.parse("2026-11-18T01:45:00Z")));
        assertTrue(UsListingArchiveWorker.captureWindow(Instant.parse("2026-07-14T20:05:00Z")));
        assertFalse(UsListingArchiveWorker.captureWindow(Instant.parse("2026-11-21T21:05:00Z")));
        assertFalse(UsListingArchiveWorker.captureWindow(Instant.parse("2026-11-26T21:05:00Z")));
    }

    @Test public void displaysMostRecentDueSessionBeforeAndAfterTheWindowOpens() {
        assertEquals(LocalDate.of(2026, 11, 16),
                UsListingArchiveWorker.latestArchiveDay(Instant.parse("2026-11-17T21:04:00Z")));
        assertEquals(LocalDate.of(2026, 11, 17),
                UsListingArchiveWorker.latestArchiveDay(Instant.parse("2026-11-17T21:05:00Z")));
        assertEquals(LocalDate.of(2026, 11, 25),
                UsListingArchiveWorker.latestArchiveDay(Instant.parse("2026-11-26T22:00:00Z")));
    }
}
