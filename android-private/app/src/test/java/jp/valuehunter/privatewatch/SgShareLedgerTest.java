package jp.valuehunter.privatewatch;

import java.time.LocalDate;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertNull;

public class SgShareLedgerTest {
    private static final LocalDate DATE = LocalDate.of(2026, 11, 16);

    @Test public void usesOnlyTheExactVerifiedDisclosureDate() throws JSONException {
        var row = new JSONObject().put("date", DATE.toString())
                .put("disclosed_at", "2026-11-16T18:21:27+08:00").put("shares", 3_115_347_115L)
                .put("source", "https://links.sgx.com/1.0.0/corporate-announcements/EE91Z8VP8VZN8PJN/"
                        + "e88920826649e589c68fba0c48aae0681ae2fdb10acb81ab3f82c2bd58a0e36b");
        var rows = new JSONArray().put(row);
        var payload = new JSONObject().put("schema", 1).put("symbol", "S63").put("records", rows);
        var disclosure = SgShareLedger.read(payload, DATE);
        assertEquals(3_115_347_115L, disclosure.shares());
        assertEquals(row.getString("source"), disclosure.source());
        assertEquals("2026-11-16T18:21:27+08:00", disclosure.disclosedAt().toString());
        assertNull(SgShareLedger.read(payload, DATE.plusDays(1)));
        rows.put(row);
        assertThrows(JSONException.class, () -> SgShareLedger.read(payload, DATE));
        rows.remove(1);
        row.put("disclosed_at", "2026-11-17T18:21:27+08:00");
        assertThrows(JSONException.class, () -> SgShareLedger.read(payload, DATE));
    }
}
