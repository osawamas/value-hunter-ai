package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import org.json.JSONArray;
import org.json.JSONException;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

public class SgValuationTest {
    @Test public void computesUsingTheSameDatesSharesAndTrailingProfit() {
        var date = LocalDate.of(2026, 11, 16);
        var trial = SgValuation.forClose(new SgCloseCheck.Close(date, 9.25), 3_115_347_115L);
        double cap = 3_115_347_115L * 9.25;
        assertEquals(3_115_347_115L, trial.shares());
        assertEquals(cap, trial.cap(), 0.001);
        assertEquals(cap / 572_067_000L, trial.per(), 0.0001);
        assertEquals(cap / 2_524_548_000L, trial.pbr(), 0.0001);
    }

    @Test public void selectsRecentSgdRateWithoutUsingFutureOrUsdRates() throws JSONException {
        var payload = new JSONArray("""
                [
                  {"base":"SGD","quote":"JPY","date":"2026-11-13","rate":120},
                  {"base":"USD","quote":"JPY","date":"2026-11-16","rate":155},
                  {"base":"SGD","quote":"JPY","date":"2026-11-17","rate":133}
                ]
                """);
        var fx = UsScreen.readFx(payload, LocalDate.of(2026, 11, 16), "SGD");
        assertEquals(LocalDate.of(2026, 11, 13), fx.date());
        assertEquals(120, fx.yenPerDollar(), 0);
    }
}
