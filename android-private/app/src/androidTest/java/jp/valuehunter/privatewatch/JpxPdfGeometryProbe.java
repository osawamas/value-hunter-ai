package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.Instrumentation;
import android.graphics.RectF;
import android.graphics.pdf.PdfRenderer;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/** Checks official report coordinates with Android's actual PDF engine. */
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
            checkReport("jpx-20261029.pdf", List.of(
                    new Quote("1301", "4475"), new Quote("1401", "1386")));
            checkReport("jpx-20261116.pdf", List.of(new Quote("7203", "3428")));
            result.putString("stream", "JPX_PDF_GEOMETRY_OK: 3 reference closes in 2 official PDFs\n");
            finish(Activity.RESULT_OK, result);
        } catch (Exception | AssertionError error) {
            result.putString("stream", "JPX_PDF_GEOMETRY_FAILED: " + error + "\n");
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private void checkReport(String filename, List<Quote> quotes) throws Exception {
        var file = new File(getTargetContext().getDataDir(), filename);
        try (var descriptor = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
             var renderer = new PdfRenderer(descriptor)) {
            var expected = new ArrayList<>(quotes);
            for (int i = 0; i < renderer.getPageCount() && !expected.isEmpty(); i++) {
                try (var page = renderer.openPage(i)) {
                    var checked = new ArrayList<Quote>();
                    for (Quote quote : expected) {
                        if (matchesAfternoonClose(page, quote)) checked.add(quote);
                    }
                    expected.removeAll(checked);
                }
            }
            if (!expected.isEmpty()) {
                throw new AssertionError(filename + ": could not place closes for " + expected);
            }
        }
    }

    private static boolean matchesAfternoonClose(PdfRenderer.Page page, Quote quote) {
        var width = page.getWidth();
        var codes = matches(page, quote.code());
        var codesInColumn = codes.stream().filter(word -> {
            double x = word.centerX(width);
            return x > .057 && x < .094;
        }).toList();
        if (codesInColumn.isEmpty()) return false;
        var words = new ArrayList<>(codesInColumn);
        words.addAll(matches(page, quote.price()));
        String comma = String.format(java.util.Locale.US, "%,d", Integer.parseInt(quote.price()));
        if (!comma.equals(quote.price())) words.addAll(matches(page, comma));
        var table = new JpxCloseTable(Set.of(quote.code()));
        table.acceptPage(width, words);
        var sessions = table.prices().get(quote.code());
        return sessions != null && sessions.afternoon() != null
                && sessions.afternoon().compareTo(new java.math.BigDecimal(quote.price())) == 0;
    }

    private static List<JpxCloseTable.Word> matches(PdfRenderer.Page page, String text) {
        var words = new ArrayList<JpxCloseTable.Word>();
        for (var match : page.searchText(text)) {
            if (match.getBounds().size() == 1) {
                RectF box = match.getBounds().get(0);
                words.add(new JpxCloseTable.Word(box.left, box.top, box.right, box.bottom, text));
            }
        }
        return words;
    }

    private record Quote(String code, String price) {}
}
