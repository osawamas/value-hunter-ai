package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

public final class DiagnosticLogTest {
    @Test public void firstEntryHasNoBlankLineAndOnlyTheNewest240AreRetained() {
        assertEquals("first", DiagnosticLog.append("", "first"));
        String report = "";
        for (int i = 0; i < 245; i++) report = DiagnosticLog.append(report, "event-" + i);
        var entries = report.split("\n");
        assertEquals(240, entries.length);
        assertEquals("event-5", entries[0]);
        assertEquals("event-244", entries[239]);
        assertFalse(report.contains("event-4\n"));
    }
}
