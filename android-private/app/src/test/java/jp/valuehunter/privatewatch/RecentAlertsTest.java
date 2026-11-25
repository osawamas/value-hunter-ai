package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.Test;

public class RecentAlertsTest {
    private static long posted(LocalDate day) {
        return day.atTime(12,30).atZone(RecentAlerts.JAPAN).toInstant().toEpochMilli();
    }
    private static NotificationHistory.Entry event(LocalDate day,String title,String detail) {
        return new NotificationHistory.Entry(day+"-"+title,posted(day),title,detail);
    }
    @Test public void includesTodayAndExactlyThreePastCalendarDates() {
        LocalDate today=LocalDate.parse("2026-11-25");
        var result=RecentAlerts.rows(List.of(
                event(today,"米国株 · 割安", "2026-11-25の終値（参考）\nABC · 100株 · 割安 · 72点"),
                event(today.minusDays(1),"東証・参考", "2026-11-24の終値\n1234 · 90000円"),
                event(today.minusDays(3),"米国株 · 超割安", "2026-11-22の終値\nZYX · 1株 · 超割安 · 95点"),
                event(today.minusDays(4),"米国株 · かなり割安", "2026-11-21の終値\nOLD · 1株 · かなり割安 · 80点"),
                event(today.plusDays(1),"米国株", "FUT · 1株 · 割安 · 70点")),
                today,Map.of("ABC","ABC INDUSTRIES INC","ZYX","ZYX CORPORATION"));
        assertEquals(3,result.size());
        assertEquals(List.of("ABC","1234","ZYX"),result.stream().map(RecentAlerts.Row::code).toList());
        assertEquals("ABC INDUSTRIES INC",result.get(0).company());
        assertEquals("割安",result.get(0).grade());
        assertEquals("超割安",result.get(2).grade());
        assertEquals("12:30",result.get(0).time());
    }
    @Test public void doesNotInventGradesForBudgetOrPriceMovement() {
        var today=LocalDate.parse("2026-11-25");
        var result=RecentAlerts.rows(List.of(
                event(today,"米国株・参考 100株10万円以下に入った 1銘柄",
                        "11月23日\nAIIR (ALPHA COMPANY INC) · 27000円"),
                event(today,"東証・参考 株価急変 1銘柄",
                        "日報\n1234 · -12%")),today,Map.of());
        assertEquals("予算条件入り（割安判定外）",result.get(0).grade());
        assertEquals("ALPHA COMPANY INC",result.get(0).company());
        assertEquals("株価急変（割安判定外）",result.get(1).grade());
    }
    @Test public void onlyParsesRealSymbolLinesAndKeepsReferenceVsPriorityDistinct() {
        var today=LocalDate.parse("2026-11-25");
        var rows=RecentAlerts.rows(List.of(
                event(today,"テスト通知","無音通知のテスト"),
                event(today,"米国株の参考条件入り 2銘柄",
                        "2026-11-23の終値（参考）\nAAPL · 100株 · 優先候補\n"
                        +"NVDA · 1株 · 参考候補")),today,Map.of());
        assertEquals(2,rows.size());
        assertEquals("財務・優先候補（3段階外）",rows.get(0).grade());
        assertEquals("財務・参考候補（3段階外）",rows.get(1).grade());
    }
    @Test public void decoratesOnlyKnownIssuerCodesWithoutGuessing() {
        assertEquals("ABC (ABC HOLDINGS) · 100株 · 割安",
                UsCompanyNames.decorate("ABC · 100株 · 割安", Map.of("ABC","ABC HOLDINGS")));
        assertEquals("XYZ · 1株 · 参考候補",
                UsCompanyNames.decorate("XYZ · 1株 · 参考候補", Map.of("ABC","ABC HOLDINGS")));
    }
}
