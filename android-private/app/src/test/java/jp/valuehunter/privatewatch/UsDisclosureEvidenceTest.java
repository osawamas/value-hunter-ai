package jp.valuehunter.privatewatch;
import org.json.*;
import org.junit.Test;
import java.time.LocalDate;
import static org.junit.Assert.*;
public class UsDisclosureEvidenceTest {
 @Test public void asOfIdentityAndNoContractBonus() throws Exception {
   var day=LocalDate.parse("2026-11-26");
   var recent=new JSONObject().put("form",new JSONArray().put("8-K").put("8-K").put("8-K"))
    .put("filingDate",new JSONArray().put("2026-11-25").put("2026-11-25").put("2026-11-26"))
    .put("items",new JSONArray().put("1.01").put("2.06,4.02").put("1.03"))
    .put("accessionNumber",new JSONArray().put("0000001234-26-000001").put("0000001234-26-000002").put("0000001234-26-000003"));
   var payload=new JSONObject().put("cik","1234").put("filings",new JSONObject().put("recent",recent));
   var events=UsDisclosureEvidence.read(payload,1234,day);
   assertEquals(1,events.length());
   assertEquals(0,UsDisclosureEvidence.read(payload,999,day).length());
   var row=new JSONObject().put("cik",1234).put("disclosure_events",events);
   var score=new ValueAlertMeter.Score(85,3,4);
   assertEquals(75,UsDisclosureEvidence.adjust(score,row,day).points());
   assertEquals(85,UsDisclosureEvidence.adjust(score,row,day.minusDays(1)).points());
 }
}
