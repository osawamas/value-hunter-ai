package jp.valuehunter.privatewatch;

import java.io.IOException;
import java.text.Normalizer;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.util.regex.Pattern;

final class JpxPdfLayout {
    static final Pattern OUTSIDE_DOMESTIC =
            Pattern.compile("(?m)^\\s*(外国株式|Foreign Stock|ToSTNeT市場)\\s*$");
    static final Pattern CELL =
            Pattern.compile("(?<![0-9A-Za-z.,])[0-9][0-9A-Z,]*(?:\\.[0-9]+)?(?![0-9A-Za-z.,])");

    private static final Pattern REPORT_DATE =
            Pattern.compile("([0-9]{4})\\s*年\\s*([0-9]{1,2})\\s*月\\s*([0-9]{1,2})\\s*日");

    private JpxPdfLayout() {}

    static void checkDate(String text, LocalDate expected) throws IOException {
        if (!expected.equals(tradingDate(text))) {
            throw new IOException("東証日報の立会日が取得先の日付と一致しない");
        }
    }

    private static LocalDate tradingDate(String text) throws IOException {
        var matcher = REPORT_DATE.matcher(Normalizer.normalize(text, Normalizer.Form.NFKC));
        LocalDate reportDate = null;
        try {
            while (matcher.find()) {
                var found = LocalDate.of(Integer.parseInt(matcher.group(1)),
                        Integer.parseInt(matcher.group(2)), Integer.parseInt(matcher.group(3)));
                if (reportDate != null && !reportDate.equals(found)) {
                    throw new IOException("東証日報に異なる立会日が含まれている");
                }
                reportDate = found;
            }
        } catch (DateTimeException error) {
            throw new IOException("東証日報の立会日が無効", error);
        }
        if (reportDate == null) {
            throw new IOException("東証日報から立会日を一意に読み取れなかった");
        }
        return reportDate;
    }
}
