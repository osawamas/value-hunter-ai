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

    @Test public void bookDiscountRequiresNarrowingLossAndPreservedEquity() {
        var close = new BigDecimal("400");
        var book = new BigDecimal("1000");
        var priorBook = new BigDecimal("1100");
        var loss = new BigDecimal("-30");
        var priorLoss = new BigDecimal("-60");
        assertEquals(1, JpxOperatingValuation.assessRecoverableBook(close, book, priorBook, loss, priorLoss)
                .level(ValueAlertMeter.DEFAULT));
        assertEquals(0, JpxOperatingValuation.assessRecoverableBook(new BigDecimal("600"),
                book, priorBook, loss, priorLoss).level(ValueAlertMeter.DEFAULT));
        assertNull(JpxOperatingValuation.assessRecoverableBook(close, book, priorBook, priorLoss, loss));
        assertNull(JpxOperatingValuation.assessRecoverableBook(close, book, new BigDecimal("1200"), loss, priorLoss));
        assertNull(JpxOperatingValuation.assessRecoverableBook(close, book, priorBook,
                new BigDecimal("-51"), new BigDecimal("-80")));
    }

    @Test public void correctedTdnetRowsUseTheCurrentTitleAndKeepTheWholePage() throws Exception {
        String day = """
                <div id="kaiji-date-1">2026年11月17日</div>
                <div class="kaijiSum">1～2件&nbsp;/&nbsp;全2件</div>
                <tr class="hyodaiUpd"><td class="oddnew-L kjTime">10:00</td><td class="oddnew-M kjCode">55790</td>
                <td class="oddnew-M kjName">ＧＳＩ</td><td class="oddnew-M kjTitle">
                <a>第２四半期決算説明資料</a><BR><s>2026年3月期決算短信〔日本基準〕(連結)</s></td></tr>
                <tr><td class="evennew-L kjTime">10:01</td><td class="evennew-M kjCode">14200</td>
                <td class="evennew-M kjName">会社</td><td class="evennew-M kjTitle">
                <a>2026年3月期決算短信〔日本基準〕(連結)</a></td></tr>
                """;
        var result = JpxDisclosureCalendar.read(DAY, ignored -> day, () -> false);
        assertEquals(Set.of(CODE), result.annual());
    }

    @Test public void temporarilyUnavailableFilingKeepsVerifiedAnnualForRecovery() throws Exception {
        var valid = acquire(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var missing = JpxAutomaticFinance.acquire(CODE, DAY, valid, new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                throw new JpxIssuerArchive.HttpFailure(404);
            }
            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                throw new AssertionError("Cannot read a missing filing");
            }
        });
        assertNull(missing.annual());
        assertEquals(valid.annual(), missing.previousAnnual());
        assertFalse(missing.failure(CODE, DAY, Map.of()).isEmpty());
        var pair = new JpxDailyCheck.Comparison(report(DAY, "600"), report(DAY.minusDays(1), "950"));
        var finance = new JpxAutomaticFinance.Batch(Map.of(CODE, missing), Map.of(), 1, 1);
        var screen = pair.screen(new JpxShareRights(Set.of(), Set.of(), List.of()), finance);
        assertFalse(screen.assessedCodes().contains(CODE));
        assertTrue(screen.holds().stream().anyMatch(hold -> CODE.equals(hold.code())
                && missing.hold().equals(hold.reason())));
        var retried = JpxAutomaticFinance.acquire(CODE, DAY, missing,
                sources(archive("決算短信〔日本基準〕(連結)", PATH), filing()));
        assertEquals(valid.annual(), retried.annual());
        assertEquals("", retried.hold());
        assertNull(retried.previousAnnual());
    }

    @Test public void tdnetRepairsOtherDaysWhenOneDateIsUnavailable() throws Exception {
        var cache = new HashMap<String, Object>();
        var latest = java.time.LocalDate.of(2026, 11, 17);
        var older = latest.minusDays(1);
        String empty = "<div id=\"kaiji-date-1\">2026年11月16日</div>に開示された情報はありません";
        var days = JpxDisclosureCalendar.refresh(preferences(cache), latest, older, () -> false,
                url -> {
                    if (url.toString().endsWith("20261117.html")) throw new IOException("Individual date unavailable");
                    return empty;
                }, null);
        assertFalse(days.containsKey(latest));
        assertTrue(days.containsKey(older));
        var saved = new org.json.JSONObject((String) cache.get("disclosure-days"));
        cache.put("disclosure-days", saved.put("invalid date", new org.json.JSONObject()).toString());
        var next = JpxDisclosureCalendar.refresh(preferences(cache), latest, older, () -> false,
                url -> { throw new IOException("offline"); }, null);
        assertEquals(days, next);
    }

    @Test public void meterUsesVerifiedPreviousReportWhenPhoneHasNeverScoredTheIssuer() throws Exception {
        var state = preferences(new HashMap<>());
        var priorDay = DAY.minusDays(1);
        var valid = acquire(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var finance = new JpxAutomaticFinance.Batch(Map.of(CODE, valid), Map.of(), 1, 1);
        var rights = new JpxShareRights(Set.of(), Set.of(), List.of());
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "600"), report(priorDay, "950"));
        var screen = comparison.screen(rights, finance);
        assertTrue(screen.holds().stream().noneMatch(hold -> CODE.equals(hold.code())));
        assertNull(ValueAlertPreview.history(state, ValueAlertPreview.Market.JPX).latest());

        var edit = state.edit();
        var pair = JpxWatchWorker.saveMeter(state, edit, comparison, screen, finance, rights);
        var entries = ValueAlertPreview.entries(state, ValueAlertPreview.Market.JPX, DAY, "JPX",
                pair.rows(), pair.prior(), Set.of(), code -> code);
        assertEquals(Set.of("meter:1:" + CODE), entries.keySet());
        assertTrue(edit.commit());
        assertEquals(priorDay, ValueAlertPreview.history(state, ValueAlertPreview.Market.JPX).previous().day());
        assertTrue(ValueAlertPreview.entries(state, ValueAlertPreview.Market.JPX, DAY, "JPX",
                pair.rows(), pair.prior(), entries.keySet(), code -> code).isEmpty());

        var gap = new JpxDailyCheck.Comparison(report(DAY, "600"), report(priorDay.minusDays(3), "950"));
        var noPrior = JpxWatchWorker.saveMeter(state, state.edit(), gap, gap.screen(rights, finance), finance, rights);
        assertNull(noPrior.prior());
    }

    @Test public void missingBookValueDoesNotPreventFlexibleAssessment() throws Exception {
        var latest=new JpxAnnualSummary.Annual(LocalDate.of(2026,3,31),RELEASED,new BigDecimal("60"),null,"current");
        var previous=new JpxAnnualSummary.Annual(LocalDate.of(2025,3,31),LocalDate.of(2025,5,12),
                new BigDecimal("50"),new BigDecimal("940"),"prior");
        var entry=new JpxAutomaticFinance.Entry(DAY,latest,"",previous);
        var batch=new JpxAutomaticFinance.Batch(Map.of(CODE,entry),Map.of(),1,1);
        var rights=new JpxShareRights(Set.of(),Set.of(),List.of());
        var comparison=new JpxDailyCheck.Comparison(report(DAY,"300"),report(DAY.minusDays(1),"1000"));
        var screen=comparison.screen(rights,batch);
        assertFalse(screen.assessedCodes().contains(CODE));
        var row=comparison.meterRows(screen,batch,rights).getJSONArray(CODE);
        assertEquals(1,row.getInt(1));
        assertEquals(2,row.getInt(2));
        assertEquals(100,row.getInt(3));
    }

    @Test public void verifiedPriorBookCanSupportSecondFlexibleTier() throws Exception {
        var latest = new JpxAnnualSummary.Annual(LocalDate.of(2026, 3, 31), RELEASED,
                new BigDecimal("60"), null, "current", List.of(), "ConsolidatedMember/NetIncomePerShare");
        var prior = new JpxAnnualSummary.Annual(LocalDate.of(2025, 3, 31), LocalDate.of(2025, 5, 12),
                new BigDecimal("50"), new BigDecimal("940"), "prior", List.of(), latest.reportingBasis());
        var entry = new JpxAutomaticFinance.Entry(DAY, latest, "", prior);
        var batch = new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1);
        var rights = new JpxShareRights(Set.of(), Set.of(), List.of());
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "300"), null);
        var screen = comparison.screen(rights, batch);
        assertFalse(screen.assessedCodes().contains(CODE));
        var row = comparison.meterRows(screen, batch, rights).getJSONArray(CODE);
        assertEquals(2, row.getInt(1));
        assertEquals(3, row.getInt(2));
    }

    @Test public void operatingFactsRescueALossAndKeepWeakBalanceOutOfCheapTiers() throws Exception {
        String source = "https://www2.jpx.co.jp/disc/14200/100920260511000001.html";
        String instant = "CurrentYearInstant_ConsolidatedMember_ResultMember";
        String duration = "CurrentYearDuration_ConsolidatedMember_ResultMember";
        String shares = "CurrentYearInstant_NonConsolidatedMember_ResultMember";
        String prior = "PriorYearDuration_ConsolidatedMember_ResultMember";
        String details = """
                <xbrli:unit id="JPY"><xbrli:measure>iso4217:JPY</xbrli:measure></xbrli:unit>
                <xbrli:unit id="Shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>
                """ + context("Instant", "<xbrli:instant>2026-03-31</xbrli:instant>")
                        .replace("ConsolidatedMember", "NonConsolidatedMember")
                + context("Duration", "<xbrli:startDate>2024-04-01</xbrli:startDate>"
                        + "<xbrli:endDate>2025-03-31</xbrli:endDate>").replace("CurrentYear", "PriorYear")
                + operatingFact(duration, "CashFlowsFromOperatingActivities", "JPY", 6, 25)
                + operatingFact(duration, "NetSales", "JPY", 6, 300)
                + operatingFact(instant, "TotalAssets", "JPY", 6, 500)
                + operatingFact(instant, "NetAssets", "JPY", 6, 300)
                + operatingFact(duration, "OperatingIncome", "JPY", 6, 20)
                + operatingFact(prior, "OperatingIncome", "JPY", 6, 15)
                + operatingFact(shares, "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock",
                        "Shares", 0, 1_000_000);
        String xml = filing().replace(">60.00</ix:nonFraction>", " sign=\"-\">60.00</ix:nonFraction>")
                .replace("</html>", details + "</html>");
        var annual = JpxAnnualSummary.read(xml, CODE, RELEASED, source, false);
        assertNotNull(annual);
        assertNotNull(annual.operating());
        assertEquals(25_000_000, annual.operating().cashFlow().intValueExact());
        String cashFact = operatingFact(duration, "CashFlowsFromOperatingActivities", "JPY", 6, 25);
        var withoutCash = JpxAnnualSummary.read(xml.replace(cashFact, ""), CODE, RELEASED, source, false);
        assertNotNull(withoutCash.operating());
        assertNull(withoutCash.operating().cashFlow());
        assertEquals(1, JpxOperatingValuation.assess(withoutCash, DAY, new BigDecimal("110")).ceiling());
        assertNull(JpxOperatingValuation.assess(withoutCash, DAY, new BigDecimal("150")));
        assertEquals(2, JpxOperatingValuation.assess(withoutCash, DAY, new BigDecimal("50"))
                .level(ValueAlertMeter.DEFAULT));

        var malformedCash = JpxAnnualSummary.read(xml.replace(cashFact, cashFact.replace("JPY", "Shares")),
                CODE, RELEASED, source, false);
        assertNull(malformedCash.operating());

        String stable = xml.replace(operatingFact(duration, "OperatingIncome", "JPY", 6, 20),
                operatingFact(duration, "OperatingIncome", "JPY", 6, 35))
                .replace(operatingFact(prior, "OperatingIncome", "JPY", 6, 15),
                        operatingFact(prior, "OperatingIncome", "JPY", 6, 36));
        String priorCash = operatingFact(prior, "CashFlowsFromOperatingActivities", "JPY", 6, 24);
        var established = JpxAnnualSummary.read(stable.replace("</html>", priorCash + "</html>"),
                CODE, RELEASED, source, false);
        assertEquals(3, JpxOperatingValuation.assess(established, DAY, new BigDecimal("100")).ceiling());
        var unknownHistory = JpxAnnualSummary.read(stable, CODE, RELEASED, source, false);
        assertEquals(1, JpxOperatingValuation.assess(unknownHistory, DAY, new BigDecimal("100")).ceiling());

        var tier3 = JpxOperatingValuation.assess(annual, DAY, new BigDecimal("100"));
        assertEquals(3, tier3.level(ValueAlertMeter.DEFAULT));
        assertEquals(2, JpxOperatingValuation.assess(annual, DAY, new BigDecimal("150")).ceiling());
        assertEquals(1, JpxOperatingValuation.assess(annual, DAY, new BigDecimal("220")).ceiling());
        var weak = JpxAnnualSummary.read(xml.replace(">300</ix:nonFraction>", ">20</ix:nonFraction>"),
                CODE, RELEASED, source, false);
        assertEquals(0, JpxOperatingValuation.assess(weak, DAY, new BigDecimal("100")).ceiling());

        var comparison = new JpxDailyCheck.Comparison(report(DAY, "100"), null);
        var entry = new JpxAutomaticFinance.Entry(DAY, annual, "");
        var batch = new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1);
        var rights = new JpxShareRights(Set.of(), Set.of(), List.of());
        var screen = comparison.screen(rights, batch);
        assertFalse(screen.assessedCodes().contains(CODE));
        assertEquals(3, comparison.meterRows(screen, batch, rights).getJSONArray(CODE).getInt(1));
        var dilution = new JpxDisclosureCalendar.Day(Set.of(), Set.of(), Set.of(CODE));
        var dated = new JpxAutomaticFinance.Entry(DAY.minusDays(1), annual, "");
        var held = new JpxAutomaticFinance.Batch(Map.of(CODE, dated), Map.of(DAY, dilution), 1, 1);
        assertFalse(comparison.meterRows(comparison.screen(rights, held), held, rights).has(CODE));
        assertNull(JpxAnnualSummary.read(xml.replace("iso4217:JPY</xbrli:measure></xbrli:unit>",
                "iso4217:USD</xbrli:measure></xbrli:unit>"), CODE, RELEASED, source, false).operating());
    }

    private static String operatingFact(String context, String tag, String unit, int scale, long value) {
        return """
                <ix:nonFraction contextRef="%s" name="tse-ed-t:%s" unitRef="%s" scale="%d">%d</ix:nonFraction>
                """.formatted(context, tag, unit, scale, value);
    }

    @Test public void twoComparableAnnualFilingsEnableRealJpxUltraValueMeterAndPromotion() throws Exception {
        var latest = new JpxAnnualSummary.Annual(LocalDate.of(2026, 3, 31), RELEASED,
                new BigDecimal("60"), new BigDecimal("1000"), "current-verified");
        var previousAnnual = new JpxAnnualSummary.Annual(LocalDate.of(2025, 3, 31),
                LocalDate.of(2025, 5, 12), new BigDecimal("50"), new BigDecimal("940"), "prior-verified");
        var entry = new JpxAutomaticFinance.Entry(DAY, latest, "", previousAnnual);
        var batch = new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1);
        var rights = new JpxShareRights(Set.of(), Set.of(), List.of());
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "300"), report(DAY.minusDays(1), "1000"));
        var screen = comparison.screen(rights, batch);
        assertEquals(1, screen.assessed());
        var current = comparison.meterRows(screen, batch, rights).getJSONArray(CODE);
        var prior = comparison.previousMeterRows(screen, batch, rights).getJSONArray(CODE);
        assertEquals(3, current.getInt(1)); // strict JPX level-three ceiling
        assertEquals(3, current.getInt(2)); // cannot claim unknown cash or peers were verified
        assertTrue(current.getInt(0) >= 85);
        assertEquals(0, prior.getInt(1));
        assertEquals(100, current.getInt(3));

        var state = preferences(new HashMap<>());
        var pair = JpxWatchWorker.saveMeter(state, state.edit(), comparison, screen, batch, rights);
        var entries = ValueAlertPreview.entries(state, ValueAlertPreview.Market.JPX,
                DAY, "JPX", pair.rows(), pair.prior(), Set.of(), code -> code);
        assertEquals(Set.of("meter:3:" + CODE), entries.keySet());
        assertTrue(ValueAlertPreview.entries(state, ValueAlertPreview.Market.JPX,
                DAY, "JPX", pair.rows(), pair.prior(), entries.keySet(), code -> code).isEmpty());

        // A single fiscal year must not be promoted by simply omitting the older EPS.
        var incomplete = new JpxAutomaticFinance.Batch(
                Map.of(CODE, new JpxAutomaticFinance.Entry(DAY, latest, "")), Map.of(), 1, 1);
        var weak = comparison.meterRows(comparison.screen(rights, incomplete), incomplete, rights)
                .getJSONArray(CODE);
        assertTrue(weak.getInt(1) < 3);
    }

    @Test public void refreshedTdnetCorrectionInvalidatesAPreviouslyClearTradingDay() throws Exception {
        var cache = new HashMap<String, Object>();
        var older = DAY.minusDays(1);
        String empty = "<div id=\"kaiji-date-1\">2026年11月16日</div>に開示された情報はありません";
        var initial = JpxDisclosureCalendar.refresh(preferences(cache), older, older, () -> false,
                url -> empty, older);
        assertTrue(initial.get(older).rights().isEmpty());

        var filing = acquire(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var entry = new JpxAutomaticFinance.Entry(older.minusDays(1), filing.annual(), "");
        assertEquals("", entry.failure(CODE, older, initial));
        String corrected = """
                <div id="kaiji-date-1">2026年11月16日</div>
                <div class="kaijiSum">1～1件&nbsp;/&nbsp;全1件</div>
                <tr class="hyodaiUpd"><td class="oddnew-L kjTime">15:00</td><td class="oddnew-M kjCode">14200</td>
                <td class="oddnew-M kjName">会社</td><td class="oddnew-M kjTitle"><a>株式分割</a>
                <s>その他のお知らせ</s></td></tr>
                """;
        var resumed = JpxDisclosureCalendar.refresh(preferences(cache), older, older, () -> false,
                url -> corrected, older);
        assertEquals(Set.of(CODE), resumed.get(older).rights());
        assertFalse(entry.failure(CODE, older, resumed).isEmpty());

        var offline = JpxDisclosureCalendar.refresh(preferences(cache), older, older, () -> false,
                url -> { throw new IOException("offline"); }, older);
        assertFalse(offline.containsKey(older));
        assertFalse(entry.failure(CODE, older, offline).isEmpty());
    }

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
                {"2026-11-16":{"rights":[],"annual":["1420"],"dilution":[]},
                 "2026-11-17":{"rights":[],"annual":[],"dilution":[]}}
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
        assertEquals(0, comparison.priceOnly(results).assessed());
    }

    @Test public void heldFinancialRecordStillAllowsAnIndependentBudgetAlertAfterRetry() throws Exception {
        var entry = acquire(archive("決算短信〔日本基準〕(連結)", PATH),
                filing().replace(">60.00<", ">0.00<"));
        assertNotNull(entry.annual());
        var before = DAY.minusDays(1);
        var comparison = new JpxDailyCheck.Comparison(report(DAY, "1000"), report(before, "1001"));
        var screen = comparison.screen(new JpxShareRights(Set.of(), Set.of(), List.of()),
                new JpxAutomaticFinance.Batch(Map.of(CODE, entry), Map.of(), 1, 1));
        assertEquals(0, screen.assessed());
        assertTrue(screen.entered().isEmpty());

        var budget = comparison.priceOnly(screen);
        assertEquals(1, budget.assessed());
        assertEquals(List.of(new PriceOnlyScreen.BudgetEntry(CODE, new BigDecimal("100000"))), budget.entered());
        assertEquals(budget.entered(), JpxWatchWorker.pendingBudget(before, before, DAY, budget.entered(), Set.of()));
        assertEquals(budget.entered(), JpxWatchWorker.pendingBudget(before, DAY, DAY, budget.entered(), Set.of()));
        assertTrue(JpxWatchWorker.pendingBudget(before, DAY, DAY, budget.entered(),
                Set.of("price-budget:" + CODE)).isEmpty());
    }

    @Test public void missingBookValueCanUseVerifiedPriorAnnualFromTheArchive() throws Exception {
        String source = "https://www2.jpx.co.jp" + PATH;
        String earlierSource = source.replace("/140120", "/140119");
        var earlierDay = RELEASED.minusYears(1);
        var page = new JpxIssuerArchive.Page(List.of(
                new JpxIssuerArchive.Disclosure(RELEASED, "2026年3月期決算短信", java.net.URI.create(source), null, true),
                new JpxIssuerArchive.Disclosure(earlierDay, "2025年3月期決算短信", java.net.URI.create(earlierSource), null, true)));
        String current = filing().replace("name=\"tse-ed-t:NetAssetsPerShare\"", "name=\"tse-ed-t:AbsentBookValue\"");
        String prior = filing().replace("2026年５月11日", "2025年5月11日")
                .replace("2025-04-01", "2024-04-01").replace("2026-03-31", "2025-03-31");
        var entry = JpxAutomaticFinance.acquire(CODE, DAY, null, new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) { return page; }
            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                return disclosure.day().equals(RELEASED) ? current : prior;
            }
        });
        assertNotNull(entry.annual());
        assertNull(entry.annual().bps());
        assertNotNull(entry.previousAnnual());
        assertEquals(earlierDay, entry.previousAnnual().released());
    }

    @Test public void retriesSameDayParserHoldsAfterAnUpgrade() throws Exception {
        var data = new HashMap<String, Object>();
        data.put("annual-" + CODE, new org.json.JSONObject().put("checked", DAY.toString())
                .put("hold", "通期EPS・BPSを照合できなかった").toString());
        data.put("repair-after-" + CODE, 100L);
        var state = preferences(data);
        var report = new JpxDailyCheck.Report(DAY, "", Map.of(CODE,
                new JpxCloseTable.Sessions(BigDecimal.valueOf(100), null)), Set.of());
        var source = sources(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var recovered = JpxAutomaticFinance.refresh(state, report, DAY, source, () -> false, () -> 1L);
        assertEquals(1, recovered.fetched());
        assertNotNull(recovered.entries().get(CODE).annual());
        assertEquals(0, JpxAutomaticFinance.refresh(state, report, DAY, source, () -> false, () -> 2L).fetched());
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

    @Test public void flushesCompletedIssuersBeforeResumingAnInterruptedBatch() {
        var commits = new java.util.concurrent.atomic.AtomicInteger();
        var disconnected = new java.util.concurrent.atomic.AtomicBoolean();
        var prefs = preferences(new HashMap<>(), () -> { commits.incrementAndGet(); return true; });
        var report = new JpxDailyCheck.Report(DAY, "https://www.jpx.co.jp/",
                Map.of("1419", new JpxCloseTable.Sessions(null, new BigDecimal("900")),
                        CODE, new JpxCloseTable.Sessions(null, new BigDecimal("890"))), Set.of());
        var good = sources(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var checks = new java.util.ArrayList<String>();
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                checks.add(code);
                if (CODE.equals(code) && !disconnected.get()) {
                    disconnected.set(true);
                    throw new IOException("Wi-Fi disconnected");
                }
                return good.archive(code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return good.financial(disclosure);
            }
        };
        var first = JpxAutomaticFinance.refresh(prefs, report, DAY, network, disconnected::get);
        assertEquals(Set.of("1419"), first.entries().keySet());
        assertEquals(1, commits.get());
        var resumed = JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false);
        assertEquals(Set.of("1419", CODE), resumed.entries().keySet());
        assertEquals(List.of("1419", CODE, CODE), checks);
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

    @Test public void retriesPendingFinancialsOnTheSameDayAfterCooldown() {
        var prefs = preferences(new HashMap<>());
        var report = new JpxDailyCheck.Report(DAY, "https://www.jpx.co.jp/",
                Map.of("1419", new JpxCloseTable.Sessions(null, new BigDecimal("900")),
                        CODE, new JpxCloseTable.Sessions(null, new BigDecimal("890"))), Set.of());
        var good = sources(archive("決算短信〔日本基準〕(連結)", PATH), filing());
        var checks = new java.util.ArrayList<String>();
        var now = new java.util.concurrent.atomic.AtomicLong(1L);
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                checks.add(code);
                return "1419".equals(code) && now.get() == 1 ? null : good.archive(code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return good.financial(disclosure);
            }
        };

        JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false, now::get);
        assertEquals(0, JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false, now::get).fetched());
        now.addAndGet(java.util.concurrent.TimeUnit.HOURS.toMillis(2));
        assertEquals(1, JpxAutomaticFinance.refresh(prefs, report, DAY, network, () -> false, now::get).fetched());
        assertEquals(List.of("1419", CODE, "1419"), checks);
    }

    @Test public void fullListingQueueContinuesFromSavedEntriesAfterRateLimit() {
        var quotes = new HashMap<String, JpxCloseTable.Sessions>();
        for (int code = 1000; code < 4686; code++)
            quotes.put(Integer.toString(code), new JpxCloseTable.Sessions(null, new BigDecimal("890")));
        var report = new JpxDailyCheck.Report(DAY, "https://www.jpx.co.jp/", Map.copyOf(quotes), Set.of());
        var cache = new HashMap<String, Object>();
        var scanned = new java.util.HashSet<String>();
        var calls = new java.util.concurrent.atomic.AtomicInteger();
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                if (calls.incrementAndGet() == 10) throw new JpxIssuerArchive.HttpFailure(429);
                assertTrue(scanned.add(code));
                return new JpxIssuerArchive.Page(List.of());
            }
            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                throw new AssertionError("This replay exercises the queue without requesting filings");
            }
        };
        var clock = new java.util.concurrent.atomic.AtomicLong(1);
        var first = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network, () -> false, clock::get);
        assertEquals(9, first.fetched());
        assertTrue(first.status().contains("初回確認待ち 3677銘柄"));
        long resumeAt = clock.get() + java.util.concurrent.TimeUnit.HOURS.toMillis(1);
        assertEquals(resumeAt, JpxWatchWorker.nextFinanceStart(clock.get(), true, true, first));
        assertEquals(0, JpxWatchWorker.nextFinanceStart(clock.get(), true, false, first));
        clock.addAndGet(java.util.concurrent.TimeUnit.MINUTES.toMillis(30));
        var pause = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network, () -> false, clock::get);
        assertEquals(0, pause.fetched());
        assertEquals(resumeAt, JpxWatchWorker.nextFinanceStart(clock.get(), true, true, pause));
        assertEquals(10, calls.get());
        clock.addAndGet(java.util.concurrent.TimeUnit.MINUTES.toMillis(30));
        int passes = 1;
        while (scanned.size() < quotes.size() && passes < 165) {
            var batch = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network, () -> false, clock::get);
            long expected = scanned.size() < quotes.size() ? clock.get() + 900_000 : 0;
            assertEquals(expected, JpxWatchWorker.nextFinanceStart(clock.get(), true, true, batch));
            assertEquals(0, JpxWatchWorker.nextFinanceStart(clock.get(), true, false, batch));
            assertEquals(expected, JpxWatchWorker.nextFinanceStart(clock.get(), false, false, batch));
            passes++;
        }
        assertEquals(21, passes);
        assertEquals(quotes.keySet(), scanned);
        assertEquals(quotes.size() + 1, calls.get());
        assertEquals(0, JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network,
                () -> false, clock::get).fetched());
    }

    @Test public void extendsHealthyInitialBatchesButKeepsTimeAndFailureGuards() {
        var quotes = new HashMap<String, JpxCloseTable.Sessions>();
        for (int code = 1400; code < 1600; code++)
            quotes.put(Integer.toString(code), new JpxCloseTable.Sessions(null, new BigDecimal("890")));
        var report = new JpxDailyCheck.Report(DAY, "", Map.copyOf(quotes), Set.of());
        record Replay(String name, long baseMillis, long extensionMillis, long finalMillis,
                      int failingRequest, IOException failure, int expectedCalls) {}
        var replays = List.of(
                new Replay("fast throughout", 700, 700, 700, -1, null, 192),
                new Replay("final time cap", 700, 700, 2000, -1, null, 177),
                new Replay("first extension too slow for the final extension", 720, 900, 900, -1, null, 144),
                new Replay("extended time cap", 700, 1700, 1700, -1, null, 128),
                new Replay("original time cap", 800, 800, 800, -1, null, 94),
                new Replay("original deadline crossed after request 96", 785, 785, 785, -1, null, 96),
                new Replay("early timeout", 0, 0, 0, 1, new IOException("Issuer timed out"), 96),
                new Replay("503 during first extension", 0, 0, 0, 105,
                        new JpxIssuerArchive.HttpFailure(503, "7200"), 105),
                new Replay("429 during final extension", 0, 0, 0, 155,
                        new JpxIssuerArchive.HttpFailure(429, "7200"), 155));
        for (var replay : replays) {
            var elapsed = new java.util.concurrent.atomic.AtomicLong();
            var calls = new java.util.concurrent.atomic.AtomicInteger();
            var cache = new HashMap<String, Object>();
            var source = new JpxAutomaticFinance.Sources() {
                @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                    int call = calls.incrementAndGet();
                    long millis = replay.baseMillis();
                    if (call > 144) millis = replay.finalMillis();
                    else if (call > 96) millis = replay.extensionMillis();
                    elapsed.addAndGet(java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(millis));
                    if (call == replay.failingRequest()) throw replay.failure();
                    return new JpxIssuerArchive.Page(List.of());
                }
                @Override public String financial(JpxIssuerArchive.Disclosure disclosure) {
                    throw new AssertionError();
                }
            };
            var result = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, source, () -> false, () -> 1,
                    elapsed::get, uri -> { throw new AssertionError(uri); }, null);
            assertEquals(replay.name(), replay.expectedCalls(), calls.get());
            assertEquals(replay.name(), replay.expectedCalls() - (replay.failure() == null ? 0 : 1), result.fetched());
            boolean limited = replay.failure() instanceof JpxIssuerArchive.HttpFailure;
            assertEquals(replay.name(), !limited, result.continueInitial());
            if (limited) {
                var cooled = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, source, () -> false,
                        () -> 7_200_000, elapsed::get, uri -> { throw new AssertionError(uri); }, null);
                assertEquals(0, cooled.fetched());
                assertEquals(replay.expectedCalls(), calls.get());
            }
        }
    }

    @Test public void slowSourcesStopNewRequestsAtTheTimeBudgetAndResumeTheRest() {
        var quotes = new HashMap<String, JpxCloseTable.Sessions>();
        for (int code = 1400; code < 1406; code++)
            quotes.put(Integer.toString(code), new JpxCloseTable.Sessions(null, new BigDecimal("890")));
        var report = new JpxDailyCheck.Report(DAY, "", Map.copyOf(quotes), Set.of());
        var saved = new HashMap<String, Object>();
        var elapsed = new java.util.concurrent.atomic.AtomicLong();
        var calls = new java.util.ArrayList<String>();
        var source = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) {
                calls.add(code);
                elapsed.addAndGet(java.util.concurrent.TimeUnit.SECONDS.toNanos(30));
                return new JpxIssuerArchive.Page(List.of());
            }
            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) { throw new AssertionError(); }
        };
        for (int pass = 0; pass < 2; pass++) {
            var run = JpxAutomaticFinance.refresh(preferences(saved), report, DAY, source, () -> false, () -> 1,
                    elapsed::get, uri -> { throw new AssertionError(uri); }, null);
            assertEquals(3, run.fetched());
            assertEquals(pass == 0 ? 901_000 : 0, JpxWatchWorker.nextFinanceStart(1_000, true, true, run));
        }
        assertEquals(List.of("1400", "1401", "1402", "1403", "1404", "1405"), calls);
        var unwritten = JpxAutomaticFinance.refresh(preferences(new HashMap<>(), () -> false), report, DAY, source,
                () -> false, () -> 1, elapsed::get, uri -> { throw new AssertionError(uri); }, null);
        assertEquals(3, unwritten.fetched());
        assertEquals(0, JpxWatchWorker.nextFinanceStart(1_000, true, true, unwritten));
    }

    @Test public void archiveRateLimitHonorsAProviderDelayLongerThanAnHour() {
        long now = java.time.Instant.parse("2026-11-19T00:00:00Z").toEpochMilli();
        assertEquals(now + 7_200_000, JpxAutomaticFinance.archiveRetryAt(now, "7200"));
        assertEquals(now + 7_200_000, JpxAutomaticFinance.archiveRetryAt(now, "Thu, 19 Nov 2026 02:00:00 GMT"));
        assertEquals(now + 3_600_000, JpxAutomaticFinance.archiveRetryAt(now, "30"));
        assertEquals(now + 3_600_000, JpxAutomaticFinance.archiveRetryAt(now, "invalid"));
    }

    @Test public void firstTimeOneShareCoveragePrecedesRoutineHundredShareRefresh() throws Exception {
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

    @Test public void verifiedHistoricSplitCanBeScreenedAndLaterOrUncertainActionsStayHeld() throws Exception {
        String link = "/disc/14200/140120251112000000.pdf";
        String archive = archive("決算短信〔日本基準〕(連結)", PATH).replace("2026/11/12", "2025/11/12")
                .replace("自己株式の取得状況", "<a href=\"" + link + "\">株式分割に関するお知らせ</a>");
        var filingSources = sources(archive, filing());
        var proof = new java.util.concurrent.atomic.AtomicReference<>(
                "株式分割に関するお知らせ　基準日 2025年11月30日　効力発生日 令和7年12月1日");
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                return filingSources.archive(code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return filingSources.financial(disclosure);
            }

            @Override public LocalDate effective(JpxIssuerArchive.Disclosure disclosure) {
                assertEquals(URI.create("https://www2.jpx.co.jp" + link), disclosure.pdfLink());
                return JpxCorporateActionDate.effective(proof.get(), disclosure);
            }
        };
        assertEquals("", JpxAutomaticFinance.acquire(CODE, DAY, null, network).hold());
        proof.set("株式分割　基準日 2026年3月31日　効力発生日 2026年4月1日");
        assertFalse(JpxAutomaticFinance.acquire(CODE, DAY, null, network).hold().isEmpty());
        proof.set("株式分割　基準日 2025年11月30日　定款変更の効力発生日 2025年12月1日");
        assertFalse(JpxAutomaticFinance.acquire(CODE, DAY, null, network).hold().isEmpty());
        proof.set("株式分割　基準日 2025年11月30日　効力発生日 2025年12月1日　効力発生日 2026年4月1日");
        assertFalse(JpxAutomaticFinance.acquire(CODE, DAY, null, network).hold().isEmpty());
    }

    @Test public void transientShareActionFailureDoesNotFinalizeTheFinancialCheckpoint() throws Exception {
        String link = "/disc/14200/140120251112000000.pdf";
        String html = archive("決算短信〔日本基準〕(連結)", PATH).replace("2026/11/12", "2025/11/12")
                .replace("自己株式の取得状況", "<a href=\"" + link + "\">株式分割に関するお知らせ</a>");
        var filingSources = sources(html, filing());
        var calls = new java.util.concurrent.atomic.AtomicInteger();
        var network = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                return filingSources.archive(code);
            }
            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return filingSources.financial(disclosure);
            }
            @Override public LocalDate effective(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                if (calls.getAndIncrement() == 0) throw new JpxIssuerArchive.HttpFailure(503);
                return LocalDate.of(2025, 12, 1);
            }
        };
        var cache = new HashMap<String, Object>();
        var report = report(DAY, "890");
        var stopped = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network, () -> false, () -> 1);
        assertEquals(0, stopped.fetched());
        assertFalse(cache.containsKey("annual-" + CODE));

        var resumed = JpxAutomaticFinance.refresh(preferences(cache), report, DAY, network, () -> false,
                () -> 1 + java.util.concurrent.TimeUnit.HOURS.toMillis(1));
        assertEquals(1, resumed.fetched());
        assertEquals("", resumed.entries().get(CODE).hold());
        assertEquals(1, JpxAutomaticFinance.refresh(preferences(cache), report, DAY, null, () -> true).entries().size());
    }

    @Test public void appliesVerifiedSplitOnlyOnAndAfterTheOfficialExDay() throws Exception {
        var rights = JpxShareRights.parse("""
                {"revision":"2026-11-18T18:32:00Z", "coveredCodes":["9999"], "notices":[],
                 "monthlySources":{"2026-11":"https://www.jpx.co.jp/report.pdf"},
                 "adjustments":[["1420","2026-11-17","2026-11-18","1","2"]]}
                """).rights();
        String html = archive("決算短信〔日本基準〕(連結)", PATH)
                .replace("自己株式の取得状況", "<a href=\"/disc/14200/140120261112500000.pdf\">株式分割に関するお知らせ</a>");
        var text = "株式分割　基準日 2026年11月18日　効力発生日 2026年11月19日";
        var sources = new JpxAutomaticFinance.Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) {
                return JpxIssuerArchive.read(html, code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure filing) {
                return JpxAutomaticFinanceTest.filing();
            }

            @Override public JpxShareRights.Adjustment adjustment(String code, JpxIssuerArchive.Disclosure disclosure) {
                return rights.adjustment(code, disclosure, JpxCorporateActionDate.recordDay(text, disclosure,
                        JpxCorporateActionDate.effective(text, disclosure)));
            }
        };
        var prefs = preferences(new HashMap<>());
        var after = report(DAY, "450");
        var batch = JpxAutomaticFinance.refresh(prefs, after, DAY, sources, () -> false);
        var entry = batch.entries().get(CODE);
        assertEquals("", entry.hold());
        var annual = entry.annual();
        assertEquals(1, annual.adjustments().size());
        assertEquals(ValueCandidateScreen.Level.PRIORITY, annual.level(DAY.minusDays(1), new BigDecimal("900")));
        assertEquals(ValueCandidateScreen.Level.PRIORITY, annual.level(DAY, new BigDecimal("450")));
        assertEquals(ValueCandidateScreen.Level.OUTSIDE, annual.level(DAY, new BigDecimal("900")));
        var comparison = new JpxDailyCheck.Comparison(after, report(DAY.minusDays(1), "900"));
        assertEquals(1, comparison.screen(rights, batch).assessed());
        assertTrue(comparison.screen(rights, batch).entered().isEmpty());
        assertEquals(0, comparison.screen(new JpxShareRights(Set.of(), Set.of(), List.of()), batch).assessed());
        var reloaded = JpxAutomaticFinance.refresh(prefs, after, DAY, null, () -> true);
        assertEquals(annual.adjustments(), reloaded.entries().get(CODE).annual().adjustments());
        assertEquals(0, comparison.screen(rights,
                new JpxAutomaticFinance.Batch(Map.of(CODE, new JpxAutomaticFinance.Entry(DAY,
                        new JpxAnnualSummary.Annual(annual.end(), annual.released(), annual.eps(), annual.bps(),
                                annual.source()), "")), Map.of(), 1, 1)).assessed());
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
        return preferences(data, () -> true);
    }

    private static SharedPreferences preferences(Map<String, Object> data, java.util.function.BooleanSupplier commit) {
        return (SharedPreferences) Proxy.newProxyInstance(SharedPreferences.class.getClassLoader(),
                new Class<?>[]{SharedPreferences.class}, (instance, method, args) -> switch (method.getName()) {
                    case "getString", "getLong" -> data.getOrDefault(args[0].toString(), args[1]);
                    case "edit" -> Proxy.newProxyInstance(SharedPreferences.Editor.class.getClassLoader(),
                            new Class<?>[]{SharedPreferences.Editor.class}, (editor, change, values) -> {
                                switch (change.getName()) {
                                    case "putString", "putLong" -> data.put(values[0].toString(), values[1]);
                                    case "remove" -> data.remove(values[0].toString());
                                    case "apply" -> { return null; }
                                    case "commit" -> { return commit.getAsBoolean(); }
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
    @Test public void explorationKeepsTheRequestSetAndProtectsPriorityEntries() {
        var ordinary = java.util.stream.IntStream.range(0, 101).mapToObj(Integer::toString).toList();
        var day = java.time.LocalDate.of(2026, 11, 26);
        var ordered = JpxAutomaticFinance.explorationOrder(ordinary, day, code -> !code.equals("99"));
        org.junit.Assert.assertEquals(ordinary.subList(0, 49), ordered.subList(0, 49));
        org.junit.Assert.assertNotEquals("49", ordered.get(49));
        org.junit.Assert.assertEquals("99", ordered.get(99));
        org.junit.Assert.assertEquals(new java.util.HashSet<>(ordinary), new java.util.HashSet<>(ordered));
        org.junit.Assert.assertEquals(ordered, JpxAutomaticFinance.explorationOrder(ordinary, day, code -> !code.equals("99")));
    }
}
