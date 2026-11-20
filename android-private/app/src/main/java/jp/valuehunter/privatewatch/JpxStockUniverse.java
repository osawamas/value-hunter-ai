package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/** The reference list of domestic ordinary shares on Prime, Standard, and Growth. */
record JpxStockUniverse(LocalDate asOf, Set<String> codes) {
    private static final Pattern CODE = Pattern.compile("[0-9][0-9A-Z]{3}");
    private static final URI DELISTINGS = URI.create("https://www.jpx.co.jp/listing/stocks/delisted/");
    private static final URI LISTINGS = URI.create("https://www.jpx.co.jp/listing/stocks/new/");
    private static final Pattern TABLE = Pattern.compile("<table\\b[^>]*>(.*?)</table>", Pattern.DOTALL);
    private static final Pattern BODY = Pattern.compile("<tbody\\b[^>]*>(.*?)</tbody>", Pattern.DOTALL);
    private static final Pattern ROW = Pattern.compile("<tr\\b[^>]*>(.*?)</tr>", Pattern.DOTALL);
    private static final Pattern CELL = Pattern.compile("<td\\b[^>]*>(.*?)</td>", Pattern.DOTALL);
    private static final Pattern DATE = Pattern.compile("[0-9]{4}/[0-9]{2}/[0-9]{2}");
    private static final Pattern LISTING_DATE = Pattern.compile("^\\s*([0-9]{4}/[0-9]{2}/[0-9]{2})\\s*<br\\s*/?>\\s*（");
    private static final Set<String> DOMESTIC_MARKETS = Set.of("プライム", "スタンダード", "グロース");

    static Map<String, LocalDate> listings() {
        try {
            return readListings(JpxIssuerArchive.publicPage(LISTINGS));
        } catch (IOException | IllegalArgumentException unavailable) {
            return Map.of();
        }
    }

    static Map<String, LocalDate> readListings(String page) throws IOException {
        var tables = TABLE.matcher(page);
        while (tables.find()) {
            String table = tables.group(1);
            if (!table.contains("（上場承認日）") || !table.contains(">コード</th>")) continue;
            var body = BODY.matcher(table);
            if (!body.find()) throw new IOException("Missing JPX listing rows");
            var rows = groups(ROW, body.group(1));
            var events = new HashMap<String, LocalDate>();
            for (int i = 0; i < rows.size(); i++) {
                var fields = groups(CELL, rows.get(i));
                if (fields.size() != 8 || i + 1 == rows.size()) continue;
                var marketFields = groups(CELL, rows.get(i + 1));
                if (marketFields.size() != 6 || !DOMESTIC_MARKETS.contains(
                        JpxIssuerArchive.visibleText(marketFields.get(0)))) continue;
                var date = LISTING_DATE.matcher(fields.get(0));
                if (!date.find()) continue;
                var code = JpxIssuerArchive.visibleText(fields.get(2));
                if (!CODE.matcher(code).matches()) throw new IOException("Invalid JPX listing code");
                try {
                    var listingDate = LocalDate.parse(date.group(1).replace('/', '-'));
                    var earlier = events.putIfAbsent(code, listingDate);
                    if (earlier != null && !earlier.equals(listingDate)) throw new IOException("Conflicting JPX listing dates");
                } catch (DateTimeParseException invalid) {
                    throw new IOException("Invalid JPX listing date", invalid);
                }
            }
            if (!events.isEmpty()) return Map.copyOf(events);
        }
        throw new IOException("Missing JPX listings");
    }

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
                var fields = groups(CELL, rows.group(1)).stream()
                        .map(JpxIssuerArchive::visibleText).collect(Collectors.toUnmodifiableList());
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

    private static List<String> groups(Pattern pattern, String html) {
        var values = new ArrayList<String>();
        var matcher = pattern.matcher(html);
        while (matcher.find()) values.add(matcher.group(1));
        return values;
    }

    JpxStockUniverse forTradingDay(LocalDate day, Map<String, LocalDate> listings, Map<String, LocalDate> delistings) {
        var effective = new HashSet<>(codes);
        listings.forEach((code, date) -> {
            if (date.isAfter(asOf) && !date.isAfter(day)) effective.add(code);
        });
        delistings.forEach((code, date) -> {
            var listing = listings.get(code);
            if (date.isAfter(asOf) && !date.isAfter(day)
                    && (listing == null || !listing.isAfter(date) || listing.isAfter(day))) effective.remove(code);
        });
        return effective.equals(codes) ? this : new JpxStockUniverse(asOf, Set.copyOf(effective));
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
