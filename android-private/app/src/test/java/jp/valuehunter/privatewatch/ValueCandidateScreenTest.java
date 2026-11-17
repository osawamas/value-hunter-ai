package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.math.BigDecimal;

import org.junit.Test;

public class ValueCandidateScreenTest {
    @Test public void comparesUnroundedRatiosAndAllowsOneMissingMetric() {
        assertEquals(ValueCandidateScreen.Level.PRIORITY, assess("916.50", "61.10", "1257.44"));
        assertEquals(ValueCandidateScreen.Level.REFERENCE, assess("916.51", "61.10", "1257.44"));
        assertEquals(ValueCandidateScreen.Level.REFERENCE, assess("900", "61.10", null));
        assertEquals(ValueCandidateScreen.Level.OUTSIDE, assess("900", "10", "1000"));
        assertEquals(ValueCandidateScreen.Level.HELD, assess("900", "0", "1000"));
        assertEquals(ValueCandidateScreen.Level.HELD, assess("900", null, null));
    }

    @Test public void onlyNewOrImprovedEvidenceCanNotify() {
        assertFalse(ValueCandidateScreen.Level.REFERENCE.entersFrom(ValueCandidateScreen.Level.HELD));
        assertFalse(ValueCandidateScreen.Level.REFERENCE.entersFrom(ValueCandidateScreen.Level.REFERENCE));
        assertTrue(ValueCandidateScreen.Level.REFERENCE.entersFrom(ValueCandidateScreen.Level.OUTSIDE));
        assertTrue(ValueCandidateScreen.Level.PRIORITY.entersFrom(ValueCandidateScreen.Level.REFERENCE));
    }

    private static ValueCandidateScreen.Level assess(String close, String eps, String bps) {
        return ValueCandidateScreen.assess(new BigDecimal(close),
                eps == null ? null : new BigDecimal(eps), bps == null ? null : new BigDecimal(bps));
    }
}
