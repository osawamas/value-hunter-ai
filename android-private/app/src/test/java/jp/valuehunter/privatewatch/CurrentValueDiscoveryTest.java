package jp.valuehunter.privatewatch;
import org.junit.Test;
import static org.junit.Assert.*;
public class CurrentValueDiscoveryTest {
 @Test public void firstAndRecoveredEvidenceCanNotifyAllThreeLevels() {
   var t=ValueAlertMeter.DEFAULT;
   for(int level=1;level<=3;level++){
     int points=level==1?60:level==2?75:85;
     var current=new ValueAlertPreview.Row(new ValueAlertMeter.Score(points,3,4),100);
     assertEquals(level,ValueAlertPreview.discoveryLevel(null,current,t));
     assertEquals(0,ValueAlertPreview.discoveryLevel(current,current,t));
   }
 }
 @Test public void noBudgetOrEvidenceNeverNotifies() {
   assertEquals(0,ValueAlertPreview.discoveryLevel(null,new ValueAlertPreview.Row(new ValueAlertMeter.Score(99,3,4),0),ValueAlertMeter.DEFAULT));
   assertEquals(0,ValueAlertPreview.discoveryLevel(null,new ValueAlertPreview.Row(new ValueAlertMeter.Score(99,3,0),100),ValueAlertMeter.DEFAULT));
 }
}
