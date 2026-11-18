package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.io.IOException;
import java.math.BigDecimal;
import java.net.URI;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

public class JpxAutomaticFinanceTest {
    private static final String CODE = "1420";
    private static final String PATH = "/disc/14200/081220260511521448_tse-acedjpsm-14200-20260511314200-ixbrl.htm";
    private static final LocalDate RELEASED = LocalDate.of(2026, 5, 11);
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);

    @Test public void publicFinancialStatementEntersAutomaticScreenWithoutManualRegistration() throws Exception {
        var entry = acquire(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        assertNotNull(entry.annual());
        assertEquals(LocalDate.of(2026, 3, 31), entry.annual().end());
        assertEquals(new BigDecimal("60.00"), entry.annual().eps());
        assertEquals(new BigDecimal("1000.00"), entry.annual().bps());
        assertFalse(JpxDailyCheck.WATCH_CODES.contains(CODE));

        var comparison = new JpxDailyCheck.Comparison(report(DAY, "890"), report(DAY.minusDays(1), "1300"));
        var results = comparison.screen(new JpxShareRights(Set.of(), Set.of(), List.of()),
                new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1));
        assertEquals(1, results.assessed());
        assertEquals(List.of(new JpxDailyCheck.Candidate(CODE, 100, ValueCandidateScreen.Level.PRIORITY)),
                results.entered());
    }

    @Test public void rejectsAnotherIssuerAndCorrectionWithoutSummary() throws Exception {
        assertNull(acquire(archive("決算短信〔日本基準〕(連結)", PATH),
                filing().replace("14200", "99990")).annual());
        assertNull(acquire(archive("（訂正）決算短信の一部訂正", null), filing()).annual());
    }

    @Test public void splitOrIncompleteRecentDisclosuresPreventNotification() throws Exception {
        var held = acquire(archive("決算短信〔日本基準〕(連結)", PATH)
                .replace("自己株式の取得状況", "株式分割に関するお知らせ"), filing());
        assertNotNull(held.annual());
        assertFalse(held.hold().isEmpty());
        var entry = new JpxAutomaticFinance.Entry(DAY.minusDays(1), held.annual(), "");
        assertFalse(entry.failure(CODE, DAY, Map.of()).isEmpty());
        var split = Map.of(DAY, new JpxDisclosureCalendar.Day(Set.of(CODE), Set.of()));
        assertFalse(entry.failure(CODE, DAY, split).isEmpty());
        var completed = Map.of(DAY, new JpxDisclosureCalendar.Day(Set.of(), Set.of("9999")));
        assertEquals("", entry.failure(CODE, DAY, completed));
    }

    @Test public void requiresACompleteDatedTdnetEdition() throws Exception {
        String page = """
                <div id="kaiji-date-1">2026年11月17日</div>
                <div class="kaijiSum">1～1件&nbsp;/&nbsp;全1件</div>
                <tr><td class="oddnew-L kjTime">15:00</td><td class="oddnew-M kjCode">14200</td>
                <td class="oddnew-M kjName">会社</td><td class="oddnew-M kjTitle">株式分割</td></tr>
                """;
        assertEquals(Set.of(CODE), JpxDisclosureCalendar.read(DAY, ignored -> page, () -> false).rights());
        assertThrows(IOException.class, () -> JpxDisclosureCalendar.read(
                DAY, ignored -> page.replace("全1件", "全2件"), () -> false));
        assertThrows(IOException.class, () -> JpxDisclosureCalendar.read(
                DAY.minusDays(1), ignored -> page, () -> false));
        String holiday = """
                <div id="kaiji-date-1">2026年11月03日</div>
                <div id="kaiji-text-1">に開示された情報はありません。</div>
                """;
        var empty = JpxDisclosureCalendar.read(DAY.withDayOfMonth(3), ignored -> holiday, () -> false);
        assertTrue(empty.rights().isEmpty());
        assertTrue(empty.annual().isEmpty());
    }

    private static JpxAutomaticFinance.Entry acquire(String archive, String filing) throws IOException {
        return JpxAutomaticFinance.acquire(CODE, DAY, null, new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) {
                return JpxIssuerArchive.read(archive, code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                assertEquals(RELEASED, disclosure.day());
                assertEquals(URI.create("https://www2.jpx.co.jp" + PATH), disclosure.annualLink());
                return filing;
            }
        });
    }

    private static JpxDailyCheck.Report report(LocalDate day, String close) {
        return new JpxDailyCheck.Report(day, "https://www.jpx.co.jp/",
                Map.of(CODE, new JpxCloseTable.Sessions(null, new BigDecimal(close))), Set.of());
    }

    private static String archive(String title, String link) {
        return """
                上場会社詳細（適時開示情報）
                <td>14200</td>
                決定事実 / 発生事実
                displayMore('1101', '1', '1')
                displayMore('1102', '1', '1')
                displayMore('1103', '0', '1')
                displayMore('1104', '0', '1')
                <tr id="1101_0"><td>2026/05/11</td><td>%s</td><td>%s</td></tr>
                <tr id="1102_0"><td>2026/11/12</td><td>自己株式の取得状況</td></tr>
                """.formatted(title, link == null ? "" : "<a href=\"" + link + "\">HTML</a>");
    }

    private static String filing() {
        return """
                <html xmlns:ix="http://www.xbrl.org/2008/inlineXBRL"
                    xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi">
                  <ix:nonNumeric contextRef="CurrentYearInstant" name="tse-ed-t:DocumentName">決算短信〔日本基準〕(連結)</ix:nonNumeric>
                  <ix:nonNumeric contextRef="CurrentYearInstant" name="tse-ed-t:FilingDate">2026年５月11日</ix:nonNumeric>
                  <ix:nonNumeric contextRef="CurrentYearInstant" name="tse-ed-t:SecuritiesCode">1420<span>0</span></ix:nonNumeric>
                  <ix:nonFraction contextRef="CurrentYearDuration_ConsolidatedMember_ResultMember"
                      name="tse-ed-t:NetIncomePerShare" unitRef="JPYPerShares" scale="0">60.00</ix:nonFraction>
                  <ix:nonFraction contextRef="NextYearDuration_ConsolidatedMember_ForecastMember"
                      name="tse-ed-t:NetIncomePerShare" unitRef="JPYPerShares" scale="0">399.99</ix:nonFraction>
                  <ix:nonFraction contextRef="CurrentYearInstant_ConsolidatedMember_ResultMember"
                      name="tse-ed-t:NetAssetsPerShare" unitRef="JPYPerShares" scale="0">1,000.00</ix:nonFraction>
                  <xbrli:unit id="JPYPerShares"><xbrli:divide>
                      <xbrli:unitNumerator><xbrli:measure>iso4217:JPY</xbrli:measure></xbrli:unitNumerator>
                      <xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>
                  </xbrli:divide></xbrli:unit>
                  %s
                  %s
                </html>
                """.formatted(context("Duration", "<xbrli:startDate>2025-04-01</xbrli:startDate>"
                        + "<xbrli:endDate>2026-03-31</xbrli:endDate>"),
                        context("Instant", "<xbrli:instant>2026-03-31</xbrli:instant>"));
    }

    private static String context(String period, String dates) {
        return """
                <xbrli:context id="CurrentYear%s_ConsolidatedMember_ResultMember">
                   <xbrli:entity><xbrli:identifier>14200</xbrli:identifier></xbrli:entity>
                   <xbrli:period>%s</xbrli:period>
                   <xbrli:scenario>
                    <xbrldi:explicitMember dimension="tse-ed-t:ResultForecastAxis">tse-ed-t:ResultMember</xbrldi:explicitMember>
                    <xbrldi:explicitMember dimension="tse-ed-t:ConsolidatedNonconsolidatedAxis">tse-ed-t:ConsolidatedMember</xbrldi:explicitMember>
                   </xbrli:scenario>
                </xbrli:context>
                """.formatted(period, dates);
    }
}
