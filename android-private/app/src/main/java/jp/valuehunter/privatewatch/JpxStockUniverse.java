package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/** The reference list of domestic ordinary shares on Prime, Standard, and Growth. */
record JpxStockUniverse(LocalDate asOf, Set<String> codes) {
    private static final Pattern CODE = Pattern.compile("[0-9][0-9A-Z]{3}");
    private static final URI DELISTINGS = URI.create("https://www.jpx.co.jp/listing/stocks/delisted/");
    private static final Pattern TABLE = Pattern.compile("<table\\b[^>]*>(.*?)</table>", Pattern.DOTALL);
    private static final Pattern BODY = Pattern.compile("<tbody\\b[^>]*>(.*?)</tbody>", Pattern.DOTALL);
    private static final Pattern ROW = Pattern.compile("<tr\\b[^>]*>(.*?)</tr>", Pattern.DOTALL);
    private static final Pattern CELL = Pattern.compile("<td\\b[^>]*>(.*?)</td>", Pattern.DOTALL);
    private static final Pattern DATE = Pattern.compile("[0-9]{4}/[0-9]{2}/[0-9]{2}");

    static Map<String, LocalDate> delistings() {
        try {
            return readDelistings(JpxIssuerArchive.publicPage(DELISTINGS));
        } catch (IOException | IllegalArgumentException unavailable) {
            return Map.of();
        }
    }

    static Map<String, LocalDate> readDelistings(String page) throws IOException {
        var tables = TABLE.matcher(page);
        Map<String, LocalDate> events = null;
        while (tables.find()) {
            String table = tables.group(1);
            if (!table.contains(">上場廃止日</th>") || !table.contains(">コード</th>")
                    || !table.contains(">上場廃止理由</th>")) continue;
            if (events != null) throw new IOException("Duplicate JPX delisting tables");
            var body = BODY.matcher(table);
            if (!body.find()) throw new IOException("Missing JPX delisting rows");
            events = new HashMap<>();
            var rows = ROW.matcher(body.group(1));
            while (rows.find()) {
                var fields = CELL.matcher(rows.group(1)).results()
                        .map(cell -> JpxIssuerArchive.visibleText(cell.group(1))).toList();
                if (fields.size() != 5 || !DATE.matcher(fields.get(0)).matches()
                        || !CODE.matcher(fields.get(2)).matches()) throw new IOException("Invalid JPX delisting row");
                try {
                    var day = LocalDate.parse(fields.get(0).replace('/', '-'));
                    var other = events.putIfAbsent(fields.get(2), day);
                    if (other != null && !other.equals(day)) throw new IOException("Conflicting JPX delisting dates");
                } catch (DateTimeParseException invalid) {
                    throw new IOException("Invalid JPX delisting date", invalid);
                }
            }
        }
        if (events == null || events.isEmpty()) throw new IOException("Missing JPX delistings");
        return Map.copyOf(events);
    }

    JpxStockUniverse forTradingDay(LocalDate day, Map<String, LocalDate> delistings) {
        var effective = new HashSet<>(codes);
        delistings.forEach((code, date) -> {
            if (date.isAfter(asOf) && !date.isAfter(day)) effective.remove(code);
        });
        return effective.size() == codes.size() ? this : new JpxStockUniverse(asOf, Set.copyOf(effective));
    }

    static JpxStockUniverse load(Context context) throws IOException {
        try (var stream = context.getAssets().open("jpx-stock-universe.txt");
             var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.US_ASCII))) {
            String date = reader.readLine();
            if (date == null) throw new IOException("東証の銘柄一覧に基準日がない");
            LocalDate asOf;
            try {
                asOf = LocalDate.parse(date);
            } catch (DateTimeParseException error) {
                throw new IOException("東証の銘柄一覧の基準日を読み取れなかった", error);
            }
            var codes = new HashSet<String>();
            for (String line; (line = reader.readLine()) != null;) {
                if (!CODE.matcher(line).matches() || !codes.add(line)) {
                    throw new IOException("東証の銘柄一覧に不正または重複コードがある");
                }
            }
            if (codes.isEmpty()) throw new IOException("東証の銘柄一覧が空");
            return new JpxStockUniverse(asOf, Set.copyOf(codes));
        }
    }
}
