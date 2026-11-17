package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Pattern;

/** Extracts TSE domestic ordinary-stock closes from positioned JPX table words. */
final class JpxCloseTable {
    private static final Pattern PRICE = Pattern.compile("[0-9][0-9,]*(?:\\.[0-9]+)?");
    private static final double ROW_TOLERANCE = 2.5;

    record Word(double x0, double y0, double x1, double y1, String text) {
        double centerX(double width) { return (x0 + x1) / (2 * width); }
        double centerY() { return (y0 + y1) / 2; }
    }

    record Sessions(BigDecimal morning, BigDecimal afternoon) {
        BigDecimal close() { return afternoon != null ? afternoon : morning; }
    }

    private final Set<String> stocks;
    private final Map<String, Sessions> prices = new HashMap<>();
    private final Set<String> ambiguous = new HashSet<>();

    JpxCloseTable(Set<String> stocks) {
        this.stocks = new HashSet<>(stocks);
    }

    void acceptPage(double width, List<Word> words) {
        if (!Double.isFinite(width) || width <= 0) {
            throw new IllegalArgumentException("Invalid JPX page width");
        }
        NavigableMap<Double, List<Word>> wordsByY = new TreeMap<>();
        for (Word word : words) {
            wordsByY.computeIfAbsent(word.centerY(), ignored -> new ArrayList<>()).add(word);
        }
        for (Word word : words) {
            String code = word.text();
            double x = word.centerX(width);
            if (x <= .057 || x >= .094 || !stocks.contains(code) || ambiguous.contains(code)) {
                continue;
            }
            double y = word.centerY();
            var row = wordsByY.subMap(y - ROW_TOLERANCE, false, y + ROW_TOLERANCE, false);
            Sessions sessions = new Sessions(
                    bandPrice(row.values(), .389, .439, width),
                    bandPrice(row.values(), .591, .641, width));
            Sessions previous = prices.putIfAbsent(code, sessions);
            if (previous != null && !previous.equals(sessions)) {
                ambiguous.add(code);
                prices.remove(code);
            }
        }
    }

    Map<String, Sessions> prices() {
        return new HashMap<>(prices);
    }

    Set<String> ambiguousCodes() {
        return new HashSet<>(ambiguous);
    }

    private static BigDecimal bandPrice(Iterable<List<Word>> row, double left, double right, double width) {
        BigDecimal found = null;
        for (List<Word> group : row) {
            for (Word word : group) {
                double x = word.centerX(width);
                if (x > left && x < right && PRICE.matcher(word.text()).matches()) {
                    if (found != null) {
                        throw new IllegalArgumentException("Ambiguous JPX closing price column");
                    }
                    found = new BigDecimal(word.text().replace(",", "")).stripTrailingZeros();
                }
            }
        }
        return found;
    }
}
