package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.util.Map;
import org.json.JSONObject;
import org.json.JSONArray;
import org.junit.Test;

public class CurrentCandidatesTest {
    private static JSONObject data() throws Exception {
        JSONObject quote=new JSONObject().put("trading_date_et","2026-11-23").put("source","testprovider")
                .put("closes",new JSONArray()
                        .put(new JSONObject().put("symbol","ABC").put("close_usd",5))
                        .put(new JSONObject().put("symbol","XYZ").put("close_usd",20)));
        JSONObject screen=new JSONObject().put("fx_date","2026-11-23").put("provider","testprovider")
                .put("observations",new JSONArray()
                    .put(new JSONObject().put("symbol","ABC").put("exchange","NYSE")
                        .put("cik",11).put("status","priority").put("quantity",100))
                    .put(new JSONObject().put("symbol","XYZ").put("exchange","NYSE")
                        .put("cik",12).put("status","reference").put("quantity",1))
                    .put(new JSONObject().put("symbol","SKIP").put("exchange","NYSE")
                        .put("cik",13).put("status","outside_valuation").put("quantity",1)))
                .put("meter_rows",new JSONObject().put(UsReferenceAlerts.meterKey("NYSE",11,"ABC"),
                        new JSONArray().put(90).put(2).put(3).put(100)));
        JSONObject state=new JSONObject().put("ledger",new JSONObject()
                .put("trading_date_et","2026-11-23").put("reference_screen",screen))
                .put("valuation_evidence",new JSONObject().put("fx_rate",150))
                .put("results",new JSONArray()
                    .put(new JSONObject().put("symbol","ABC").put("exchange","NYSE")
                         .put("cik",11).put("shares","100").put("profit","1000").put("equity","2000"))
                    .put(new JSONObject().put("symbol","XYZ").put("exchange","NYSE")
                         .put("cik",12).put("shares","100").put("profit","200").put("equity","400")));
        return new JSONObject().put("quote",quote).put("state",state);
    }
    @Test public void existingLedgerShowsCandidatesWithoutAnyNewNotifications() throws Exception {
        JSONObject d=data();
        var result=CurrentCandidates.parse(d.getJSONObject("quote"),d.getJSONObject("state"),
                Map.of("ABC","ABC INTERNATIONAL"),ValueAlertMeter.DEFAULT);
        assertEquals(2,result.rows().size());
        assertEquals(1,result.priority());assertEquals(1,result.reference());
        assertEquals("ABC INTERNATIONAL",result.rows().get(0).name());
        assertEquals("75000",result.rows().get(0).purchaseYen());
        assertEquals("0.50",result.rows().get(0).per());
        assertEquals("0.25",result.rows().get(0).pbr());
        assertEquals("かなり割安",result.rows().get(0).grade());
        assertEquals("3段階未判定",result.rows().get(1).grade());
    }
    @Test public void mismatchedTradeDateCannotBeShown() throws Exception {
        JSONObject d=data();
        d.getJSONObject("quote").put("trading_date_et","2026-11-24");
        assertThrows(org.json.JSONException.class,()->CurrentCandidates.parse(
                d.getJSONObject("quote"),d.getJSONObject("state"),Map.of(),ValueAlertMeter.DEFAULT));
    }
    @Test public void changedIssuerCIKDoesNotAcquireUnrelatedFinancials() throws Exception {
        JSONObject d=data();
        d.getJSONObject("state").getJSONArray("results").getJSONObject(0).put("cik",999);
        var result=CurrentCandidates.parse(d.getJSONObject("quote"),d.getJSONObject("state"),Map.of(),ValueAlertMeter.DEFAULT);
        assertEquals(1,result.rows().size());
        assertEquals("XYZ",result.rows().get(0).code());
    }
}
