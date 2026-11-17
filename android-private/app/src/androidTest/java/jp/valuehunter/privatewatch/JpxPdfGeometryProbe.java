package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDate;
import java.util.HashSet;
import java.util.Locale;
import java.util.TreeSet;

public final class JpxPdfGeometryProbe extends Instrumentation {
    @Override
    public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override
    public void onStart() {
        var result = new Bundle();
        try {
            var directory = getTargetContext().getDataDir();
            var codes = new HashSet<String>();
            try (var input = new BufferedReader(new FileReader(new File(directory, "jpx-codes.txt")))) {
                for (String code; (code = input.readLine()) != null;) {
                    codes.add(code);
                }
            }
            if (codes.size() < 3000) throw new AssertionError("Missing JPX stock universe");
            String logs = digestReport(directory, LocalDate.of(2026, 10, 29), codes)
                    + digestReport(directory, LocalDate.of(2026, 11, 13), codes)
                    + digestReport(directory, LocalDate.of(2026, 11, 16), codes)
                    + checkSampleReport(directory);
            result.putString("stream", logs);
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("stream", "JPX_PDF_GEOMETRY_FAILED: " + error + "\n");
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private static String digestReport(File directory, LocalDate day, HashSet<String> codes) throws Exception {
        String filename = "jpx-" + day.format(java.time.format.DateTimeFormatter.BASIC_ISO_DATE) + ".pdf";
        var table = JpxAndroidPdfReader.read(new File(directory, filename), codes, day);
        var prices = table.prices();
        var ambiguous = table.ambiguousCodes();
        var digest = MessageDigest.getInstance("SHA-256");
        int closes = 0;
        for (String code : new TreeSet<>(prices.keySet())) {
            var quote = prices.get(code);
            if (quote.close() != null) closes++;
            String row = code + "\t" + display(quote.morning()) + "\t" + display(quote.afternoon()) + "\n";
            digest.update(row.getBytes(StandardCharsets.UTF_8));
        }
        for (String code : new TreeSet<>(ambiguous)) {
            digest.update((code + "\tconflict\n").getBytes(StandardCharsets.UTF_8));
        }
        var hex = new StringBuilder();
        for (byte value : digest.digest()) hex.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return "JPX_ANDROID_CLOSES " + filename + " " + prices.size() + " " + closes + " " + hex + "\n";
    }

    private static String checkSampleReport(File directory) throws IOException {
        var file = new File(directory, "jpx-20261116.pdf");
        var day = LocalDate.of(2026, 11, 16);
        var report = JpxDailyCheck.readReport(file, day);
        var previousDay = LocalDate.of(2026, 11, 13);
        var previous = JpxDailyCheck.readReport(new File(directory, "jpx-20261113.pdf"), previousDay);
        var comparison = JpxDailyCheck.checkRecent(day.plusDays(2), date -> {
            if (date.equals(day.plusDays(1))) return null;
            if (date.equals(day)) return report;
            if (date.equals(previousDay)) return previous;
            throw new AssertionError("Checked an unexpected JPX date: " + date);
        });
        String html = comparison.html();
        if (!report.date().equals(day) || !report.source().endsWith("/202611/stq_20261116.pdf")
                || !html.contains("7203  3428 円（後場）")
                || !html.contains("3861  847.4 円（後場）")
                || !html.contains("100株 84740円 / 1株 847.4円")
                || !html.contains("参考PER 13.87倍 / 参考PBR 0.67倍")
                || !html.contains("自己株式控除後 850020917株")
                || !html.contains("予算10万円以内 · 100株")
                || !html.contains("予算10万円以内 · 単元未満株の取扱いは証券会社による")
                || !html.contains("参考財務条件は対象外 · PBR 1倍超")
                || html.indexOf("3861  847.4") > html.indexOf("1301  4705")
                || !html.contains("参考PER 8.17倍 / 参考PBR 0.72倍")
                || !html.contains("参考PER 11.61倍 / 参考PBR 1.12倍")
                || !html.contains("自己株式控除後 11888495株")
                || !html.contains("自己株式控除後 11737603369株（2026-10-31時点）")
                || !html.contains("S100ZH9B.pdf")
                || !html.contains("比較日 2026-11-13")
                || !html.contains("比較日の終値 4660円 / +45円（+0.97%）")
                || !html.contains("比較日の終値 3418円 / +10円（+0.29%）")
                || !html.contains("時価総額は保留（立会日の株式数未照合）")) {
            throw new AssertionError("The Android daily report preview did not match the JPX reference");
        }
        try {
            JpxDailyCheck.readReport(file, day.minusDays(1));
            throw new AssertionError("JPX report with a different trading date was accepted");
        } catch (IOException expected) {
            if (!expected.getMessage().contains("立会日が取得先の日付と一致しない")) throw expected;
        }
        var beforeDisclosure = new StringBuilder();
        JpxReferenceFinancials.appendHtml(beforeDisclosure, "1301", LocalDate.of(2026, 5, 15),
                new BigDecimal("4705"));
        if (beforeDisclosure.toString().contains("参考PER")
                || beforeDisclosure.toString().contains("自己株式控除後")) {
            throw new AssertionError("Financials disclosed on or after the close must not be used");
        }
        var onShareDisclosure = new StringBuilder();
        JpxReferenceFinancials.appendHtml(onShareDisclosure, "7203", previousDay, new BigDecimal("3418"));
        if (!onShareDisclosure.toString().contains("自己株式控除後 11779620513株（2026-09-30時点）")
                || onShareDisclosure.toString().contains("S100ZH9B.pdf")) {
            throw new AssertionError("Used an EDINET share count before its eligible session");
        }
        var oneReport = JpxDailyCheck.checkRecent(day.plusDays(1), date -> {
            if (date.equals(day)) return report;
            if (date.equals(previousDay)) throw new IOException("Unavailable report");
            throw new AssertionError("A failed download must not select an older comparison date");
        });
        if (!oneReport.html().contains("7203  3428 円（後場）")
                || !oneReport.html().contains("比較用の日報を取得できなかった")) {
            throw new AssertionError("A failed comparison hid the latest report");
        }
        if (JpxDailyCheck.budgetQuantity(new BigDecimal("1000.00")) != 100
                || JpxDailyCheck.budgetQuantity(new BigDecimal("1000.01")) != 1
                || JpxDailyCheck.budgetQuantity(new BigDecimal("100000.00")) != 1
                || JpxDailyCheck.budgetQuantity(new BigDecimal("100000.01")) != 0) {
            throw new AssertionError("Incorrect JPX purchase budget boundary");
        }
        var nearLimit = new StringBuilder();
        JpxReferenceFinancials.appendHtml(nearLimit, "3861", day, new BigDecimal("916.51"));
        if (!nearLimit.toString().contains("参考PER 15.00倍")
                || !nearLimit.toString().contains("参考財務条件は対象外 · PER 15倍超")) {
            throw new AssertionError("Rounded display value was used to check the PER limit");
        }
        return "JPX_ANDROID_PREVIEW_OK\n";
    }

    private static String display(BigDecimal value) {
        return value == null ? "" : value.toPlainString();
    }
}
