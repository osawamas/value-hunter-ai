package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.FileInputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URL;
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
                  Set<String> ambiguous) {
        BigDecimal close(String code) {
            var sessions = quotes.get(code);
            if (ambiguous.contains(code) || sessions == null || sessions.close() == null
                    || sessions.close().signum() <= 0) return null;
            return sessions.close();
        }
    }

    record Comparison(Report latest, Report previous) {
        String html() {
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
                    if (previous != null) appendChange(message, close, previous.close(code));
                    JpxReferenceFinancials.appendHtml(message, code, latest.date(), close);
                    if (previous != null) appendReferenceTransition(message, code);
                }
            }
            if (previous != null) {
                message.append("<br><br>参考判定は分割・併合を未照合");
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

        private static void appendChange(StringBuilder message, BigDecimal close, BigDecimal previous) {
            if (previous == null) {
                message.append("<br>比較日の終値を確認できなかった");
                return;
            }
            var change = close.subtract(previous);
            var percent = change.movePointRight(2).divide(previous, 2, RoundingMode.HALF_UP);
            message.append("<br>比較日の終値 ").append(previous.toPlainString()).append("円 / ")
                    .append(change.signum() > 0 ? "+" : "").append(change.stripTrailingZeros().toPlainString())
                    .append("円（").append(percent.signum() > 0 ? "+" : "")
                    .append(percent.toPlainString()).append("%）");
        }

        private void appendReferenceTransition(StringBuilder message, String code) {
            if (!previous.date().isBefore(latest.date())) return;
            var before = referenceTier(previous, code);
            var now = referenceTier(latest, code);
            String change;
            if (before == ReferenceTier.UNKNOWN || now == ReferenceTier.UNKNOWN) {
                change = "保留（比較に必要な終値または通期決算なし）";
            } else if (before == now) {
                change = "条件の変化なし";
            } else if (now == ReferenceTier.OUTSIDE) {
                change = "条件から外れた";
            } else if (before == ReferenceTier.OUTSIDE) {
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
            return checkRecent(today, day -> download(reportUrl(day), pdf) ? readReport(pdf, day) : null);
        } finally {
            pdf.delete();
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
            if (latest != null) return new Comparison(latest, report);
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

    private static boolean download(String source, File pdf) throws IOException {
        var connection = (HttpsURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(12_000);
        connection.setReadTimeout(20_000);
        connection.setInstanceFollowRedirects(false);
        try {
            int status = connection.getResponseCode();
            if (status == 404) return false;
            if (status != 200) throw new IOException("JPXの応答 HTTP " + status);
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
            return true;
        } finally {
            connection.disconnect();
        }
    }
}
