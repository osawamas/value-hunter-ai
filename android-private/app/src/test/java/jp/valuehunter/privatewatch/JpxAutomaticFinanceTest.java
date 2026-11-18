package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;
import org.junit.Test;

import java.io.IOException;
import java.math.BigDecimal;
import java.lang.reflect.Proxy;
import java.net.URI;
import java.time.LocalDate;
import java.util.HashMap;
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

    @Test public void newFilingComparesAgainstCachedFinancialsAndAlertsOnlyOnce() throws Exception {
        var cache = new HashMap<String, Object>();
        var prefs = preferences(cache);
        LocalDate previousDay = DAY.minusDays(1);
        LocalDate beforeFiling = previousDay.minusDays(1);
        var initial = JpxAutomaticFinance.refresh(prefs, report(beforeFiling, "890"), beforeFiling,
                sources(archive("決算短信〔日本基準〕(連結)", PATH),
                        filing().replace(">60.00<", ">20.00<")), () -> false);
        var old = initial.entries().get(CODE);
        cache.put("disclosure-days", """
                {"2026-11-16":{"rights":[],"annual":["1420"]},"2026-11-17":{"rights":[],"annual":[]}}
                """);
        var latestSources = sources(archive("決算短信〔日本基準〕(連結)", PATH)
                .replace("2026/05/11", "2026/11/16"), filing().replace("2026年５月11日", "2026年11月16日"));
        var refreshed = JpxAutomaticFinance.refresh(prefs, report(DAY, "890"), DAY, latestSources, () -> false);
        assertEquals(1, refreshed.fetched());
        var next = refreshed.entries().get(CODE);
        assertEquals(old.annual(), next.annualFor(previousDay));
        assertEquals(next.annual(), next.annualFor(DAY));
        var resumed = JpxAutomaticFinance.refresh(prefs, report(DAY, "890"), DAY, null, () -> true);
        assertEquals(next, resumed.entries().get(CODE));
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "890"), report(previousDay, "890"));
        var screen = comparison.screen(new JpxShareRights(Set.of(), Set.of(), List.of()),
                new JpxAutomaticFinance.Batch(Map.of(CODE, next), Map.of(), 1, 1));
        assertEquals(1, screen.entered().size());
        assertEquals(screen.entered(), JpxWatchWorker.pending(previousDay, previousDay, DAY, screen.entered(), Set.of()));
        assertTrue(JpxWatchWorker.pending(previousDay, DAY, DAY, screen.entered(), Set.of(CODE)).isEmpty());
    }

    @Test public void alertsWhenAnExistingValueCandidateFirstFitsOneHundredShares() throws Exception {
        var entry = acquire(archive("決算短信〔日本基準〕(連結)", PATH),
                filing().replace(">60.00<", ">100.00<").replace(">1,000.00<", ">1,500.00<"));
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "1000"), report(DAY.minusDays(1), "1001"));
        var results = comparison.screen(new JpxShareRights(Set.of(), Set.of(), List.of()),
                new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1));
        assertEquals(List.of(new JpxDailyCheck.Candidate(CODE, 100, ValueCandidateScreen.Level.PRIORITY)),
                results.entered());
    }

    @Test public void rejectsExternalXmlEntitiesInPublicAnnualFilings() throws Exception {
        String malicious = filing().replaceFirst("<", "<!DOCTYPE html [<!ENTITY leak SYSTEM \"file:///etc/passwd\">]><");
        assertNull(JpxAnnualSummary.read(malicious, CODE, RELEASED,
                "https://www2.jpx.co.jp" + PATH, false));
        assertNotNull(JpxAnnualSummary.read(filing(), CODE, RELEASED,
                "https://www2.jpx.co.jp" + PATH, false));
    }

    @Test public void rejectsAnotherIssuerAndCorrectionWithoutSummary() throws Exception {
        assertNull(acquire(archive("決算短信〔日本基準〕(連結)", PATH),
                filing().replace("14200", "99990")).annual());
        assertNull(acquire(archive("（訂正）決算短信の一部訂正", null), filing()).annual());
    }

    @Test public void correctedStatementUsesOfficialReleaseAndAcceptsEraDate() throws Exception {
        var summary = filing().replace("2026年５月11日", "令和８年５月11日");
        var corrected = archive("（訂正）2026年3月期決算短信〔日本基準〕(連結)", PATH)
                .replace("2026/05/11", "2026/06/03");
        var entry = JpxAutomaticFinance.acquire(CODE, DAY, null, sources(corrected, summary));
        LocalDate release = LocalDate.of(2026, 6, 3);
        assertNotNull(entry.annual());
        assertEquals(release, entry.annual().released());
        assertNull(entry.annualFor(release));
        assertEquals(entry.annual(), entry.annualFor(release.plusDays(1)));
        assertNull(JpxAutomaticFinance.acquire(CODE, DAY, null,
                sources(corrected.replace("（訂正）", ""), summary)).annual());
        assertNull(JpxAutomaticFinance.acquire(CODE, DAY, null,
                sources(corrected, summary.replace("５月11日", "７月11日"))).annual());
    }

    @Test public void prefersTheNewestFiscalPeriodOverALateCorrectionOfAnOlderPeriod() {
        var html = archive("令和８年3月期決算短信〔日本基準〕(連結)", PATH)
                .replace("'1101', '1'", "'1101', '2'")
                + """
                <tr id="1101_1"><td>2026/05/29</td><td>（訂正）2025年3月期決算短信</td></tr>
                """;
        var page = JpxIssuerArchive.read(html, CODE);
        assertNotNull(page);
        assertEquals(URI.create("https://www2.jpx.co.jp" + PATH), page.annualOn(DAY).annualLink());
    }

    @Test public void acceptsAnExplicitlyEmptyCorporateActionSection() {
        var html = archive("2026年3月期決算短信〔日本基準〕(連結)", PATH)
                .replace("'1102', '1'", "'1102', '0'")
                .replaceAll("(?s)<tr id=\"1102_0\">.*?</tr>", "");
        assertNotNull(JpxIssuerArchive.read(html, CODE));
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

    @Test public void reopensTheJpxSessionOnAnUnexpectedSearchForm() throws Exception {
        var visits = new java.util.ArrayList<String>();
        String candidate = archive("2026年3月期決算短信〔日本基準〕(連結)", PATH);
        var session = new JpxIssuerArchive.Session((uri, code, cookies) -> {
            visits.add(uri.getPath());
            return visits.size() < 4 ? "<form name=\"JJK010010Form\">" : candidate;
        });
        assertNotNull(session.archive(CODE));
        assertEquals(List.of("/tseHpFront/StockSearch.do", "/tseHpFront/JJK010030Action.do",
                "/tseHpFront/StockSearch.do", "/tseHpFront/JJK010030Action.do"), visits);
    }

    @Test public void resumesPastAnIndividualIssuerWithATransientNetworkError() {
        var prefs = preferences(new HashMap<>());
        var report = new JpxDailyCheck.Report(DAY, "https://www.jpx.co.jp/",
                Map.of("1419", new JpxCloseTable.Sessions(null, new BigDecimal("900")),
                        CODE, new JpxCloseTable.Sessions(null, new BigDecimal("890"))), Set.of());
        var good = sources(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var checks = new java.util.ArrayList<String>();
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                checks.add(code);
                if ("1419".equals(code)) throw new IOException("Issuer timed out");
                return good.archive(code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return good.financial(disclosure);
            }
        };
        assertEquals(1, JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false).fetched());
        assertEquals(0, JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false).fetched());
        assertEquals(List.of("1419", CODE), checks);
    }

    @Test public void firstTimeOneShareCoveragePrecedesRoutineHundredShareRefresh() {
        var cache = new HashMap<String, Object>();
        var prefs = preferences(cache);
        LocalDate old = DAY.minusDays(21);
        var initial = sources(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        assertEquals(1, JpxAutomaticFinance.refresh(prefs, report(old, "890"), old, initial, () -> false).fetched());
        var dates = new org.json.JSONObject();
        for (LocalDate date = old.plusDays(1); !date.isAfter(DAY); date = date.plusDays(1)) {
            dates.put(date.toString(), new org.json.JSONObject().put("rights", new org.json.JSONArray())
                    .put("annual", new org.json.JSONArray()));
        }
        cache.put("disclosure-days", dates.toString());
        var quotes = new JpxDailyCheck.Report(DAY, "https://www.jpx.co.jp/",
                Map.of(CODE, new JpxCloseTable.Sessions(null, new BigDecimal("890")),
                        "1421", new JpxCloseTable.Sessions(null, new BigDecimal("1400"))), Set.of());
        var order = new java.util.ArrayList<String>();
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                order.add(code);
                return CODE.equals(code) ? initial.archive(code) : null;
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return initial.financial(disclosure);
            }
        };
        assertEquals(2, JpxAutomaticFinance.refresh(prefs, quotes, DAY, network, () -> false).fetched());
        assertEquals(List.of("1421", CODE), order);
    }

    private static JpxAutomaticFinance.Sources sources(String archive, String filing) {
        return new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) {
                return JpxIssuerArchive.read(archive, code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                return filing;
            }
        };
    }

    private static SharedPreferences preferences(Map<String, Object> data) {
        return (SharedPreferences) Proxy.newProxyInstance(SharedPreferences.class.getClassLoader(),
                new Class<?>[]{SharedPreferences.class}, (instance, method, args) -> switch (method.getName()) {
                    case "getString", "getLong" -> data.getOrDefault(args[0].toString(), args[1]);
                    case "edit" -> Proxy.newProxyInstance(SharedPreferences.Editor.class.getClassLoader(),
                            new Class<?>[]{SharedPreferences.Editor.class}, (editor, change, values) -> {
                                switch (change.getName()) {
                                    case "putString", "putLong" -> data.put(values[0].toString(), values[1]);
                                    case "remove" -> data.remove(values[0].toString());
                                    case "apply" -> { return null; }
                                    default -> throw new IllegalStateException(change.getName());
                                }
                                return editor;
                            });
                    default -> throw new IllegalStateException(method.getName());
                });
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
