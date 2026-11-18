package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class JpxReferenceFinancialsTest {
    @Test public void verifiedAnnualDisclosuresAreAvailableAfterRelease() {
        assertEquals(8, JpxReferenceFinancials.watchCodes().size());
        check("3864", LocalDate.of(2026, 5, 14), "43.37", "2354.68", "43808179");
        check("5020", LocalDate.of(2026, 5, 14), "96.18", "1252.75", "2689892692");
        check("9433", LocalDate.of(2026, 5, 12), "183.59", "1333.50", "3807078418");
    }

    private static void check(String code, LocalDate release, String eps, String bps, String shares) {
        var close = new BigDecimal("500");
        assertEquals(ValueCandidateScreen.Level.HELD, JpxReferenceFinancials.level(code, release, close));
        assertEquals(ValueCandidateScreen.Level.PRIORITY, JpxReferenceFinancials.level(code, release.plusDays(1), close));
        var html = new StringBuilder();
        JpxReferenceFinancials.appendHtml(html, code, release.plusDays(1), close);
        assertTrue(html.toString().contains("EPS " + eps + "円 / BPS " + bps + "円"));
        assertTrue(html.toString().contains("自己株式控除後 " + shares + "株"));
    }
}
