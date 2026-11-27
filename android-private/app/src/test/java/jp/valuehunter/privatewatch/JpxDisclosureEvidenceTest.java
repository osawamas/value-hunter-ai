package jp.valuehunter.privatewatch;
import org.junit.Test;
import java.time.LocalDate;
import java.net.URI;
import java.util.List;
import static org.junit.Assert.*;
public class JpxDisclosureEvidenceTest {
    @Test public void issuerDateDuplicateAndRiskChecks() throws Exception {
        var day = LocalDate.parse("2026-11-26");
        var buy = new JpxIssuerArchive.Disclosure(day.minusDays(1),"自己株式取得に係る事項の決定",null,URI.create("https://www2.jpx.co.jp/disc/12340/123.pdf"),false);
        var wrong = new JpxIssuerArchive.Disclosure(day.minusDays(1),"大型受注",null,URI.create("https://www2.jpx.co.jp/disc/99990/456.pdf"),false);
        var future = new JpxIssuerArchive.Disclosure(day.plusDays(1),"特許取得",null,buy.pdfLink(),false);
        var events = JpxDisclosureEvidence.extract("1234",day,new JpxIssuerArchive.Page(List.of(buy,buy,wrong,future)));
        assertEquals(1,events.size());
        assertEquals(events,JpxDisclosureEvidence.decode("1234",JpxDisclosureEvidence.encode(events),day));
        var score = new ValueAlertMeter.Score(59,1,3);
        assertEquals(62,JpxDisclosureEvidence.adjust(score,events,day).points());
        assertEquals(59,JpxDisclosureEvidence.adjust(score,events,day.minusDays(1)).points());
        assertEquals(1,JpxDisclosureEvidence.adjust(score,events,day).ceiling());
        var risk = new JpxDisclosureEvidence.Event(day.minusDays(1),"下方修正",buy.pdfLink().toString(),"risk");
        assertEquals(49,JpxDisclosureEvidence.adjust(score,List.of(events.get(0),risk),day).points());
        assertFalse(JpxDisclosureEvidence.relevant("自己株式の取得状況"));
        assertFalse(JpxDisclosureEvidence.relevant("自己株式取得の中止"));
    }
    @Test public void verifiedDistressSuppressesEvenStrongFinancialEvidence() {
        var date = LocalDate.of(2026, 11, 26);
        var notice = new JpxIssuerArchive.Disclosure(date.minusDays(1), "民事再生手続開始の申立に関するお知らせ",
                null, URI.create("https://www2.jpx.co.jp/disc/12340/123.pdf"), false);
        var events = JpxDisclosureEvidence.extract("1234", date, new JpxIssuerArchive.Page(List.of(notice)));
        assertEquals(1, events.size());
        var score = new ValueAlertMeter.Score(100, 3, 4);
        assertEquals(0, JpxDisclosureEvidence.adjust(score, events, date).level(ValueAlertMeter.DEFAULT));
        assertEquals(3, JpxDisclosureEvidence.adjust(score, events, date.minusDays(1)).level(ValueAlertMeter.DEFAULT));
    }
}
