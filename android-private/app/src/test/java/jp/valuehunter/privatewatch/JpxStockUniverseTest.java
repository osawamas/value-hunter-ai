package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.io.IOException;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

public class JpxStockUniverseTest {
    @Test public void appliesOfficialDelistingOnlyOnAndAfterTheEffectiveDay() throws Exception {
        var asOf = LocalDate.of(2026, 10, 31);
        var event = LocalDate.of(2026, 11, 11);
        var stocks = new JpxStockUniverse(asOf, Set.of("7523", "1301", "6198"));
        var source = """
                <table><thead><tr><th>上場廃止日</th><th>銘柄名</th><th>コード</th>
                <th>市場区分</th><th>上場廃止理由</th></tr></thead><tbody>
                <tr><td>2026/11/11</td><td>アールビバン（株）</td><td>7523</td><td>スタンダード</td><td>ＭＢＯ</td></tr>
                <tr><td>2026/10/01</td><td>旧銘柄</td><td>1301</td><td>スタンダード</td><td>合併</td></tr>
                </tbody></table>
                """;
        var verified = JpxStockUniverse.readDelistings(source);
        assertEquals(stocks.codes(), stocks.forTradingDay(event.minusDays(1), Map.of(), verified).codes());
        assertEquals(Set.of("1301", "6198"), stocks.forTradingDay(event, Map.of(), verified).codes());
        assertThrows(IOException.class, () -> JpxStockUniverse.readDelistings(source.replace("2026/11/11", "2026/02/30")));
        assertThrows(IOException.class, () -> JpxStockUniverse.readDelistings(source.replace("<td>7523</td>", "<td>?</td>")));
    }

    @Test public void usesTheOfficialFirstSessionAndIgnoresUnconfirmedDateRanges() throws Exception {
        var table = """
                <table><thead><tr><th>上場日<br />（上場承認日）</th><th>コード</th></tr></thead><tbody>
                <tr><td>2026/11/10<br />（2026/10/06）</td><td>会社</td><td><a>660A</a></td>
                <td></td><td></td><td></td><td></td><td></td></tr>
                <tr><td>グロース</td><td></td><td></td><td></td><td></td><td></td></tr>
                <tr><td>2026/11/20～2026/11/26<br />（2026/10/22）</td><td>会社</td><td>661A</td>
                <td></td><td></td><td></td><td></td><td></td></tr>
                <tr><td>プライム</td><td></td><td></td><td></td><td></td><td></td></tr>
                </tbody></table>
                """;
        var listings = JpxStockUniverse.readListings(table);
        var day = LocalDate.of(2026, 11, 10);
        var base = new JpxStockUniverse(day.minusDays(10), Set.of("7523"));
        assertEquals(Map.of("660A", day), listings);
        assertEquals(Set.of("7523"), base.forTradingDay(day.minusDays(1), listings, Map.of()).codes());
        assertEquals(Set.of("660A"), base.forTradingDay(day, listings, Map.of("7523", day)).codes());
    }
}
