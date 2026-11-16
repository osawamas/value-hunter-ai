package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import java.util.List;
import java.util.Set;

/** Pure transition logic shared by manual and scheduled scans. */
final class WatchTransitions {
    private WatchTransitions() {}

    static List<JapanScreen.Candidate> newEntrants(
            String lastDate, LocalDate sessionDate, List<JapanScreen.Candidate> current,
            Set<String> previous) {
        // The first successful scan only establishes a baseline.
        if (lastDate == null || lastDate.isEmpty()) return List.of();
        // Never notify twice for one trading session or for older data.
        if (!sessionDate.isAfter(LocalDate.parse(lastDate))) return List.of();
        return JapanScreen.newlyQualified(current, previous);
    }
}
