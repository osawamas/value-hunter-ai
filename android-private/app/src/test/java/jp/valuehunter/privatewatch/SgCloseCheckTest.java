package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.time.Instant;
import java.time.LocalDate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

public class SgCloseCheckTest {
    private static final LocalDate CUTOFF = LocalDate.parse("2026-11-15");

    @Test public void readsLastTwoCompletedSingaporeSessionsFromRawBars() throws JSONException {
        var pair = SgCloseCheck.read(payload(
                bar("2026-11-15T16:00:00Z", 8.3), bar("2026-11-12T16:00:00Z", 8.2),
                bar("2026-11-11T16:00:00Z", 8.1)), CUTOFF);
        assertEquals(LocalDate.parse("2026-11-12"), pair.previous().session());
        assertEquals(LocalDate.parse("2026-11-13"), pair.latest().session());
        assertEquals(8.2, pair.latest().sgd(), 0);
    }

    @Test public void rejectsWrongBasisDuplicateDatesAndMissingSessions() throws JSONException {
        var latest = bar("2026-11-12T16:00:00Z", 8.2);
        var earlier = bar("2026-11-11T16:00:00Z", 8.1);
        assertThrows(JSONException.class, () -> SgCloseCheck.read(payload(latest), CUTOFF));
        assertThrows(JSONException.class, () -> SgCloseCheck.read(payload(latest, latest), CUTOFF));
        earlier.put("adjustment", "all");
        assertThrows(JSONException.class, () -> SgCloseCheck.read(payload(latest, earlier), CUTOFF));
        earlier.put("adjustment", "raw");
        var wrongCurrency = payload(latest, earlier);
        wrongCurrency.getJSONObject("meta").put("currency", "USD");
        assertThrows(JSONException.class, () -> SgCloseCheck.read(wrongCurrency, CUTOFF));
        assertThrows(JSONException.class, () -> SgCloseCheck.read(payload(latest, earlier), CUTOFF.plusWeeks(2)));
    }

    private static JSONObject payload(JSONObject... rows) throws JSONException {
        var data = new JSONArray();
        for (JSONObject row : rows) data.put(row);
        return new JSONObject().put("data", data).put("meta", new JSONObject()
                .put("sid", "sgx:S63").put("currency", "SGD").put("timezone", "Asia/Singapore"));
    }

    private static JSONObject bar(String time, double price) throws JSONException {
        return new JSONObject().put("sid", "sgx:S63").put("timeframe", "1Day")
                .put("ts_ms", Long.toString(Instant.parse(time).toEpochMilli()))
                .put("close", price).put("adjustment", "raw");
    }
}
