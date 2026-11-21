package jp.valuehunter.privatewatch;

import org.json.JSONObject;
import org.junit.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class UsDatedListingsTest {
    private static final LocalDate BEFORE = LocalDate.of(2026, 11, 16);
    private static final LocalDate DAY = BEFORE.plusDays(1);

    @Test public void onlySameOrdinaryIssueOnSameExchangeCanReceiveASupplement() throws Exception {
        var before = snapshot(BEFORE, Map.of("MOVE", "ABC CLASS A COMMON STOCK",
                "GOOD", "ABC CLASS A COMMON STOCK", "TRADE", "ABC CLASS A COMMON STOCK",
                "COLLIDE", "ABC COMMON STOCK"), Map.of("COLLIDE", "ABC COMMON STOCK"));
        var after = snapshot(DAY,
                Map.of("GOOD", "ABC CLASS A COMMON STOCK", "TRADE", "OTHER CLASS B COMMON STOCK",
                        "NEW", "ABC CLASS A COMMON STOCK", "COLLIDE", "ABC COMMON STOCK"),
                Map.of("MOVE", "ABC CLASS A COMMON STOCK"));

        assertEquals(Set.of("GOOD"), UsMarketCoverage.verifiedSupplementSymbols(before, after, BEFORE, DAY));
        assertTrue(UsMarketCoverage.verifiedSupplementSymbols(before, after, BEFORE, DAY.plusDays(1)).isEmpty());
        assertTrue(UsMarketCoverage.verifiedSupplementSymbols(new JSONObject(), after, BEFORE, DAY).isEmpty());
        after.put("time", "20:44");
        assertEquals(Set.of("GOOD"), UsMarketCoverage.verifiedSupplementSymbols(before, after, BEFORE, DAY));
        after.put("time", "20:45");
        assertTrue(UsMarketCoverage.verifiedSupplementSymbols(before, after, BEFORE, DAY).isEmpty());
    }

    @Test public void unpricedSymbolsShowTheOutstandingIdentityCheck() {
        var result = MarketCoverage.build(DAY, DAY, Set.of("HOLD", "PRICE"), Set.of(), Set.of(),
                Map.of("HOLD", MarketCoverage.Reason.DATED_LISTING));
        assertEquals(Map.of(MarketCoverage.Reason.DATED_LISTING, List.of("HOLD"),
                MarketCoverage.Reason.CLOSE, List.of("PRICE")), result.unassessed());
    }

    private static JSONObject snapshot(LocalDate day, Map<String, String> nyse, Map<String, String> nasdaq)
            throws Exception {
        return new JSONObject().put("day", day.toString()).put("time", "15:00")
                .put("nyse", new JSONObject(nyse)).put("nasdaq", new JSONObject(nasdaq));
    }
}
