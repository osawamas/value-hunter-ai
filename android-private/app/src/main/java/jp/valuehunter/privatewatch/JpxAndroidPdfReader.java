package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;
import android.graphics.pdf.PdfRenderer;
import android.graphics.pdf.models.selection.SelectionBoundary;
import android.os.Build;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.IOException;
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

    static JpxCloseTable read(File file, Set<String> stockCodes) throws IOException {
        if (Build.VERSION.SDK_INT < 35) {
            throw new UnsupportedOperationException("The JPX PDF reader requires Android 15 or later");
        }
        var table = new JpxCloseTable(stockCodes);
        try (var descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
             var renderer = new PdfRenderer(descriptor)) {
            for (int i = 0; i < renderer.getPageCount(); i++) {
                try (var page = renderer.openPage(i)) {
                    var contents = page.getTextContents();
                    if (contents.isEmpty()) continue;
                    if (contents.size() != 1) {
                        throw new IOException("Unexpected text streams on JPX PDF page " + (i + 1));
                    }
                    String text = contents.get(0).getText();
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
        if (table.prices().size() < stockCodes.size() * .95) {
            throw new IOException("JPX Android PDF coverage too low: " + table.prices().size()
                    + " / " + stockCodes.size());
        }
        return table;
    }
}
