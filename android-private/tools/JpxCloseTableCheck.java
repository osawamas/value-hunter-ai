package jp.valuehunter.privatewatch;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.TreeSet;

/** Runs the production Java row matcher on positioned words supplied by the JPX probe. */
public final class JpxCloseTableCheck {
    public static void main(String[] args) throws Exception {
        checkConflictingRows();
        checkMalformedCellIsolation();
        try (var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            var table = new JpxCloseTable(new HashSet<>(List.of(input.readLine().split("\\t"))));
            Double width = null;
            var words = new ArrayList<JpxCloseTable.Word>();
            for (String line; (line = input.readLine()) != null;) {
                var values = line.split("\\t", 5);
                if (values.length == 1) {
                    if (width != null) table.acceptPage(width, words);
                    width = Double.parseDouble(values[0]);
                    words.clear();
                } else {
                    words.add(new JpxCloseTable.Word(
                            Double.parseDouble(values[0]), Double.parseDouble(values[1]),
                            Double.parseDouble(values[2]), Double.parseDouble(values[3]), values[4]));
                }
            }
            if (width != null) table.acceptPage(width, words);
            var prices = table.prices();
            for (String code : new TreeSet<>(prices.keySet())) {
                var row = prices.get(code);
                print(code, row.morning(), row.afternoon());
            }
            for (String code : new TreeSet<>(table.ambiguousCodes())) {
                System.out.println(code + "\tconflict");
            }
        }
    }

    private static void print(String code, java.math.BigDecimal morning, java.math.BigDecimal afternoon) {
        System.out.println(code + "\t" + (morning == null ? "" : morning.toPlainString())
                + "\t" + (afternoon == null ? "" : afternoon.toPlainString()));
    }

    private static void checkMalformedCellIsolation() {
        var table = new JpxCloseTable(java.util.Set.of("1301", "1302"));
        var badCode = new JpxCloseTable.Word(65, 10, 75, 12, "1301");
        var duplicate1 = new JpxCloseTable.Word(400, 10, 410, 12, "100");
        var duplicate2 = new JpxCloseTable.Word(410, 10, 420, 12, "101");
        var goodCode = new JpxCloseTable.Word(65, 30, 75, 32, "1302");
        var goodPrice = new JpxCloseTable.Word(400, 30, 415, 32, "200");
        table.acceptPage(1000, List.of(badCode, duplicate1));
        table.acceptPage(1000, List.of(badCode, duplicate1, duplicate2, goodCode, goodPrice));
        var goodRow = table.prices().get("1302");
        if (!table.ambiguousCodes().equals(java.util.Set.of("1301"))
                || table.prices().containsKey("1301")
                || goodRow == null || goodRow.close() == null
                || new java.math.BigDecimal("200").compareTo(goodRow.close()) != 0) {
            throw new AssertionError("Malformed JPX quote must be excluded without losing valid symbols");
        }
        table.acceptPage(1000, List.of(badCode, duplicate1));
        if (table.prices().containsKey("1301")) {
            throw new AssertionError("Later clean-looking rows must not clear a quote conflict");
        }
    }

    private static void checkConflictingRows() {
        var table = new JpxCloseTable(java.util.Set.of("1301"));
        var code = new JpxCloseTable.Word(65, 10, 75, 12, "1301");
        var morning = new JpxCloseTable.Word(400, 10, 415, 12, "1,000.5");
        var afternoon = new JpxCloseTable.Word(600, 10, 615, 12, "1,200");
        table.acceptPage(1000, List.of(code, morning));
        if (!new java.math.BigDecimal("1000.5").equals(table.prices().get("1301").close())) {
            throw new AssertionError("JPX morning-only close should be used");
        }
        table.acceptPage(1000, List.of(code, morning, afternoon));
        table.acceptPage(1000, List.of(code, morning));
        if (!table.prices().isEmpty() || !table.ambiguousCodes().equals(java.util.Set.of("1301"))) {
            throw new AssertionError("Conflicting JPX close should stay excluded");
        }
    }
}
