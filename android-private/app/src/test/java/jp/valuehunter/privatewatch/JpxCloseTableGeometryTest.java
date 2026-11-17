package jp.valuehunter.privatewatch;

import static org.junit.Assert.*;
import java.math.BigDecimal;
import java.util.List;
import java.util.Set;
import org.junit.Test;

public class JpxCloseTableGeometryTest {
    @Test public void corruptWordGeometryDoesNotAbortValidStock() {
        JpxCloseTable table = new JpxCloseTable(Set.of("1301", "7203"));
        double width = 1000;
        table.acceptPage(width, List.of(
                new JpxCloseTable.Word(70, 100, 80, 110, "1301"),
                new JpxCloseTable.Word(400, 100, 410, 110, "100"),
                new JpxCloseTable.Word(600, 100, 610, 110, "101"),
                new JpxCloseTable.Word(Double.NaN, 100, 10, 110, "7203"),
                new JpxCloseTable.Word(70, Double.NaN, 80, 110, "7203"),
                new JpxCloseTable.Word(70, 120, 80, 110, "7203")
        ));
        assertEquals(0, new BigDecimal("101").compareTo(table.prices().get("1301").close()));
        assertFalse(table.prices().containsKey("7203"));
        assertTrue(table.ambiguousCodes().isEmpty());
    }

    @Test public void invalidPageWidthIsRejected() {
        JpxCloseTable table = new JpxCloseTable(Set.of("1301"));
        assertThrows(IllegalArgumentException.class, () -> table.acceptPage(Double.NaN, List.of()));
    }
}
