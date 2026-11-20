package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.io.IOException;
import java.time.LocalDate;
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
        assertEquals(stocks.codes(), stocks.forTradingDay(event.minusDays(1), verified).codes());
        assertEquals(Set.of("1301", "6198"), stocks.forTradingDay(event, verified).codes());
        assertThrows(IOException.class, () -> JpxStockUniverse.readDelistings(source.replace("2026/11/11", "2026/02/30")));
        assertThrows(IOException.class, () -> JpxStockUniverse.readDelistings(source.replace("<td>7523</td>", "<td>?</td>")));
    }
}
