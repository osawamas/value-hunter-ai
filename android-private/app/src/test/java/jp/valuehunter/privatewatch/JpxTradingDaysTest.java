package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.time.Instant;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public final class JpxTradingDaysTest {
    @Test public void waitsUntilTheCashMarketClosesToExpectTheNewReport() {
        assertEquals(LocalDate.of(2026, 11, 19), JpxTradingDays.expected(Instant.parse("2026-11-20T06:29:59Z")));
        assertEquals(LocalDate.of(2026, 11, 20), JpxTradingDays.expected(Instant.parse("2026-11-20T06:30:00Z")));
    }

    @Test public void skipsWeekendsAndOfficialClosures() {
        assertEquals(LocalDate.of(2026, 11, 20), JpxTradingDays.expected(Instant.parse("2026-11-23T09:00:00Z")));
        assertEquals(LocalDate.of(2026, 12, 30), JpxTradingDays.expected(Instant.parse("2027-01-03T09:00:00Z")));
        assertNull(JpxTradingDays.expected(Instant.parse("2028-05-01T09:00:00Z")));
    }
}
