package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static jp.valuehunter.privatewatch.MarketCoverage.Reason.*;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class MarketCoverageTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 19);

    @Test public void jpxUsesTheListingAsDenominatorAndDistinguishesFourUnassessedReasons() {
        var quotes = Map.of("1111", close(500), "3333", close(400), "4444", close(300),
                "5555", close(200_000), "9999", close(100));
        var universe = new JpxStockUniverse(DAY, Set.of("1111", "2222", "3333", "4444", "5555"));
        var report = new JpxDailyCheck.Report(DAY, "", quotes, Set.of(), "fixture", universe);
        var screen = new JpxDailyCheck.Screening(List.of(), List.of(),
                List.of(new JpxDailyCheck.Held("3333", "権利落月報の未確認月")), Set.of("1111", "9999"));
        var coverage = JpxWatchWorker.coverage(report, screen, Set.of("4444"));
        assertEquals(5, coverage.target());
        assertEquals(4, coverage.closed());
        assertEquals(1, coverage.assessed());
        assertEquals(Map.of(CLOSE, List.of("2222"), CORPORATE_ACTION, List.of("3333"),
                DOWNLOAD, List.of("4444"), OUTSIDE_BUDGET, List.of("5555")), coverage.unassessed());
    }

    @Test public void usUsesOnlyDatedOrdinaryListingsAndTracksIssuerAndSplitEvidence() throws Exception {
        var hash = "a".repeat(64);
        var scan = new JSONObject().put("day", DAY.toString()).put("hash", hash)
                .put("coverage_listing_date", DAY.plusDays(1).toString())
                .put("coverage_symbols", new JSONArray(List.of("DONE", "NOQUOTE", "NOSEC", "NODATA", "ERROR", "SPLIT")))
                .put("coverage_failed", "ERROR")
                .put("targets", new JSONArray(List.of(row("NODATA"), row("ERROR"))))
                .put("results", new JSONArray(List.of(row("DONE"), row("SPLIT"))));
        var observation = row("DONE").put("exchange", "NYSE").put("cik", 123)
                .put("status", "outside_valuation").put("quantity", 100);
        scan.put("ledger", new JSONObject().put("trading_date_et", DAY.toString()).put("close_sha256", hash)
                .put("split_holds", new JSONArray(List.of("SPLIT"))).put("reference_screen", new JSONObject()
                        .put("fx_date", DAY.toString()).put("provider", UsDoltCloses.SOURCE)
                        .put("close_sha256", hash).put("observations", new JSONArray(List.of(observation)))));
        var coverage = UsSecFinanceWorker.coverage(scan, Set.of("DONE", "NOSEC", "NODATA", "ERROR", "SPLIT", "ETF"));
        assertEquals(6, coverage.target());
        assertEquals(5, coverage.closed());
        assertEquals(1, coverage.assessed());
        assertTrue(coverage.summary().contains("対象は " + DAY.plusDays(1) + " 時点の上場一覧（参考）"));
        assertEquals(Map.of(CLOSE, List.of("NOQUOTE"), IDENTIFICATION, List.of("NOSEC"),
                FINANCIALS, List.of("NODATA"), DOWNLOAD, List.of("ERROR"), CORPORATE_ACTION, List.of("SPLIT")),
                coverage.unassessed());
    }

    @Test public void completedLedgerDistinguishesNonPositiveFinancialsFromWaitingForEvidence() throws Exception {
        var hash = "a".repeat(64);
        var scan = new JSONObject().put("day", DAY.toString()).put("hash", hash)
                .put("coverage_listing_date", DAY.toString())
                .put("coverage_symbols", new JSONArray(List.of("LOSS", "WAIT")))
                .put("targets", new JSONArray()).put("results", new JSONArray(List.of(
                        row("LOSS").put("profit", "-1").put("equity", "10"),
                        row("WAIT").put("profit", "2").put("equity", "3"))));
        scan.put("ledger", new JSONObject().put("trading_date_et", DAY.toString()).put("close_sha256", hash)
                .put("reference_screen", new JSONObject().put("fx_date", DAY.toString())
                        .put("provider", UsDoltCloses.SOURCE).put("close_sha256", hash)
                        .put("observations", new JSONArray())));
        var coverage = UsSecFinanceWorker.coverage(scan, Set.of("LOSS", "WAIT"));
        assertEquals(0, coverage.assessed());
        assertEquals(Map.of(NON_POSITIVE_FINANCIALS, List.of("LOSS"), VALUATION, List.of("WAIT")),
                coverage.unassessed());
    }

    private static JpxCloseTable.Sessions close(long amount) {
        return new JpxCloseTable.Sessions(null, BigDecimal.valueOf(amount));
    }

    private static JSONObject row(String symbol) throws Exception {
        return new JSONObject().put("symbol", symbol);
    }
}
