package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.File;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.Set;

final class ListingArchiveProbe {
    private static final LocalDate BEFORE = LocalDate.of(2026, 11, 16);
    private static final LocalDate DAY = BEFORE.plusDays(1);
    private static final LocalTime NOW = LocalTime.of(17, 0);
    private static final Map<MarketCoverage.Reason, List<String>> UNPRICED = Map.of(
            MarketCoverage.Reason.DATED_LISTING, List.of("KEEP", "CHANGE", "LATE"));

    private ListingArchiveProbe() {}

    private static File directory(Context context) {
        return new File(context.getNoBackupFilesDir(), "listing-archive-probe");
    }

    static void prepare(Context context) throws Exception {
        var dir = directory(context);
        if (!dir.mkdirs() && !dir.isDirectory()) throw new AssertionError("Cannot create archive fixture");
        var beforeNyse = nyse("1116202616:08", "Class A");
        var beforeNasdaq = nasdaq("1116202616:08");
        require(UsListingHistory.capture(dir, BEFORE, NOW, beforeNyse, beforeNasdaq),
                "Could not persist the first session");
        require(!UsListingHistory.capture(dir, DAY, NOW, nyse("1117202616:08", "Class B"), beforeNasdaq),
                "Different dates were combined");
        require(UsListingHistory.hasIdentity(dir, BEFORE) && !UsListingHistory.hasIdentity(dir, DAY)
                && !UsListingArchiveWorker.hasVerifiedPending(UNPRICED,
                        UsListingHistory.verifiedSupplementSymbols(dir, DAY)), "Failed capture changed the first session");
        require(UsListingHistory.capture(dir, DAY, NOW, nyse("1117202616:08", "Class B"),
                nasdaq("1117202616:08")), "Could not retry and save the second session");
    }

    static void checkAfterReboot(Context context) {
        var dir = directory(context);
        var matched = UsListingHistory.verifiedSupplementSymbols(dir, DAY);
        require(UsListingHistory.hasIdentity(dir, BEFORE) && UsListingHistory.hasIdentity(dir, DAY),
                "The two listing archives did not survive reboot");
        require(matched.equals(Set.of("KEEP", "STABLE"))
                && UsListingArchiveWorker.hasVerifiedPending(UNPRICED, matched),
                "Reconciliation should admit exactly one pending ticker and hold its changed or missing peers");
    }

    private static UsMarketCoverage.Directory nyse(String time, String shareClass) throws Exception {
        return UsMarketCoverage.directory("ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
                + "STABLE|Stable Corp Ordinary Shares|N|N|N\n"
                + "CHANGE|Change Corp " + shareClass + " Ordinary Shares|N|N|N\n"
                + "File Creation Time: " + time + "||||", false);
    }

    private static UsMarketCoverage.Directory nasdaq(String time) throws Exception {
        return UsMarketCoverage.directory("Symbol|Security Name|Test Issue|ETF|NextShares\n"
                + "KEEP|Keep Corp Common Stock|N|N|N\nFile Creation Time: " + time + "||||", true);
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
