package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

public class UsPriceOnlyBudgetTest {
    private static final LocalDate FRIDAY = LocalDate.of(2026, 11, 13);
    private static final LocalDate MONDAY = FRIDAY.plusDays(3);
    private static final String VERIFIED = UsDailyCloses.MASSIVE_SOURCE;
    private static final Set<String> LISTED = Set.of("ABC", "FIN", "UNCHANGED");

    @Test public void usesEachDaysExchangeRateAndExcludesFinanciallyScreenedStocks() throws Exception {
        var result = UsPriceOnlyBudget.compare(closes(FRIDAY, VERIFIED), closes(MONDAY, VERIFIED), rates(),
                LISTED, finance(VERIFIED), MONDAY);
        assertTrue(result.verifiedPriceBasis());
        assertEquals(2, result.screen().assessed());
        assertEquals(List.of("ABC"), result.screen().entered().stream().map(PriceOnlyScreen.BudgetEntry::code).toList());
        assertEquals(0, new BigDecimal("98000").compareTo(result.screen().entered().get(0).yen()));
    }

    @Test public void unverifiedDailyFeedProvidesAComparisonButIsIneligibleForAlerts() throws Exception {
        var provider = UsDoltCloses.SOURCE;
        var result = UsPriceOnlyBudget.compare(closes(FRIDAY, provider), closes(MONDAY, provider), rates(),
                LISTED, finance(provider), MONDAY);
        assertEquals(1, result.screen().entered().size());
        assertFalse(result.verifiedPriceBasis());
    }

    @Test public void rejectsMixedSourcesMissingSessionsStaleCacheAndPriorDayFx() throws Exception {
        var latest = closes(MONDAY, VERIFIED);
        var validPrevious = closes(FRIDAY, VERIFIED);
        var financial = finance(VERIFIED);
        assertEquals(0, UsPriceOnlyBudget.compare(closes(FRIDAY, UsDoltCloses.SOURCE), latest, rates(),
                LISTED, financial, MONDAY).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(closes(FRIDAY.minusDays(1), VERIFIED), latest, rates(),
                LISTED, financial, MONDAY).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(validPrevious, latest, rates(),
                LISTED, financial, MONDAY.plusDays(1)).screen().assessed());
        assertEquals(0, UsPriceOnlyBudget.compare(validPrevious, latest,
                new JSONArray().put(rate(FRIDAY, 150)), LISTED, financial, MONDAY).screen().assessed());
    }

    @Test public void rejectsAdjustedOrUnspecifiedPriceBasisForNotification() throws Exception {
        var prior = closes(FRIDAY, VERIFIED);
        var latest = closes(MONDAY, VERIFIED);
        assertTrue(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());

        prior.put("adjusted", true);
        assertFalse(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());

        prior.put("adjusted", false);
        latest.remove("adjusted");
        assertFalse(UsPriceOnlyBudget.compare(prior, latest, rates(), LISTED,
                finance(VERIFIED), MONDAY).verifiedPriceBasis());
    }

    private static JSONObject closes(LocalDate day, String provider) throws Exception {
        return new JSONObject().put("trading_date_et", day.toString()).put("source", provider)
                .put("adjusted", VERIFIED.equals(provider) ? Boolean.FALSE : JSONObject.NULL)
                .put("closes", new JSONArray().put(row("ABC", 7)).put(row("FIN", 7))
                        .put(row("UNCHANGED", 5)).put(row("NOT_LISTED", 7)));
    }

    private static JSONObject row(String symbol, int price) throws Exception {
        return new JSONObject().put("symbol", symbol).put("close_usd", price);
    }

    private static JSONArray rates() throws Exception {
        return new JSONArray().put(rate(FRIDAY, 150)).put(rate(MONDAY, 140));
    }

    private static JSONObject rate(LocalDate date, int rate) throws Exception {
        return new JSONObject().put("date", date.toString()).put("base", "USD").put("quote", "JPY").put("rate", rate);
    }

    private static UsReferenceAlerts.Screen finance(String provider) {
        return new UsReferenceAlerts.Screen(MONDAY, provider, "a".repeat(64),
                Map.of("FIN", new UsReferenceAlerts.Observation(1, "NYSE", "outside_valuation", 1)));
    }
}
