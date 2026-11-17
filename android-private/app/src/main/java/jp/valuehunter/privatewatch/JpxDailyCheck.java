package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.FileInputStream;
import java.net.URL;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.net.ssl.HttpsURLConnection;

@TargetApi(35)
final class JpxDailyCheck {
    private static final String REPORT_ROOT =
            "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/";
    private static final int MAX_PDF_BYTES = 32_000_000;
    private static final List<String> SAMPLE_CODES = List.of("1301", "7203");

    record Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes,
                  Set<String> ambiguous) {
        String summary() {
            var message = new StringBuilder("立会日 ").append(date);
            for (String code : SAMPLE_CODES) {
                var sessions = quotes.get(code);
                message.append("\n").append(code).append("  ");
                if (ambiguous.contains(code)) {
                    message.append("終値を一意に読み取れなかった");
                } else if (sessions == null) {
                    message.append("銘柄行が見つからなかった");
                } else if (sessions.close() == null) {
                    message.append("終値なし");
                } else {
                    message.append(sessions.close().toPlainString()).append(" 円")
                            .append(sessions.afternoon() == null ? "（前場）" : "（後場）");
                }
            }
            return message.toString();
        }
    }

    static Report check(File cache) throws IOException {
        var today = LocalDate.now(ZoneId.of("Asia/Tokyo"));
        var pdf = File.createTempFile("jpx-daily-", ".pdf", cache);
        try {
            for (LocalDate day : candidateDays(today)) {
                if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
                String source = reportUrl(day);
                if (download(source, pdf)) return readReport(pdf, day);
            }
            throw new IOException("直近10日間に公表された株式相場表が見つからなかった");
        } finally {
            pdf.delete();
        }
    }

    static Report readReport(File pdf, LocalDate day) throws IOException {
        var table = JpxAndroidPdfReader.read(pdf, Set.copyOf(SAMPLE_CODES), day);
        return new Report(day, reportUrl(day), table.prices(), table.ambiguousCodes());
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
