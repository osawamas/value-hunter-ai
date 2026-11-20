package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.CookieManager;
import java.net.URI;
import java.net.URL;
import java.nio.charset.Charset;
import java.nio.charset.CharacterCodingException;
import java.nio.ByteBuffer;
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
    private static final Pattern PDF_LINK = Pattern.compile("href=\"(/disc/[0-9A-Z]{4}0/[0-9]+\\.pdf)\"");
    private static final Pattern ANNUAL_LINK = Pattern.compile(
            "href=\"(/disc/[0-9A-Z]{4}0/[0-9]+_tse-a(?:ce|ne)[A-Za-z0-9-]+-ixbrl\\.htm)\"");
    private static final Pattern FISCAL_MONTH = Pattern.compile("(?:(20[0-9]{2})|(令和)(元|[0-9]{1,2}))年(0?[1-9]|1[0-2])月期");
    private static final Pattern NON_ANNUAL = Pattern.compile("四半期|中間|半期");
    private static final Pattern ROW = Pattern.compile(
            "<tr id=\"(110[1-4])_(\\d+)\"[^>]*>\\s*<td[^>]*>\\s*(\\d{4}/\\d{2}/\\d{2})"
                    + "\\s*</td>\\s*<td[^>]*>(.*?)</td>(.*?)</tr>", Pattern.DOTALL);
    private static final Pattern SHARE_CHANGE = Pattern.compile(
            "株式(?:の)?(?:分割|併合)|無償割当[てり]?|新株落|割当増資|権利落");
    private static final Pattern TAG = Pattern.compile("<[^>]*>");

    record Review(LocalDate since, LocalDate through) {
        boolean covers(LocalDate from, LocalDate until) {
            return !from.isBefore(since) && !until.isAfter(through);
        }
    }

    private JpxIssuerArchive() {}

    record Disclosure(LocalDate day, String title, URI annualLink, URI pdfLink, boolean results) {
        boolean corrected() { return title.contains("訂正"); }

        YearMonth fiscalMonth() {
            var match = FISCAL_MONTH.matcher(title);
            if (!match.find()) return null;
            int year = match.group(1) != null ? Integer.parseInt(match.group(1))
                    : 2018 + ("元".equals(match.group(3)) ? 1 : Integer.parseInt(match.group(3)));
            return YearMonth.of(year, Integer.parseInt(match.group(4)));
        }
    }

    record Page(List<Disclosure> disclosures) {
        boolean clearSince(LocalDate since) {
            return disclosures.stream().noneMatch(d -> !d.day().isBefore(since) && shareChange(d.title()));
        }

        Disclosure annualOn(LocalDate date) {
            var annuals = disclosures.stream().filter(disclosure -> disclosure.results()
                    && disclosure.day().isBefore(date) && annualTitle(disclosure.title())).toList();
            var latestMonth = annuals.stream().map(Disclosure::fiscalMonth).filter(java.util.Objects::nonNull)
                    .max(YearMonth::compareTo).orElse(null);
            Disclosure latest = null;
            boolean ambiguous = false;
            for (var disclosure : annuals) {
                var month = disclosure.fiscalMonth();
                if (month != null && !month.equals(latestMonth)) continue;
                if (latest == null || disclosure.day().isAfter(latest.day())) {
                    latest = disclosure;
                    ambiguous = false;
                } else if (latest.day().equals(disclosure.day()) && !latest.equals(disclosure)) {
                    if (latest.corrected() == disclosure.corrected()) ambiguous = true;
                    else if (disclosure.corrected()) {
                        latest = disclosure;
                        ambiguous = false;
                    }
                }
            }
            if (ambiguous) return null;
            return latest;
        }
    }

    @FunctionalInterface
    interface Transport {
        String fetch(URI uri, String code, CookieManager cookies) throws IOException;
    }

    static final class Session {
        private final CookieManager cookies = new CookieManager();
        private final Transport transport;
        private boolean opened;

        Session() { this(JpxIssuerArchive::request); }

        Session(Transport transport) { this.transport = transport; }

        Page archive(String code) throws IOException {
            String html = companyPage(code);
            if (searchForm(html)) {
                cookies.getCookieStore().removeAll();
                opened = false;
                html = companyPage(code);
                if (searchForm(html)) {
                    opened = false;
                    throw new IOException("JPX returned its search form instead of the company archive");
                }
            }
            return read(html, code);
        }

        private String companyPage(String code) throws IOException {
            if (!opened) {
                transport.fetch(HOME, null, cookies);
                opened = true;
            }
            return transport.fetch(DETAIL, code, cookies);
        }

        private static boolean searchForm(String html) {
            return html.contains("name=\"JJK010010Form\"") && !html.contains("上場会社詳細（適時開示情報）");
        }

        String annual(URI uri) throws IOException {
            return transport.fetch(uri, null, cookies);
        }
    }

    static boolean clear(String html, String code, LocalDate since) {
        var page = read(html, code);
        return page != null && page.clearSince(since);
    }

    static boolean shareChange(String title) {
        return SHARE_CHANGE.matcher(title).find();
    }

    static String visibleText(String markup) {
        return JpxAnnualSummary.normalized(TAG.matcher(markup).replaceAll("")
                .replace("&nbsp;", "").replace("&amp;", "&"));
    }

    static boolean disclosureSource(URI uri) {
        return uri != null && uri.toString().matches("https://www2\\.jpx\\.co\\.jp/disc/[0-9A-Z]{4}0/[0-9]+\\.pdf");
    }

    static boolean annualSource(String source, String code) {
        return source.matches("https://www2\\.jpx\\.co\\.jp/disc/" + code
                + "0/[0-9]+_tse-a(?:ce|ne)[A-Za-z0-9-]+-ixbrl\\.htm");
    }

    static Page read(String html, String code) {
        if (!code.matches("[0-9][0-9A-Z]{3}") || !html.contains("上場会社詳細（適時開示情報）")
                || !Pattern.compile("<td>\\s*" + code + "0\\s*</td>").matcher(html).find()
                || !html.contains("決定事実 / 発生事実")) return null;

        var counts = new HashMap<String, Integer>();
        var sections = SECTION.matcher(html);
        while (sections.find()) {
            if (counts.put(sections.group(1), Integer.parseInt(sections.group(2))) != null) return null;
        }
        if (!counts.keySet().equals(Set.of("1101", "1102", "1103", "1104"))) return null;

        var found = new HashMap<String, Set<Integer>>();
        var disclosures = new ArrayList<Disclosure>();
        var rows = ROW.matcher(html);
        while (rows.find()) {
            String section = rows.group(1);
            int index = Integer.parseInt(rows.group(2));
            if (index >= counts.get(section) || !found.computeIfAbsent(section, ignored -> new HashSet<>()).add(index)) {
                return null;
            }
            LocalDate date = LocalDate.parse(rows.group(3).replace('/', '-'));
            String title = visibleText(rows.group(4));
            if (title.isEmpty()) return null;
            URI annualLink = null;
            if ("1101".equals(section)) {
                var links = ANNUAL_LINK.matcher(rows.group(5));
                if (links.find()) {
                    annualLink = HOME.resolve(links.group(1));
                    if (links.find() || !annualSource(annualLink.toString(), code)) return null;
                }
            }
            URI pdfLink = null;
            if (shareChange(title)) {
                var pdfs = PDF_LINK.matcher(rows.group(4));
                if (pdfs.find()) {
                    URI link = HOME.resolve(pdfs.group(1));
                    if (link.getPath().startsWith("/disc/" + code + "0/") && !pdfs.find()) pdfLink = link;
                }
            }
            disclosures.add(new Disclosure(date, title, annualLink, pdfLink, "1101".equals(section)));
        }
        if (!counts.entrySet().stream().allMatch(
                section -> found.getOrDefault(section.getKey(), Set.of()).size() == section.getValue())) return null;
        return new Page(List.copyOf(disclosures));
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
        var session = new Session();
        boolean offline = false;
        for (String code : JpxDailyCheck.WATCH_CODES) {
            if (!rights.coveredCodes().contains(code)
                    || rights.firstChange(code, JpxReferenceFinancials.periodEnd(code), through) != null) continue;
            String key = code + "/" + since;
            String reviewed = cache.getString(key, "");
            String current = through.toString() + ":";
            if (!reviewed.startsWith(current) && !offline) {
                try {
                    var page = session.archive(code);
                    boolean clear = page != null && page.clearSince(since.minusYears(1));
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
        var updated = new JpxShareRights(rights.coveredCodes(), rights.months(), rights.notices(), Map.copyOf(verified), rights.adjustments());
        return new JpxShareRights.Selection(updated, selection.status() + " · 東証開示で補完 " + verified.size() + "銘柄",
                selection.revision() + "/" + String.join(",", audited));
    }

    static final class HttpFailure extends IOException {
        final int status;
        final String retryAfter;
        HttpFailure(int status) {
            this(status, null);
        }
        HttpFailure(int status, String retryAfter) {
            super("JPX disclosure HTTP " + status);
            this.status = status;
            this.retryAfter = retryAfter;
        }
    }

    static boolean annualTitle(String title) {
        return title.contains("決算短信") && !NON_ANNUAL.matcher(title).find();
    }

    static String publicPage(URI uri) throws IOException {
        return request(uri, null, new CookieManager());
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
            int status = connection.getResponseCode();
            if (status != 200) throw new HttpFailure(status, connection.getHeaderField("Retry-After"));
            session.put(uri, connection.getHeaderFields());
            try (var input = connection.getInputStream(); var bytes = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                for (int n; (n = input.read(buffer)) != -1;) {
                    if (bytes.size() + n > MAX_RESPONSE) throw new IllegalArgumentException("JPX company archive too large");
                    bytes.write(buffer, 0, n);
                }
                try {
                    return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes.toByteArray())).toString();
                } catch (CharacterCodingException legacy) {
                    return bytes.toString(LEGACY_JAPANESE.name());
                }
            }
        } finally {
            connection.disconnect();
        }
    }
}
