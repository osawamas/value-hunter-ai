package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;
import android.graphics.pdf.PdfRenderer;
import android.graphics.pdf.models.selection.SelectionBoundary;
import android.os.Build;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.IOException;
import java.text.Normalizer;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Set;
import java.util.regex.Pattern;

/** Converts the Android PDF engine's numeric selections into JPX table cells. */
@TargetApi(35)
final class JpxAndroidPdfReader {
    private static final Pattern OUTSIDE_DOMESTIC =
            Pattern.compile("(?m)^\\s*(外国株式|Foreign Stock|ToSTNeT市場)\\s*$");
    private static final Pattern CELL =
            Pattern.compile("(?<![0-9A-Za-z.,])[0-9][0-9A-Z,]*(?:\\.[0-9]+)?(?![0-9A-Za-z.,])");

    private static final Pattern REPORT_DATE =
            Pattern.compile("([0-9]{4})\\s*年\\s*([0-9]{1,2})\\s*月\\s*([0-9]{1,2})\\s*日");

    static JpxCloseTable read(File file, Set<String> stockCodes, LocalDate expectedDate)
            throws IOException {
        if (Build.VERSION.SDK_INT < 35) {
            throw new UnsupportedOperationException("The JPX PDF reader requires Android 15 or later");
        }
        var table = new JpxCloseTable(stockCodes);
        try (var descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
             var renderer = new PdfRenderer(descriptor)) {
            if (renderer.getPageCount() == 0) {
                throw new IOException("東証日報にページがない");
            }
            for (int i = 0; i < renderer.getPageCount(); i++) {
                if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
                try (var page = renderer.openPage(i)) {
                    var contents = page.getTextContents();
                    if (contents.isEmpty() && i > 0) continue;
                    if (contents.size() != 1) {
                        throw new IOException("東証日報のテキストを読み取れなかった（" + (i + 1) + "ページ）");
                    }
                    String text = contents.get(0).getText();
                    if (i == 0 && !expectedDate.equals(tradingDate(text))) {
                        throw new IOException("東証日報の立会日が取得先の日付と一致しない");
                    }
                    if (OUTSIDE_DOMESTIC.matcher(text).find()) break;
                    var matcher = CELL.matcher(text);
                    var words = new ArrayList<JpxCloseTable.Word>();
                    while (matcher.find()) {
                        String token = matcher.group();
                        var selected = page.selectContent(new SelectionBoundary(matcher.start()),
                                new SelectionBoundary(matcher.end()));
                        if (selected == null || selected.getSelectedTextContents().size() != 1) continue;
                        var content = selected.getSelectedTextContents().get(0);
                        if (!token.equals(content.getText().trim()) || content.getBounds().size() != 1) continue;
                        var box = content.getBounds().get(0);
                        words.add(new JpxCloseTable.Word(box.left, box.top, box.right, box.bottom, token));
                    }
                    table.acceptPage(page.getWidth(), words);
                }
            }
        }
        return table;
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
