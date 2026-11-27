package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.io.IOException;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;
import org.junit.Test;

public class JpxDailyCheckDateTest {
    @Test public void assessmentKeepsMissingClosesAndWeakMeterRowsInTheFixedScope() throws Exception {
        var day = LocalDate.of(2026, 11, 19);
        var scope = new JpxStockUniverse(day, Set.of("1301", "1302", "1303", "1304", "1305"));
        var cheap = new JpxCloseTable.Sessions(java.math.BigDecimal.valueOf(500), null);
        var costly = new JpxCloseTable.Sessions(java.math.BigDecimal.valueOf(100001), null);
        var report = new JpxDailyCheck.Report(day, "official", Map.of(
                "1301", cheap, "1302", cheap, "1303", cheap, "1304", costly), Set.of(), "a", scope);
        var screening = new JpxDailyCheck.Screening(java.util.List.of(), java.util.List.of(),
                java.util.List.of(), Set.of("1301"));
        var rows = new org.json.JSONObject()
                .put("1301", ValueAlertPreview.encode(new ValueAlertMeter.Score(90, 2, 2), 100))
                .put("1302", ValueAlertPreview.encode(new ValueAlertMeter.Score(85, 1, 2), 100))
                .put("1303", ValueAlertPreview.encode(new ValueAlertMeter.Score(90, 0, 1), 100));
        var result = JpxWatchWorker.assessmentCounts(report, screening, rows);
        assertEquals(5, result.getInt("scope"));
        assertEquals(1, result.getInt("strict_assessed"));
        assertEquals(1, result.getInt("flexible_added"));
        assertEquals(40.0, result.getDouble("full_scope_assessed_percent"), 0.0);
        assertEquals(2, result.getInt("budget_assessed"));
        assertEquals(3, result.getInt("unassessed"));
        assertEquals(3, result.getJSONObject("unassessed_reasons").length());
    }

    @Test public void savedQuotesReuseTheExactEditionAndPreserveNoTradeAndAmbiguity() throws Exception {
        var day = LocalDate.of(2026, 11, 19);
        var universe = new JpxStockUniverse(day.minusDays(2), Set.of("1301", "1302", "1332"));
        var original = new JpxDailyCheck.Report(day, "original", Map.of(
                "1301", new JpxCloseTable.Sessions(new java.math.BigDecimal("250.50"), null),
                "1302", new JpxCloseTable.Sessions(null, null)), Set.of("1332"), "version:exact", universe);
        var saved = new org.json.JSONObject(JpxQuoteCache.encode(original).toString());
        var restored = JpxDailyCheck.cachedReport(day, universe, saved,
                requested -> new JpxDailyCheck.Edition(true, "version:exact"),
                requested -> { throw new AssertionError("Same official edition must skip downloading"); });
        assertEquals(original.quotes(), restored.quotes());
        assertEquals(original.ambiguous(), restored.ambiguous());
        assertEquals(0, restored.close("1301").compareTo(new java.math.BigDecimal("250.5")));
        assertNull(restored.close("1302"));
        assertNull(restored.close("1332"));
    }

    @Test public void revisedEditionChangedListingsAndCorruptDataReturnToOfficialDownload() throws Exception {
        var day = LocalDate.of(2026, 11, 19);
        var universe = new JpxStockUniverse(day, Set.of("1301"));
        var original = new JpxDailyCheck.Report(day, "original",
                Map.of("1301", new JpxCloseTable.Sessions(null, new java.math.BigDecimal("250"))),
                Set.of(), "version:exact", universe);
        var saved = JpxQuoteCache.encode(original);
        var current = new JpxDailyCheck.Edition(true, "version:exact");
        var bad = new org.json.JSONObject(saved.toString()).put("payload", "{}");
        assertSame(original, JpxDailyCheck.cachedReport(day, universe, bad, ignored -> current, ignored -> original));
        assertSame(original, JpxDailyCheck.cachedReport(day, universe, saved,
                ignored -> new JpxDailyCheck.Edition(true, "version:corrected"), ignored -> original));
        assertSame(original, JpxDailyCheck.cachedReport(day, universe, saved,
                ignored -> new JpxDailyCheck.Edition(true, ""), ignored -> original));
        assertSame(original, JpxDailyCheck.cachedReport(day, universe, saved,
                ignored -> { throw new IOException("HEAD unavailable"); }, ignored -> original));
        var altered = new JpxStockUniverse(day, Set.of("1301", "1332"));
        assertSame(original, JpxDailyCheck.cachedReport(day, altered, saved, ignored -> current, ignored -> original));
        assertSame(original, JpxDailyCheck.cachedReport(day, universe, null,
                ignored -> { throw new AssertionError("Cold start should go straight to GET"); }, ignored -> original));
    }

    @Test public void unreadableEquityTableCannotAdvanceWatchBaseline() {
        assertFalse(JpxDailyCheck.hasUsableClose(Map.of(), Set.of()));
        assertFalse(JpxDailyCheck.hasUsableClose(
                Map.of("1301", new JpxCloseTable.Sessions(null, null)), Set.of()));
        assertFalse(JpxDailyCheck.hasUsableClose(
                Map.of("1301", new JpxCloseTable.Sessions(null, new java.math.BigDecimal("250"))),
                Set.of("1301")));
        assertTrue(JpxDailyCheck.hasUsableClose(
                Map.of("1332", new JpxCloseTable.Sessions(new java.math.BigDecimal("250"), null)),
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
