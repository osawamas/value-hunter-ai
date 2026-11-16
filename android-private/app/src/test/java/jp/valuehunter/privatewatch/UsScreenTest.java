package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;

public class UsScreenTest {
    @Test public void selectsCompletedClosingSessionAndDatedFx() throws JSONException {
        var close = UsScreen.readClose(new JSONObject("{\"Meta Data\":{\"2. Symbol\":\"IBM\"},"
                + "\"Time Series (Daily)\":{\"2026-11-16\":{\"4. close\":\"99\"},"
                + "\"2026-11-13\":{\"4. close\":\"25\"}}}"), LocalDate.parse("2026-11-15"));
        var fx = UsScreen.readFx(new JSONArray("[{\"date\":\"2026-11-16\",\"base\":\"USD\",\"quote\":\"JPY\",\"rate\":200},"
                + "{\"date\":\"2026-11-12\",\"base\":\"USD\",\"quote\":\"JPY\",\"rate\":150}]"), close.date());
        assertEquals(LocalDate.parse("2026-11-13"), close.date());
        assertEquals(LocalDate.parse("2026-11-12"), fx.date());
        var trial = UsScreen.trial(close, fx);
        assertEquals(1, trial.quantity());
        assertEquals(3750, trial.yen(), 0.01);
        assertEquals(25 * 945_120_805.0 / 11_171_000_000L, trial.per(), 0.00001);
        assertTrue(trial.qualifies());
        assertFalse(UsScreen.shouldAlert(false, false, trial.qualifies()));
        assertTrue(UsScreen.shouldAlert(true, false, trial.qualifies()));
        assertFalse(UsScreen.shouldAlert(true, true, trial.qualifies()));
    }

    @Test public void rejectsQuotaResponsesAndPreDisclosureValuation() throws JSONException {
        var filed = LocalDate.parse("2026-10-22");
        assertThrows(JSONException.class,
                () -> UsScreen.readClose(new JSONObject("{\"Information\":\"quota\"}"), filed));
        assertNull(UsScreen.trial(new UsScreen.Close(filed, 25), new UsScreen.Fx(filed, 150)));
        assertNull(UsScreen.trial(new UsScreen.Close(filed.plusYears(1), 25), new UsScreen.Fx(filed, 150)));
    }
}
