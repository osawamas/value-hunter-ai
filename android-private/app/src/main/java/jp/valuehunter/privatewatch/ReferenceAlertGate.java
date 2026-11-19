package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;

/** Pure, replayable per-day/per-reason gate for reference-only alerts.
 * No candidate is sent unless its caller has already verified the underlying evidence.
 */
final class ReferenceAlertGate {
    static final String BUDGET = "price-budget";
    static final String RAPID_MOVE = "price-rapid-move";

    record Signal(String code, LocalDate day, String reason) {}
    private ReferenceAlertGate() {}

    static String key(Signal signal) {
        if (signal == null || signal.day() == null || signal.code() == null
                || !signal.code().matches("[0-9][0-9A-Z]{3}")
                || !(BUDGET.equals(signal.reason()) || RAPID_MOVE.equals(signal.reason()))) {
            throw new IllegalArgumentException("Invalid reference alert signal");
        }
        return signal.day() + "|" + signal.reason() + "|" + signal.code();
    }

    static List<Signal> pending(LocalDate latestDay, LocalDate previousDay,
                                List<Signal> verifiedSignals, Set<String> deliveredKeys) {
        if (latestDay == null || previousDay == null || !previousDay.isBefore(latestDay)
                || verifiedSignals == null || deliveredKeys == null) return List.of();
        var pending = new ArrayList<Signal>();
        var seen = new java.util.HashSet<String>(deliveredKeys);
        for (var signal : verifiedSignals) {
            if (signal == null || !latestDay.equals(signal.day())) continue;
            String id = key(signal);
            if (seen.add(id)) pending.add(signal);
        }
        pending.sort(Comparator.comparing(Signal::code).thenComparing(Signal::reason));
        return List.copyOf(pending);
    }
}
