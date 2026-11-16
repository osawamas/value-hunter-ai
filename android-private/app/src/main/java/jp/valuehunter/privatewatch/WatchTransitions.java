package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/** Pure transition logic shared by manual and scheduled scans. */
final class WatchTransitions {
    private WatchTransitions() {}

    static List<JapanScreen.Candidate> newEntrants(
            String lastDate, LocalDate sessionDate, List<JapanScreen.Candidate> current,
            Set<String> previous) {
        // The first successful scan only establishes a baseline.
        if (lastDate == null || lastDate.isEmpty()) return Collections.emptyList();
        // Never notify twice for one trading session or for older data.
        LocalDate baseline;
        try {
            baseline = LocalDate.parse(lastDate);
        } catch (DateTimeParseException error) {
            // Damaged local history must never trigger a burst of false new-entrant alerts.
            return Collections.emptyList();
        }
        if (!sessionDate.isAfter(baseline)) return Collections.emptyList();
        return JapanScreen.newlyQualified(current, previous);
    }
}
