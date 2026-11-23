package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class DiagnosticLogTest {
    @Test public void secretLabelsAreRedactedBeforeExport() {
        String data = "api_key=abcd1234 token:secret123 authorization=BearerXYZ password=mypw";
        String safe = DiagnosticLog.redact(data);
        assertFalse(safe.contains("abcd1234"));
        assertFalse(safe.contains("secret123"));
        assertFalse(safe.contains("BearerXYZ"));
        assertFalse(safe.contains("mypw"));
        assertTrue(safe.contains("[REDACTED]"));
    }

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
