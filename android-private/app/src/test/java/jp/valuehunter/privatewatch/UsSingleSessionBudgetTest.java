package jp.valuehunter.privatewatch;

import static org.junit.Assert.assertEquals;

import org.json.JSONObject;
import org.junit.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;

public final class UsSingleSessionBudgetTest {
    private static final LocalDate DAY = LocalDate.of(2026, 11, 17);

    @Test public void exactThresholdIncludesOneHundredShares() {
        var fx = new UsScreen.Fx(DAY, 125);
        assertEquals(UsSingleSessionBudget.Verdict.WITHIN, UsSingleSessionBudget.check(DAY, fx, new BigDecimal("8")));
        assertEquals(UsSingleSessionBudget.Verdict.OUTSIDE, UsSingleSessionBudget.check(DAY, fx, new BigDecimal("8.01")));
        assertEquals(UsSingleSessionBudget.Verdict.HELD,
                UsSingleSessionBudget.check(DAY, new UsScreen.Fx(DAY.minusDays(1), 125), BigDecimal.ONE));
        assertEquals(UsSingleSessionBudget.Verdict.HELD, UsSingleSessionBudget.check(DAY, fx, null));
    }

    @Test public void targetsRequireExactCurrentListingsAndAvoidDuplicatingPairedRecovery() throws Exception {
        var snapshot = new JSONObject().put("day", DAY.toString()).put("time", "16:08")
                .put("nyse", new JSONObject(Map.of("KEEP", "Keep Corp", "MOVE", "Move Corp", "PAIR", "Pair Corp")))
                .put("nasdaq", new JSONObject(Map.of("MOVE", "Move Corp", "NQ", "Nq Corp")));
        var pending = Set.of("KEEP", "MOVE", "PAIR", "GONE");
        assertEquals(Set.of("KEEP"), UsSingleSessionBudget.targets(pending,
                UsMarketCoverage.sessionExchanges(snapshot, DAY), Set.of("PAIR")));
        assertEquals(Set.of(), UsMarketCoverage.sessionExchanges(snapshot, DAY.plusDays(1)).keySet());
    }
}
