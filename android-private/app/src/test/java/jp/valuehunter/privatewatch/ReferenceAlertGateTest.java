package jp.valuehunter.privatewatch;

import org.junit.Test;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import static org.junit.Assert.*;

public class ReferenceAlertGateTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);
    private static final LocalDate PREV = LocalDate.of(2026, 11, 16);

    @Test public void separatesReasonsAndRejectsDuplicateReplay() {
        var budget = new ReferenceAlertGate.Signal("1234", DAY, ReferenceAlertGate.BUDGET);
        var rapid = new ReferenceAlertGate.Signal("1234", DAY, ReferenceAlertGate.RAPID_MOVE);
        var pending = ReferenceAlertGate.pending(DAY, PREV,
                List.of(budget, budget, rapid), Set.of(ReferenceAlertGate.key(budget)));
        assertEquals(List.of(rapid), pending);
        assertEquals(List.of(), ReferenceAlertGate.pending(DAY, PREV,
                List.of(budget, rapid), Set.of(ReferenceAlertGate.key(budget), ReferenceAlertGate.key(rapid))));
    }

    @Test public void refusesWrongDayOrInvalidComparison() {
        var signal = new ReferenceAlertGate.Signal("1234", DAY, ReferenceAlertGate.RAPID_MOVE);
        assertTrue(ReferenceAlertGate.pending(DAY, DAY, List.of(signal), Set.of()).isEmpty());
        assertTrue(ReferenceAlertGate.pending(DAY, DAY.plusDays(1), List.of(signal), Set.of()).isEmpty());
        assertTrue(ReferenceAlertGate.pending(DAY, PREV,
                List.of(new ReferenceAlertGate.Signal("1234", PREV, ReferenceAlertGate.RAPID_MOVE)),
                Set.of()).isEmpty());
    }

    @Test public void invalidSignalCannotBePersisted() {
        try {
            ReferenceAlertGate.key(new ReferenceAlertGate.Signal("1234", DAY, "unknown"));
            fail("Expected validation");
        } catch (IllegalArgumentException expected) {
            assertNotNull(expected);
        }
    }
}
