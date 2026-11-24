package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class DiagnosticLogTest {
    @Test public void httpStatusRetryRemainsAnErrorNotACompletedUpdate() {
        assertEquals("RETRY", DiagnosticLog.classify("SEC財務HTTP応答 403 · 次回の再試行待ち"));
        assertEquals("RETRY", DiagnosticLog.classify("SEC財務HTTP応答 429 · 次回の再試行待ち"));
    }

    @Test public void classifyFailureAndRetryWithoutInflatingOrdinaryEvents() {
        assertEquals("ERROR", DiagnosticLog.classify("終値ファイルを保存できず"));
        assertEquals("ERROR", DiagnosticLog.classify("通知履歴が読み込めなかった"));
        assertEquals("ERROR", DiagnosticLog.classify("保存処理に失敗"));
        assertEquals("RETRY", DiagnosticLog.classify("Wi-Fi切断 · 再試行待ち"));
        assertEquals("INFO", DiagnosticLog.classify("終値保存完了"));
        assertEquals("INFO", DiagnosticLog.classify("通信設定を変更"));
    }

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
