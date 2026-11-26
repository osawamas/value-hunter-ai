package jp.valuehunter.privatewatch;
import org.junit.Test;
import org.json.*;
import static org.junit.Assert.*;
public class UsRepairReasonTest {
 @Test public void onlyTransientOrUnclassifiedHoldsRepeatToday() throws Exception {
    var targets=new JSONArray();
    var holds=new JSONObject();
    for(String symbol:new String[]{"MISSING","STALE","BAD","UNKNOWN","NEW","ABSENT"})
      targets.put(new JSONObject().put("symbol",symbol));
    holds.put("MISSING","parent_equity_missing").put("STALE","parent_equity_stale")
      .put("BAD","invalid_sec_payload").put("UNKNOWN","unknown").put("ABSENT","sec_not_found");
    var scan=new JSONObject().put("targets",targets).put("results",new JSONArray()).put("fetch_holds",holds);
    var retry=UsSecFinanceWorker.repairTargets(scan);
    assertEquals(3,retry.length());
    assertEquals("BAD",retry.getJSONObject(0).getString("symbol"));
    assertEquals("UNKNOWN",retry.getJSONObject(1).getString("symbol"));
    assertEquals("NEW",retry.getJSONObject(2).getString("symbol"));
 }
}
