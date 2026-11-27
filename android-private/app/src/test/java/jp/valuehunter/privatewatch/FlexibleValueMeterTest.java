package jp.valuehunter.privatewatch;
import java.math.BigDecimal;
import java.util.List;
import org.junit.Test;
import static org.junit.Assert.*;
public class FlexibleValueMeterTest {
 private static BigDecimal n(String s){return new BigDecimal(s);}
 @Test public void missingEquityAndShareCountCanStillReachAllLevels(){
  var e=List.of(n("2"),n("1.9"),n("1.8"));
  assertEquals(1,FlexibleValueMeter.assess(n("10"),e,null,null).level(ValueAlertMeter.DEFAULT));
  assertEquals(2,FlexibleValueMeter.assess(n("10"),e,100,null).level(ValueAlertMeter.DEFAULT));
  assertEquals(3,FlexibleValueMeter.assess(n("10"),e,100,100).level(ValueAlertMeter.DEFAULT));
  assertEquals(0,FlexibleValueMeter.assess(n("10"),e,0,100).level(ValueAlertMeter.DEFAULT));
  assertEquals(0,FlexibleValueMeter.assess(n("10"),List.of(n("2")),null,null).level(ValueAlertMeter.DEFAULT));
 }
 @Test public void exceptionalTierRequiresContinuityAcrossBothYearPairs() {
  var oldDrop = List.of(n("2"), n("1.9"), n("4.0"));
  assertEquals(2, FlexibleValueMeter.assess(n("10"), oldDrop, 100, 100).level(ValueAlertMeter.DEFAULT));
 }
}
