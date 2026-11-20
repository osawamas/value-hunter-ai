package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;
import android.graphics.pdf.PdfRenderer;
import android.graphics.pdf.models.selection.SelectionBoundary;
import android.os.Build;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.IOException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Set;

/** Converts the Android PDF engine's numeric selections into JPX table cells. */
@TargetApi(35)
final class JpxAndroidPdfReader {
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
                    if (i == 0) JpxPdfLayout.checkDate(text, expectedDate);
                    if (JpxPdfLayout.OUTSIDE_DOMESTIC.matcher(text).find()) break;
                    var matcher = JpxPdfLayout.CELL.matcher(text);
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
}
