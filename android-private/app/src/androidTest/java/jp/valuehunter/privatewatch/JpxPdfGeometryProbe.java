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
import java.time.YearMonth;
import java.util.HashSet;
import java.util.Locale;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import org.json.JSONObject;

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
            JpxShareRights rights;
            try (var input = getContext().getAssets().open("jpx-share-rights-20261117.json")) {
                rights = JpxShareRights.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8)).rights();
            }
            String logs = digestReport(directory, LocalDate.of(2026, 10, 29), codes)
                    + digestReport(directory, LocalDate.of(2026, 11, 13), codes)
                    + digestReport(directory, LocalDate.of(2026, 11, 16), codes)
                    + checkSampleReport(directory, rights);
            checkRightsRefresh(getTargetContext());
            checkJpxWatch();
            checkReportEditions();
            JpxWatchDeliveryProbe.run(getTargetContext(), directory, rights);
            result.putString("stream", logs + "JPX_ANDROID_RIGHTS_REFRESH_OK\nJPX_ANDROID_WATCH_OK\nJPX_ANDROID_WATCH_DELIVERY_OK\nJPX_ANDROID_EDITION_OK\n");
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

    private static String checkSampleReport(File directory, JpxShareRights rights) throws IOException {
        var file = new File(directory, "jpx-20261116.pdf");
        var day = LocalDate.of(2026, 11, 16);
        var report = JpxDailyCheck.readReport(file, day);
        var previousDay = LocalDate.of(2026, 11, 13);
        var previous = JpxDailyCheck.readReport(new File(directory, "jpx-20261113.pdf"), previousDay);
        var comparison = JpxDailyCheck.checkRecent(day.plusDays(2), date -> {
            if (date.isAfter(day)) return null;
            if (date.equals(day)) return report;
            if (date.equals(previousDay)) return previous;
            throw new AssertionError("Checked an unexpected JPX date: " + date);
        });
        String html = comparison.html(rights);
        var realScreen = comparison.screen(rights);
        if (realScreen.held() != 3 || !realScreen.entered().isEmpty()) {
            throw new AssertionError("Published JPX reports notified during missing rights coverage");
        }
        if (!report.date().equals(day) || !report.source().endsWith("/202611/stq_20261116.pdf")
                || !html.contains("7203  3428 円（後場）")
                || !html.contains("3861  847.4 円（後場）")
                || !html.contains("100株 84740円 / 1株 847.4円")
                || html.contains("参考PER 13.87倍 / 参考PBR 0.67倍")
                || !html.contains("自己株式控除後 850020917株")
                || !html.contains("予算10万円以内 · 100株")
                || !html.contains("予算10万円以内 · 単元未満株の取扱いは証券会社による")
                || html.contains("財務判定 ·")
                || html.indexOf("3861  847.4") > html.indexOf("1301  4705")
                || html.contains("参考PER 8.17倍 / 参考PBR 0.72倍")
                || html.contains("参考PER 11.61倍 / 参考PBR 1.12倍")
                || !html.contains("自己株式控除後 11888495株")
                || !html.contains("自己株式控除後 11737603369株（2026-10-31時点）")
                || !html.contains("S100ZH9B.pdf")
                || !html.contains("比較日 2026-11-13")
                || html.split("参考判定の変化 · 保留（権利落月報の未確認月 2026-10、2026-11", -1).length != 4
                || html.split("参考PER・PBRは保留（権利落月報の未確認月 2026-10、2026-11", -1).length != 4
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
            if (date.equals(day.plusDays(1))) return null;
            if (date.equals(day)) return report;
            if (date.equals(previousDay)) throw new IOException("Unavailable report");
            throw new AssertionError("A failed download must not select an older comparison date");
        });
        if (!oneReport.html(rights).contains("7203  3428 円（後場）")
                || !oneReport.html(rights).contains("比較用の日報を取得できなかった")) {
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
                || !nearLimit.toString().contains("財務判定 · 参考候補")) {
            throw new AssertionError("Rounded display value was used to check the PER limit");
        }
        checkReferenceTransitions(day);
        checkShareRights(rights);
        return "JPX_ANDROID_PREVIEW_OK\n";
    }

    private static void checkReferenceTransitions(LocalDate day) {
        var before = day.minusDays(3);
        var abovePer = sampleReport(before, "3861", "916.51", false);
        var atPer = sampleReport(day, "3861", "916.50", false);
        assertTransition(atPer, abovePer, "新たに優先候補（100株）");
        assertTransition(sampleReport(day, "3861", "1200.00", false),
                sampleReport(before, "3861", "1300.00", false), "新たに参考候補（1株）");
        assertTransition(sampleReport(day, "3861", "916.51", false),
                sampleReport(before, "3861", "916.50", false), "参考候補へ変更（100株）");
        assertTransition(sampleReport(day, "1301", "1000.00", false),
                sampleReport(before, "1301", "1000.01", false), "1株枠から100株枠へ");
        assertTransition(atPer, sampleReport(before, "3861", "916.51", true),
                "保留（比較に必要な終値または通期決算なし）");
        assertTransition(atPer, sampleReport(LocalDate.of(2026, 5, 15), "3861", "916.51", false),
                "保留（比較に必要な終値または通期決算なし）");
    }

    private static JpxDailyCheck.Report sampleReport(LocalDate day, String code, String close,
                                                    boolean ambiguous) {
        return new JpxDailyCheck.Report(day, "", Map.of(code,
                new JpxCloseTable.Sessions(null, new BigDecimal(close))), ambiguous ? Set.of(code) : Set.of());
    }

    private static void assertTransition(JpxDailyCheck.Report latest, JpxDailyCheck.Report previous,
                                         String expected) {
        var months = new HashSet<YearMonth>();
        for (int month = 4; month <= 11; month++) months.add(YearMonth.of(2026, month));
        var complete = new JpxShareRights(Set.of("1301", "3861", "7203"), months, List.of());
        String html = new JpxDailyCheck.Comparison(latest, previous).html(complete);
        if (!html.contains("参考判定の変化 · " + expected)) {
            throw new AssertionError("Missing JPX reference transition: " + expected);
        }
    }

    private static void checkShareRights(JpxShareRights rights) {
        var before = LocalDate.of(2026, 11, 18);
        var exDay = LocalDate.of(2026, 11, 19);
        var start = JpxReferenceFinancials.ANNUAL_END;
        var actual = rights.firstChange("6861", start, exDay);
        if (rights.firstChange("6861", start, before) != null
                || actual == null || !actual.exDay().equals(exDay)
                || !actual.source().endsWith("20261111.xls")
                || rights.firstChange("6861", exDay, exDay.plusDays(1)) != null) {
            throw new AssertionError("KEYENCE's official ex-date was applied outside its boundary");
        }
        var scenario = new JpxShareRights(Set.of("3861"), Set.of(),
                List.of(new JpxShareRights.Notice("3861", exDay, actual.source())));
        var comparison = new JpxDailyCheck.Comparison(
                sampleReport(exDay, "3861", "847.40", false), sampleReport(before, "3861", "916.51", false));
        String html = comparison.html(scenario);
        if (!html.contains("値動きの比較は保留（期間内に権利落日）")
                || !html.contains("参考PER・PBRは保留（権利落日 2026-11-19")
                || !html.contains("参考判定の変化 · 保留（権利落日 2026-11-19")
                || html.contains("新たに")) {
            throw new AssertionError("A share change produced a misleading reference transition");
        }
    }

    private static void checkRightsRefresh(android.content.Context context) throws Exception {
        var file = new android.util.AtomicFile(new File(context.getFilesDir(), "jpx-share-rights.json"));
        try {
            var bundled = JpxShareRights.refresh(context, () -> { throw new IOException("offline"); });
            var publishedMonth = bundled.rights().months().stream().max(YearMonth::compareTo)
                    .orElseThrow(() -> new AssertionError("The bundled rights snapshot has no verified months"));
            if (!bundled.status().contains("アプリ同梱資料")
                    || !bundled.rights().coveredCodes().containsAll(Set.of("1301", "3861", "7203"))) {
                throw new AssertionError("Missing bundled rights coverage for the monitored stocks");
            }
            String original;
            try (var input = context.getAssets().open("jpx-share-rights.json")) {
                original = new String(input.readAllBytes(), StandardCharsets.UTF_8);
            }
            var remote = new JSONObject(original);
            var revision = java.time.Instant.parse(remote.getString("revision")).plusSeconds(60);
            remote.put("revision", revision.toString());
            remote.getJSONObject("monthlySources").remove(publishedMonth.toString());
            var updated = JpxShareRights.refresh(context, remote::toString);
            if (!updated.status().contains("オンライン資料") || updated.rights().months().contains(publishedMonth)) {
                throw new AssertionError("The online rights snapshot did not replace superseded coverage");
            }
            for (String invalid : new String[]{"{}", original}) {
                var result = JpxShareRights.refresh(context, () -> invalid);
                if (!result.status().contains("端末に保存した資料")
                        || result.rights().months().contains(publishedMonth)) {
                    throw new AssertionError("An invalid or older remote snapshot superseded the cache");
                }
            }
        } finally {
            file.delete();
        }
    }

    private static void checkJpxWatch() {
        var before = LocalDate.of(2026, 11, 13);
        var day = LocalDate.of(2026, 11, 16);
        var months = new HashSet<YearMonth>();
        for (int month = 4; month <= 11; month++) months.add(YearMonth.of(2026, month));
        var complete = new JpxShareRights(Set.of("3861"), months, List.of());
        var partial = new JpxShareRights(Set.of("3861"), Set.of(YearMonth.of(2026, 9)), List.of());
        var outdated = sampleReport(before, "3861", "916.51", false);
        var current = sampleReport(day, "3861", "916.50", false);
        var comparison = new JpxDailyCheck.Comparison(current, outdated);
        var screen = comparison.screen(complete);
        var codes = List.of(new JpxDailyCheck.Candidate("3861", 100, ValueCandidateScreen.Level.PRIORITY));
        if (!screen.entered().equals(codes) || !comparison.screen(partial).entered().isEmpty()) {
            throw new AssertionError("JPX watch did not gate entry on verified reference data");
        }
        var unavailable = new JpxDailyCheck.Comparison(current, sampleReport(before, "3861", "916.51", true));
        if (!unavailable.screen(complete).entered().isEmpty()
                || !new JpxDailyCheck.Comparison(current, null).screen(complete).entered().isEmpty()) {
            throw new AssertionError("JPX watch notified without a usable comparison");
        }
        if (!JpxWatchWorker.pending(before, before, day, codes, Set.of()).equals(codes)
                || !JpxWatchWorker.pending(before, day, day, codes, Set.of()).equals(codes)
                || !JpxWatchWorker.pending(before, day, day, codes, Set.of("3861")).isEmpty()
                || !JpxWatchWorker.pending(null, null, day, codes, Set.of()).isEmpty()
                || !JpxWatchWorker.pending(before, day, before, codes, Set.of()).isEmpty()) {
            throw new AssertionError("JPX watch allowed a duplicate, initial or stale notification");
        }
    }

    private static void checkReportEditions() {
        var monday = LocalDate.of(2026, 11, 16);
        var friday = LocalDate.of(2026, 11, 13);
        var today = monday.plusDays(2);
        var latest = new JpxDailyCheck.Report(monday, "", Map.of(), Set.of(), "version:monday");
        var previous = new JpxDailyCheck.Report(friday, "", Map.of(), Set.of(), "version:friday");
        var comparison = new JpxDailyCheck.Comparison(latest, previous);
        String revision = "2026-11-17T00:00:00Z";
        String saved = comparison.processedKey(revision);
        JpxDailyCheck.EditionLoader same = date -> {
            if (date.equals(monday.plusDays(1))) return new JpxDailyCheck.Edition(false, "");
            if (date.equals(monday)) return new JpxDailyCheck.Edition(true, "version:monday");
            if (date.equals(friday)) return new JpxDailyCheck.Edition(true, "version:friday");
            throw new AssertionError("Unexpected JPX header date " + date);
        };
        if (saved.isEmpty() || !JpxDailyCheck.unchanged(today, saved, revision, same)
                || JpxDailyCheck.unchanged(today, saved, "2026-11-18T00:00:00Z", same)
                || JpxDailyCheck.unchanged(today, saved, revision, date -> date.equals(friday)
                        ? new JpxDailyCheck.Edition(true, "version:corrected") : same.load(date))
                || JpxDailyCheck.unchanged(today, saved, revision,
                        date -> new JpxDailyCheck.Edition(true, ""))
                || JpxDailyCheck.unchanged(today, saved, revision, date -> { throw new IOException("HEAD failed"); })
                || JpxDailyCheck.unchanged(today, saved, revision, date -> date.equals(monday.plusDays(1))
                        ? new JpxDailyCheck.Edition(true, "version:new-day") : same.load(date))) {
            throw new AssertionError("JPX watch skipped a new, corrected, or unverified input");
        }
    }

    private static String display(BigDecimal value) {
        return value == null ? "" : value.toPlainString();
    }
}
