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
        if (!report.date().equals(day) || !report.source().endsWith("/202611/stq_20261116.pdf")
                || !report.summary().contains("7203  3428 円（後場）")) {
            throw new AssertionError("The Android daily report preview did not match the JPX reference");
        }
        try {
            JpxDailyCheck.readReport(file, day.minusDays(1));
            throw new AssertionError("JPX report with a different trading date was accepted");
        } catch (IOException expected) {
            if (!expected.getMessage().contains("立会日が取得先の日付と一致しない")) throw expected;
        }
        return "JPX_ANDROID_PREVIEW_OK\n";
    }

    private static String display(BigDecimal value) {
        return value == null ? "" : value.toPlainString();
    }
}
