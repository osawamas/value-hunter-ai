package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.URI;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.ResolverStyle;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.function.BooleanSupplier;
import java.util.regex.Pattern;

/** Complete dated TDnet listings extend a verified issuer archive without re-querying each company daily. */
final class JpxDisclosureCalendar {
    private static final String CACHE = "disclosure-days";
    private static final String ROOT = "https://www.release.tdnet.info/inbs/";
    private static final int PAGE_SIZE = 100;
    private static final int MAX_TOTAL = 3_000;
    private static final int RETAIN_DAYS = 29;
    private static final DateTimeFormatter TITLE_DATE = DateTimeFormatter.ofPattern("uuuu年M月d日", Locale.JAPAN)
            .withResolverStyle(ResolverStyle.STRICT);
    private static final Pattern DATE = Pattern.compile("id=\"kaiji-date-1\">([^<]+)</div>");
    private static final Pattern TOTAL = Pattern.compile(
            "class=\"kaijiSum\">(\\d+)～(\\d+)件(?:&nbsp;|\\s)*/(?:&nbsp;|\\s)*全(\\d+)件</div>");
    private static final Pattern ROW = Pattern.compile(
            "<tr(?:\\s[^>]*)?>\\s*<td[^>]*kjTime\"[^>]*>[^<]*</td>\\s*"
            + "<td[^>]*kjCode\"[^>]*>\\s*([0-9A-Z]{5})\\s*</td>\\s*"
            + "<td[^>]*kjName\"[^>]*>[^<]*</td>\\s*<td[^>]*kjTitle\"[^>]*>(.*?)</td>", Pattern.DOTALL);
    private static final Pattern RETRACTED_TITLE =
            Pattern.compile("<s(?:\\s[^>]*)?>.*?</s\\s*>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    @FunctionalInterface
    interface PageLoader { String fetch(URI uri) throws IOException; }

    record Day(Set<String> rights, Set<String> annual) {}
    private record Page(int total, int first, int last, Day day) {}

    private JpxDisclosureCalendar() {}

    static Day read(LocalDate day, PageLoader network, BooleanSupplier stopped) throws IOException {
        var rights = new HashSet<String>();
        var annual = new HashSet<String>();
        int total = -1;
        for (int page = 1; total < 0 || (page - 1) * PAGE_SIZE < total; page++) {
            if (stopped.getAsBoolean()) throw new IOException("TDnet check interrupted");
            URI url = URI.create(ROOT + String.format(Locale.ROOT, "I_list_%03d_%s.html", page,
                    day.format(DateTimeFormatter.BASIC_ISO_DATE)));
            Page parsed = page(network.fetch(url), day);
            if (parsed == null || total >= 0 && parsed.total() != total
                    || parsed.first() != (page - 1) * PAGE_SIZE + 1
                    || parsed.last() != Math.min(page * PAGE_SIZE, parsed.total())) {
                if (page == 1 && parsed != null && parsed.total() == 0) return parsed.day();
                throw new IOException("TDnet listing is incomplete");
            }
            total = parsed.total();
            rights.addAll(parsed.day().rights());
            annual.addAll(parsed.day().annual());
        }
        return new Day(Set.copyOf(rights), Set.copyOf(annual));
    }

    private static Page page(String html, LocalDate day) {
        var date = DATE.matcher(html);
        if (!date.find()) return null;
        try {
            if (!LocalDate.parse(date.group(1), TITLE_DATE).equals(day)) return null;
        } catch (DateTimeException invalid) {
            return null;
        }
        var count = TOTAL.matcher(html);
        if (!count.find()) {
            if (html.contains("に開示された情報") && (html.contains("開示情報はありません")
                    || html.contains("開示された情報はありません"))) {
                return new Page(0, 0, 0, new Day(Set.of(), Set.of()));
            }
            return null;
        }
        int first = Integer.parseInt(count.group(1));
        int last = Integer.parseInt(count.group(2));
        int total = Integer.parseInt(count.group(3));
        if (first < 1 || first > last || last > total || total > MAX_TOTAL) return null;
        var rights = new HashSet<String>();
        var annual = new HashSet<String>();
        var rows = ROW.matcher(html);
        int seen = 0;
        while (rows.find()) {
            seen++;
            String code = rows.group(1).substring(0, 4);
            String title = JpxIssuerArchive.visibleText(RETRACTED_TITLE.matcher(rows.group(2)).replaceAll(""));
            if (title.isEmpty()) return null;
            if (JpxIssuerArchive.shareChange(title)) rights.add(code);
            if (JpxIssuerArchive.annualTitle(title)) annual.add(code);
        }
        return seen == last - first + 1 ? new Page(total, first, last, new Day(rights, annual)) : null;
    }

    static Map<LocalDate, Day> refresh(SharedPreferences state, LocalDate latest, LocalDate earliest,
                                       BooleanSupplier stopped) {
        var days = new HashMap<LocalDate, Day>();
        try {
            var saved = new JSONObject(state.getString(CACHE, "{}"));
            var keys = saved.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                LocalDate date = LocalDate.parse(key);
                if (date.isBefore(latest.minusDays(RETAIN_DAYS)) || date.isAfter(latest)) continue;
                var entry = saved.getJSONObject(key);
                days.put(date, new Day(codes(entry.getJSONArray("rights")), codes(entry.getJSONArray("annual"))));
            }
        } catch (JSONException | DateTimeException invalid) {
            days.clear();
        }
        int fetched = 0;
        boolean changed = false;
        for (LocalDate day = latest; !day.isBefore(earliest) && !day.isBefore(latest.minusDays(RETAIN_DAYS))
                && fetched < 8 && !stopped.getAsBoolean(); day = day.minusDays(1)) {
            if (days.containsKey(day)) continue;
            fetched++;
            try {
                days.put(day, read(day, JpxIssuerArchive::publicPage, stopped));
                changed = true;
            } catch (IOException | IllegalArgumentException error) {
                // A date remains unverified until all its listings are available.
                break;
            }
        }
        if (changed) {
            try {
                var saved = new JSONObject();
                for (var entry : days.entrySet()) {
                    saved.put(entry.getKey().toString(), new JSONObject()
                            .put("rights", new JSONArray(entry.getValue().rights()))
                            .put("annual", new JSONArray(entry.getValue().annual())));
                }
                state.edit().putString(CACHE, saved.toString()).apply();
            } catch (JSONException impossible) {
                throw new IllegalStateException(impossible);
            }
        }
        return Map.copyOf(days);
    }

    private static Set<String> codes(JSONArray values) throws JSONException {
        var result = new HashSet<String>();
        for (int i = 0; i < values.length(); i++) {
            String code = values.getString(i);
            if (!code.matches("[0-9A-Z]{4}")) throw new JSONException("Invalid TDnet security code");
            result.add(code);
        }
        return Set.copyOf(result);
    }
}
