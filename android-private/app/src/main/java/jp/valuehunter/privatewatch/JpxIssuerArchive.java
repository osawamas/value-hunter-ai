package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.CookieManager;
import java.net.URI;
import java.net.URL;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

import javax.net.ssl.HttpsURLConnection;

/** Checks the exchange's company disclosure archive for gaps in the monthly rights reports. */
final class JpxIssuerArchive {
    private static final URI HOME = URI.create("https://www2.jpx.co.jp/tseHpFront/StockSearch.do");
    private static final URI DETAIL = HOME.resolve("JJK010030Action.do");
    private static final int MAX_RESPONSE = 2_000_000;
    private static final ZoneId TOKYO = ZoneId.of("Asia/Tokyo");
    private static final Charset LEGACY_JAPANESE = Charset.forName("windows-31j");
    private static final Pattern SECTION = Pattern.compile("displayMore\\('(110[1-4])', '(\\d+)', '1'\\)");
    private static final Pattern ROW = Pattern.compile(
            "<tr id=\"(110[1-4])_(\\d+)\"[^>]*>\\s*<td[^>]*>\\s*(\\d{4}/\\d{2}/\\d{2})"
                    + "\\s*</td>\\s*<td[^>]*>(.*?)</td>", Pattern.DOTALL);
    private static final Pattern SHARE_CHANGE = Pattern.compile(
            "株式(?:の)?(?:分割|併合)|無償割当[てり]?|新株落|割当増資|権利落");
    private static final Pattern TAG = Pattern.compile("<[^>]*>");
    private static final Pattern SPACE = Pattern.compile("\\s+");

    record Review(LocalDate since, LocalDate through) {
        boolean covers(LocalDate from, LocalDate until) {
            return !from.isBefore(since) && !until.isAfter(through);
        }
    }

    private JpxIssuerArchive() {}

    static boolean clear(String html, String code, LocalDate since) {
        if (!html.contains("上場会社詳細（適時開示情報）")
                || !Pattern.compile("<td>\\s*" + code + "0\\s*</td>").matcher(html).find()
                || !html.contains("決定事実 / 発生事実")) return false;

        var counts = new HashMap<String, Integer>();
        var sections = SECTION.matcher(html);
        while (sections.find()) {
            if (counts.put(sections.group(1), Integer.parseInt(sections.group(2))) != null) return false;
        }
        if (!counts.keySet().equals(Set.of("1101", "1102", "1103", "1104"))
                || counts.get("1102") == 0) return false;

        var found = new HashMap<String, Set<Integer>>();
        var rows = ROW.matcher(html);
        while (rows.find()) {
            String section = rows.group(1);
            int index = Integer.parseInt(rows.group(2));
            if (index >= counts.get(section) || !found.computeIfAbsent(section, ignored -> new HashSet<>()).add(index)) {
                return false;
            }
            LocalDate date = LocalDate.parse(rows.group(3).replace('/', '-'));
            String title = SPACE.matcher(TAG.matcher(rows.group(4)).replaceAll("")).replaceAll("");
            if (title.isEmpty() || (!date.isBefore(since) && SHARE_CHANGE.matcher(title).find())) return false;
        }
        return counts.entrySet().stream().allMatch(
                section -> found.getOrDefault(section.getKey(), Set.of()).size() == section.getValue());
    }

    static JpxShareRights.Selection extend(Context context, JpxShareRights.Selection selection) {
        LocalDate today = LocalDate.now(TOKYO);
        LocalDate through = today.minusDays(1);
        var rights = selection.rights();
        if (rights.months().isEmpty()) return selection;
        // Only bridge the gap after the last complete monthly report. Never bypass an older missing month.
        LocalDate since = rights.months().stream().max(YearMonth::compareTo).orElseThrow()
                .plusMonths(1).atDay(1);
        if (through.isBefore(since)) return selection;

        var cache = context.getSharedPreferences("jpx-issuer-archive", Context.MODE_PRIVATE);
        var verified = new HashMap<String, Review>();
        List<String> audited = new ArrayList<>();
        var session = new CookieManager();
        boolean connected = false;
        boolean offline = false;
        for (String code : JpxDailyCheck.WATCH_CODES) {
            if (!rights.coveredCodes().contains(code)
                    || rights.firstChange(code, JpxReferenceFinancials.periodEnd(code), through) != null) continue;
            String key = code + "/" + since;
            String reviewed = cache.getString(key, "");
            String current = through.toString() + ":";
            if (!reviewed.startsWith(current) && !offline) {
                try {
                    if (!connected) {
                        request(HOME, null, session);
                        connected = true;
                    }
                    boolean clear = clear(request(DETAIL, code, session), code, since.minusYears(1));
                    reviewed = current + (clear ? "clear" : "hold");
                    cache.edit().putString(key, reviewed).apply();
                } catch (IOException failure) {
                    // Keep prior verified coverage. An unavailable site cannot certify a new session.
                    offline = true;
                } catch (IllegalArgumentException | java.time.DateTimeException malformed) {
                    // A changed page format cannot certify a session.
                }
            }
            if (!reviewed.endsWith(":clear")) continue;
            try {
                LocalDate day = LocalDate.parse(reviewed.substring(0, reviewed.length() - ":clear".length()));
                if (day.isBefore(since) || day.isAfter(through)) continue;
                verified.put(code, new Review(since, day));
                audited.add(code + "=" + day);
            } catch (java.time.DateTimeException malformed) {
                // Ignore an invalid cached date.
            }
        }
        if (verified.isEmpty()) return selection;
        var updated = new JpxShareRights(rights.coveredCodes(), rights.months(), rights.notices(), Map.copyOf(verified));
        return new JpxShareRights.Selection(updated, selection.status() + " · 東証開示で補完 " + verified.size() + "銘柄",
                selection.revision() + "/" + String.join(",", audited));
    }

    private static String request(URI uri, String code, CookieManager session) throws IOException {
        var connection = (HttpsURLConnection) new URL(uri.toString()).openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(8_000);
        connection.setReadTimeout(10_000);
        try {
            for (var header : session.get(uri, Map.of()).entrySet()) {
                connection.setRequestProperty(header.getKey(), String.join("; ", header.getValue()));
            }
            if (code != null) {
                connection.setRequestMethod("POST");
                connection.setDoOutput(true);
                connection.setRequestProperty("Referer", HOME.toString());
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
                byte[] payload = ("BaseJh=BaseJh&mgrCd=" + code + "0&jjHisiFlg=1&sniMtGmnId=JJK010010")
                        .getBytes(StandardCharsets.US_ASCII);
                connection.setFixedLengthStreamingMode(payload.length);
                try (var output = connection.getOutputStream()) {
                    output.write(payload);
                }
            }
            if (connection.getResponseCode() != 200) throw new IOException("JPX company archive unavailable");
            session.put(uri, connection.getHeaderFields());
            try (var input = connection.getInputStream(); var bytes = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                for (int n; (n = input.read(buffer)) != -1;) {
                    if (bytes.size() + n > MAX_RESPONSE) throw new IOException("JPX company archive too large");
                    bytes.write(buffer, 0, n);
                }
                String utf8 = bytes.toString(StandardCharsets.UTF_8.name());
                return utf8.contains("東京証券取引所") ? utf8 : bytes.toString(LEGACY_JAPANESE.name());
            }
        } finally {
            connection.disconnect();
        }
    }
}
