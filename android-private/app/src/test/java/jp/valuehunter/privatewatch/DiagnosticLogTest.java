package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

public final class DiagnosticLogTest {
    @Test public void realBuild30ScreenCountsAreNotRetries() {
        assertEquals("INFO", DiagnosticLog.classify("東証の条件入り: 財務 0件・予算 12件・急変 145件 · 通知待ち 0件"));
        assertEquals("INFO", DiagnosticLog.classify("割安判定の除外理由を集計 · 株式分割の照合待ち 19件 · 終値の照合待ち 0件"));
        assertEquals("INFO", DiagnosticLog.classify("保存状態: 財務・株数などの照合待ち"));
    }

    @Test public void realFailuresAndRetriesRemainVisible() {
        assertEquals("ERROR", DiagnosticLog.classify("保存失敗 · 再試行"));
        assertEquals("RETRY", DiagnosticLog.classify("実行結果: 再試行"));
        assertEquals("RETRY", DiagnosticLog.classify("通信タイムアウト"));
        assertEquals("ERROR", DiagnosticLog.classify("保存できず"));
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
