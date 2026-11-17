package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Collections;
import java.util.List;
import java.util.Set;

/** Pure transition logic shared by manual and scheduled scans. */
final class WatchTransitions {
    private WatchTransitions() {}

    /** A damaged persisted date must not permanently stop all future API scans. */
    static boolean shouldRequestSession(String lastDate, LocalDate requestedDate) {
        if (lastDate == null || lastDate.isEmpty()) return true;
        try {
            return requestedDate.isAfter(LocalDate.parse(lastDate));
        } catch (DateTimeParseException error) {
            return true; // Rebuild safely; newEntrants suppresses alerts for damaged history.
        }
    }

    /** Reject stale/same-session responses before they can overwrite a newer baseline. */
    static boolean shouldStoreSnapshot(String lastDate, LocalDate sessionDate) {
        if (lastDate == null || lastDate.isEmpty()) return true;
        try {
            return sessionDate.isAfter(LocalDate.parse(lastDate));
        } catch (DateTimeParseException error) {
            // A damaged baseline can be rebuilt, but must not cause an alert.
            return true;
        }
    }

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
