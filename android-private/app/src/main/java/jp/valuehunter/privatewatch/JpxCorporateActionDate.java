package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.URI;
import java.time.LocalDate;
import java.time.DateTimeException;
import java.util.regex.Pattern;

import javax.net.ssl.HttpsURLConnection;

/** Resolves historic splits and consolidations from their issuer disclosures. */
final class JpxCorporateActionDate {
    private static final int MAX_PDF_BYTES = 2_000_000;
    private static final int MAX_PAGES = 8;
    private static final Pattern SINGLE_ACTION = Pattern.compile(
            "^株式(?:の)?(分割|併合)(?:について|に関するお知らせ|及び|および|並びに|ならびに|に伴う|、|に係る|の実施)");
    private static final Pattern MIXED_OR_CONDITIONAL = Pattern.compile(
            "無償割当|増資|株式交換|株式移転|株式交付|第三者割当|公開買付|反対株主|中止|訂正|条件|撤回|取消|取止");
    private static final Pattern CONDITIONAL = Pattern.compile(
            "効力発生の条件|株主総会の承認を条件|効力発生日を変更|分割を中止|併合を中止");
    private static final Pattern EFFECTIVE = Pattern.compile("効力発生日[:：]?(?:[（(]予定[）)])?[:：]?"
            + "((?:20[0-9]{2}|令和(?:元|[0-9]{1,2}))年[0-9]{1,2}月[0-9]{1,2}日)");

    private static final Pattern RECORD = Pattern.compile("基準日[:：]?"
            + "((?:20[0-9]{2}|令和(?:元|[0-9]{1,2}))年[0-9]{1,2}月[0-9]{1,2}日)");

    private JpxCorporateActionDate() {}

    static LocalDate recordDay(String body, JpxIssuerArchive.Disclosure disclosure, LocalDate effective) {
        if (effective == null) return null;
        var dates = RECORD.matcher(JpxAnnualSummary.normalized(body));
        LocalDate found = null;
        while (dates.find()) {
            try {
                var day = JpxAnnualSummary.documentDate(dates.group(1));
                if (day == null || day.isBefore(disclosure.day()) || !day.isBefore(effective)
                        || found != null && !found.equals(day)) return null;
                found = day;
            } catch (DateTimeException invalid) {
                return null;
            }
        }
        return found;
    }

    static boolean supported(String title) {
        var action = SINGLE_ACTION.matcher(title);
        return action.find() && !MIXED_OR_CONDITIONAL.matcher(title).find()
                && !(title.contains("分割") && title.contains("併合"));
    }

    static LocalDate effective(String body, JpxIssuerArchive.Disclosure disclosure) {
        if (!supported(disclosure.title())) return null;
        String text = JpxAnnualSummary.normalized(body);
        String action = disclosure.title().contains("分割") ? "分割" : "併合";
        if (!text.contains("株式" + action) && !text.contains("株式の" + action)) return null;
        if (CONDITIONAL.matcher(text).find()) return null;
        var dates = EFFECTIVE.matcher(text);
        LocalDate found = null;
        boolean shareDate = false;
        try {
            while (dates.find()) {
                LocalDate date = JpxAnnualSummary.documentDate(dates.group(1));
                if (date == null || date.isBefore(disclosure.day()) || found != null && !found.equals(date)) return null;
                found = date;
                String preceding = text.substring(Math.max(0, dates.start() - 150), dates.start());
                boolean articles = preceding.endsWith("定款変更の") || preceding.endsWith("定款の一部変更の");
                if (!articles && (preceding.contains("基準日") || preceding.endsWith(action + "の"))) {
                    shareDate = true;
                }
            }
        } catch (DateTimeException invalid) {
            return null;
        }
        return shareDate ? found : null;
    }

    @TargetApi(35)
    static String readPdf(URI uri, File cache) throws IOException {
        if (!JpxIssuerArchive.disclosureSource(uri)) throw new IOException("Invalid JPX disclosure address");
        File file = File.createTempFile("jpx-action-", ".pdf", cache);
        try {
            var connection = (HttpsURLConnection) uri.toURL().openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(6_000);
            connection.setReadTimeout(10_000);
            try {
                int status = connection.getResponseCode();
                if (status == 429 || status >= 500) throw new JpxIssuerArchive.HttpFailure(status);
                if (status != 200 || connection.getContentLength() > MAX_PDF_BYTES) return "";
                try (var input = connection.getInputStream(); var output = new FileOutputStream(file)) {
                    var buffer = new byte[8192];
                    int total = 0;
                    for (int n; (n = input.read(buffer)) >= 0;) {
                        total += n;
                        if (total > MAX_PDF_BYTES || Thread.currentThread().isInterrupted()) return "";
                        output.write(buffer, 0, n);
                    }
                }
            } finally {
                connection.disconnect();
            }
            try (var descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
                 var pdf = new PdfRenderer(descriptor)) {
                if (pdf.getPageCount() == 0 || pdf.getPageCount() > MAX_PAGES) return "";
                var body = new StringBuilder();
                for (int i = 0; i < pdf.getPageCount(); i++) {
                    try (var page = pdf.openPage(i)) {
                        var blocks = page.getTextContents();
                        if (blocks.isEmpty()) return "";
                        for (var block : blocks) body.append(block.getText()).append('\n');
                    }
                }
                return body.toString();
            }
        } catch (IllegalArgumentException | IllegalStateException | SecurityException invalid) {
            return "";
        } finally {
            file.delete();
        }
    }
}
