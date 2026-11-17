package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.FileInputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.net.ssl.HttpsURLConnection;

@TargetApi(35)
final class JpxDailyCheck {
    private static final String REPORT_ROOT =
            "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/";
    private static final int MAX_PDF_BYTES = 32_000_000;
    private static final List<String> SAMPLE_CODES = List.of("1301", "3861", "7203");

    private static final BigDecimal BUDGET = BigDecimal.valueOf(JapanScreen.BUDGET);
    private static final BigDecimal LOT_PRICE_LIMIT = BUDGET.movePointLeft(2);

    record Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes,
                  Set<String> ambiguous, String edition) {
        Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes, Set<String> ambiguous) {
            this(date, source, quotes, ambiguous, "");
        }

        BigDecimal close(String code) {
            var sessions = quotes.get(code);
            if (ambiguous.contains(code) || sessions == null || sessions.close() == null
                    || sessions.close().signum() <= 0) return null;
            return sessions.close();
        }
    }

    record Comparison(Report latest, Report previous) {
        String processedKey(String rightsRevision) {
            if (previous == null) return "";
            return editionKey(latest.date(), latest.edition(), previous.date(), previous.edition(), rightsRevision);
        }
        String html(JpxShareRights rights) {
            var message = new StringBuilder("立会日 ").append(latest.date());
            if (previous == null) {
                message.append("<br>比較用の日報を取得できなかった");
            } else {
                message.append("<br>比較日 ").append(previous.date()).append("（分割等の調整前の終値）");
            }
            var ordered = new ArrayList<>(SAMPLE_CODES);
            ordered.sort(Comparator.comparingInt((String code) -> budgetQuantity(latest.close(code))).reversed());
            for (String code : ordered) {
                var close = latest.close(code);
                var sessions = latest.quotes().get(code);
                message.append("<br><br>").append(code).append("  ");
                if (latest.ambiguous().contains(code)) {
                    message.append("終値を一意に読み取れなかった");
                } else if (sessions == null) {
                    message.append("銘柄行が見つからなかった");
                } else if (close == null) {
                    message.append("終値なし");
                } else {
                    message.append(close.toPlainString()).append(" 円")
                            .append(sessions.afternoon() == null ? "（前場）" : "（後場）");
                    appendBudget(message, close);
                    if (previous != null) appendChange(message, code, close, rights);
                    // Missing monthly evidence is not evidence that no split occurred.
                    // Keep the displayed valuation on hold, not only its day-to-day transition.
                    String valuationHold = rights.holdReason(
                            code, JpxReferenceFinancials.ANNUAL_END, latest.date());
                    if (valuationHold.isEmpty()) {
                        JpxReferenceFinancials.appendHtml(message, code, latest.date(), close);
                    } else {
                        message.append("<br>参考PER・PBRは保留（")
                                .append(valuationHold)
                                .append("）");
                        JpxReferenceFinancials.appendShareData(message, code, latest.date());
                    }
                    if (previous != null) appendReferenceTransition(message, code, rights);
                }
            }
            appendSource(message.append("<br>"), latest);
            if (previous != null) appendSource(message, previous);
            return message.toString();
        }

        private static void appendBudget(StringBuilder message, BigDecimal close) {
            message.append("<br>100株 ").append(close.movePointRight(2).stripTrailingZeros().toPlainString())
                    .append("円 / 1株 ").append(close.toPlainString()).append("円（終値換算・手数料別）");
            int quantity = budgetQuantity(close);
            if (quantity == 100) {
                message.append("<br>予算10万円以内 · 100株");
            } else if (quantity == 1) {
                message.append("<br>予算10万円以内 · 単元未満株の取扱いは証券会社による");
            } else {
                message.append("<br>予算10万円超 · 1株でも対象外");
            }
        }

        private void appendChange(StringBuilder message, String code, BigDecimal close, JpxShareRights rights) {
            BigDecimal previousClose = previous.close(code);
            if (previousClose == null) {
                message.append("<br>比較日の終値を確認できなかった");
                return;
            }
            message.append("<br>比較日の終値 ").append(previousClose.toPlainString()).append("円");
            if (rights.firstChange(code, previous.date(), latest.date()) != null) {
                message.append(" · 値動きの比較は保留（期間内に権利落日）");
                return;
            }
            var change = close.subtract(previousClose);
            var percent = change.movePointRight(2).divide(previousClose, 2, RoundingMode.HALF_UP);
            message.append(" / ")
                    .append(change.signum() > 0 ? "+" : "").append(change.stripTrailingZeros().toPlainString())
                    .append("円（").append(percent.signum() > 0 ? "+" : "")
                    .append(percent.toPlainString()).append("%）");
        }

        Screening screen(JpxShareRights rights) {
            var entered = new ArrayList<Entrant>();
            var held = new ArrayList<Held>();
            for (String code : SAMPLE_CODES) {
                var change = referenceChange(code, rights);
                if (!change.hold().isEmpty()) {
                    held.add(new Held(code, change.hold()));
                } else if (change.entered()) {
                    entered.add(new Entrant(code, budgetQuantity(latest.close(code))));
                }
            }
            entered.sort(Comparator.comparingInt(Entrant::quantity).reversed());
            return new Screening(List.copyOf(entered), List.copyOf(held));
        }

        private ReferenceChange referenceChange(String code, JpxShareRights rights) {
            if (previous == null || !previous.date().isBefore(latest.date())) {
                return ReferenceChange.held("比較用の日報なし");
            }
            String reason = rights.holdReason(code, JpxReferenceFinancials.ANNUAL_END, latest.date());
            if (!reason.isEmpty()) return ReferenceChange.held(reason);
            var before = referenceTier(previous, code);
            var now = referenceTier(latest, code);
            if (before == ReferenceTier.UNKNOWN || now == ReferenceTier.UNKNOWN) {
                return ReferenceChange.held("比較に必要な終値または通期決算なし");
            }
            return new ReferenceChange(before, now, "");
        }

        private void appendReferenceTransition(StringBuilder message, String code, JpxShareRights rights) {
            if (!previous.date().isBefore(latest.date())) return;
            var comparison = referenceChange(code, rights);
            var before = comparison.before();
            var now = comparison.now();
            String change;
            if (!comparison.hold().isEmpty()) {
                change = "保留（" + comparison.hold() + "）";
            } else if (before == now) {
                change = "条件の変化なし";
            } else if (now == ReferenceTier.OUTSIDE) {
                change = "条件から外れた";
            } else if (comparison.entered()) {
                change = now == ReferenceTier.LOT ? "新たに条件内（100株）" : "新たに条件内（1株）";
            } else {
                change = now == ReferenceTier.LOT ? "1株枠から100株枠へ" : "100株枠から1株枠へ";
            }
            message.append("<br>参考判定の変化 · ").append(change);
        }

        private static void appendSource(StringBuilder message, Report report) {
            message.append("<br><a href='").append(report.source()).append("'>JPX 株式相場表 ")
                    .append(report.date()).append("（PDF）</a>");
        }
    }

    record Entrant(String code, int quantity) {}

    record Held(String code, String reason) {}

    record Screening(List<Entrant> entered, List<Held> holds) {
        int held() { return holds.size(); }
    }

    private record ReferenceChange(ReferenceTier before, ReferenceTier now, String hold) {
        static ReferenceChange held(String reason) {
            return new ReferenceChange(ReferenceTier.UNKNOWN, ReferenceTier.UNKNOWN, reason);
        }

        boolean entered() {
            return before == ReferenceTier.OUTSIDE && (now == ReferenceTier.SINGLE || now == ReferenceTier.LOT);
        }
    }

    private enum ReferenceTier { UNKNOWN, OUTSIDE, SINGLE, LOT }

    private static ReferenceTier referenceTier(Report report, String code) {
        var close = report.close(code);
        if (close == null) return ReferenceTier.UNKNOWN;
        var financial = JpxReferenceFinancials.condition(code, report.date(), close);
        if (financial == JpxReferenceFinancials.Condition.UNAVAILABLE) return ReferenceTier.UNKNOWN;
        if (financial != JpxReferenceFinancials.Condition.MATCH) return ReferenceTier.OUTSIDE;
        return switch (budgetQuantity(close)) {
            case 100 -> ReferenceTier.LOT;
            case 1 -> ReferenceTier.SINGLE;
            default -> ReferenceTier.OUTSIDE;
        };
    }

    static int budgetQuantity(BigDecimal close) {
        if (close == null || close.signum() <= 0 || close.compareTo(BUDGET) > 0) return 0;
        return close.compareTo(LOT_PRICE_LIMIT) <= 0 ? 100 : 1;
    }

    @FunctionalInterface
    interface ReportLoader {
        Report load(LocalDate day) throws IOException;
    }

    static Comparison check(File cache) throws IOException {
        var today = LocalDate.now(ZoneId.of("Asia/Tokyo"));
        var pdf = File.createTempFile("jpx-daily-", ".pdf", cache);
        try {
            return checkRecent(today, day -> {
                var response = download(reportUrl(day), pdf);
                if (!response.exists()) return null;
                var report = readReport(pdf, day);
                return new Report(report.date(), report.source(), report.quotes(), report.ambiguous(), response.version());
            });
        } finally {
            pdf.delete();
        }
    }

    static Comparison checkWatch(File cache, String processedKey, String rightsRevision) throws IOException {
        var today = LocalDate.now(ZoneId.of("Asia/Tokyo"));
        if (unchanged(today, processedKey, rightsRevision, JpxDailyCheck::head)) return null;
        return check(cache);
    }

    record Edition(boolean exists, String version) {}

    @FunctionalInterface
    interface EditionLoader {
        Edition load(LocalDate day) throws IOException;
    }

    static boolean unchanged(LocalDate today, String processedKey, String rightsRevision, EditionLoader loader) {
        if (processedKey.isEmpty() || rightsRevision.isEmpty()) return false;
        LocalDate latest = null;
        String latestEdition = "";
        try {
            for (LocalDate date : candidateDays(today)) {
                if (Thread.currentThread().isInterrupted()) return false;
                var edition = loader.load(date);
                if (!edition.exists()) continue;
                if (edition.version().isEmpty()) return false;
                if (latest != null) {
                    return processedKey.equals(editionKey(latest, latestEdition, date, edition.version(), rightsRevision));
                }
                latest = date;
                latestEdition = edition.version();
            }
        } catch (IOException ignored) {
            // A failed header probe must go through the normal PDF acquisition.
        }
        return false;
    }

    private static String editionKey(LocalDate latest, String latestEdition, LocalDate previous,
                                     String previousEdition, String rightsRevision) {
        if (latestEdition.isEmpty() || previousEdition.isEmpty() || rightsRevision.isEmpty()) return "";
        String identity = latest + "|" + latestEdition + "|" + previous + "|" + previousEdition + "|" + rightsRevision;
        try {
            var digest = MessageDigest.getInstance("SHA-256").digest(identity.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(error);
        }
    }

    static Comparison checkRecent(LocalDate today, ReportLoader load) throws IOException {
        Report latest = null;
        for (LocalDate day : candidateDays(today)) {
            if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
            Report report;
            try {
                report = load.load(day);
            } catch (IOException error) {
                if (latest == null || Thread.currentThread().isInterrupted()) throw error;
                return new Comparison(latest, null);
            }
            if (report == null) continue;
            // A stale cache or a mismatched response must not masquerade as the
            // requested trading day. Reject it rather than comparing false dates.
            if (report.date() == null || !report.date().equals(day)) {
                throw new IOException("東証日報の取引日が要求日と一致しない: " + day);
            }
            if (latest != null) {
                if (!report.date().isBefore(latest.date())) {
                    throw new IOException("東証日報の比較日が最新日より前ではない");
                }
                return new Comparison(latest, report);
            }
            latest = report;
        }
        if (latest != null) return new Comparison(latest, null);
        throw new IOException("直近10日間に公表された株式相場表が見つからなかった");
    }

    static Report readReport(File pdf, LocalDate day) throws IOException {
        try {
            var table = JpxAndroidPdfReader.read(pdf, Set.copyOf(SAMPLE_CODES), day);
            return new Report(day, reportUrl(day), table.prices(), table.ambiguousCodes());
        } catch (IllegalArgumentException | SecurityException error) {
            throw new IOException("東証日報のPDFを読み取れなかった", error);
        }
    }

    static List<LocalDate> candidateDays(LocalDate today) {
        var days = new ArrayList<LocalDate>();
        for (int offset = 1; offset <= 10; offset++) {
            var day = today.minusDays(offset);
            if (day.getDayOfWeek() != DayOfWeek.SATURDAY && day.getDayOfWeek() != DayOfWeek.SUNDAY) {
                days.add(day);
            }
        }
        return days;
    }

    private static String reportUrl(LocalDate day) {
        String digits = day.format(DateTimeFormatter.BASIC_ISO_DATE);
        return REPORT_ROOT + digits.substring(0, 6) + "/stq_" + digits + ".pdf";
    }

    private static HttpsURLConnection open(String source) throws IOException {
        var connection = (HttpsURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(12_000);
        connection.setReadTimeout(20_000);
        connection.setInstanceFollowRedirects(false);
        connection.setUseCaches(false);
        return connection;
    }

    private static Edition head(LocalDate day) throws IOException {
        var connection = open(reportUrl(day));
        try {
            connection.setRequestMethod("HEAD");
            return edition(connection);
        } finally {
            connection.disconnect();
        }
    }

    private static Edition edition(HttpsURLConnection connection) throws IOException {
        int status = connection.getResponseCode();
        if (status == 404) return new Edition(false, "");
        if (status != 200) throw new IOException("JPXの応答 HTTP " + status);
        String version = connection.getHeaderField("x-amz-version-id");
        if (version != null && !version.equals("null") && version.matches("[A-Za-z0-9_.-]{1,128}")) {
            return new Edition(true, "version:" + version);
        }
        String tag = connection.getHeaderField("ETag");
        return new Edition(true, tag != null && tag.matches("\"[A-Za-z0-9_.-]{1,128}\"") ? "etag:" + tag : "");
    }

    private static Edition download(String source, File pdf) throws IOException {
        var connection = open(source);
        try {
            var result = edition(connection);
            if (!result.exists()) return result;
            if (connection.getContentLengthLong() > MAX_PDF_BYTES) {
                throw new IOException("東証日報のPDFが上限サイズを超えている");
            }
            try (var input = connection.getInputStream(); var output = new FileOutputStream(pdf)) {
                byte[] buffer = new byte[32_768];
                int total = 0;
                for (int count; (count = input.read(buffer)) != -1;) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
                    total += count;
                    if (total > MAX_PDF_BYTES) {
                        throw new IOException("東証日報のPDFが上限サイズを超えている");
                    }
                    output.write(buffer, 0, count);
                }
            }
            // A CDN or proxy can return an HTML error page with HTTP 200.
            // Never pass such a response to the Android PDF engine.
            try (var header = new FileInputStream(pdf)) {
                byte[] signature = new byte[5];
                if (header.read(signature) != signature.length
                        || signature[0] != '%' || signature[1] != 'P'
                        || signature[2] != 'D' || signature[3] != 'F'
                        || signature[4] != '-') {
                    throw new IOException("東証日報の取得内容がPDFではない");
                }
            }
            return result;
        } finally {
            connection.disconnect();
        }
    }
}
