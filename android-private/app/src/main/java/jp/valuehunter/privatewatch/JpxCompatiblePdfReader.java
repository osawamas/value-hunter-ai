package jp.valuehunter.privatewatch;

import android.content.Context;

import com.tom_roush.pdfbox.android.PDFBoxResourceLoader;
import com.tom_roush.pdfbox.io.MemoryUsageSetting;
import com.tom_roush.pdfbox.pdmodel.PDDocument;
import com.tom_roush.pdfbox.pdmodel.PDPage;
import com.tom_roush.pdfbox.text.PDFTextStripper;
import com.tom_roush.pdfbox.text.TextPosition;

import java.io.File;
import java.io.IOException;
import java.io.Writer;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/** Reads JPX reports on devices without the platform PDF text APIs. */
final class JpxCompatiblePdfReader {
    private JpxCompatiblePdfReader() {}

    static JpxCloseTable read(Context context, File file, Set<String> codes, LocalDate date)
            throws IOException {
        try (var document = open(context, file)) {
            return readDocument(document, codes, date);
        }
    }

    private static JpxCloseTable readDocument(PDDocument document, Set<String> codes, LocalDate date)
            throws IOException {
        int pages = document.getNumberOfPages();
        if (pages == 0 || pages > 600) throw new IOException("東証日報のページ数が無効");
        var reader = new ReportStripper(codes, date);
        try (var sink = new Writer() {
            @Override public void write(char[] data, int offset, int length) {}
            @Override public void flush() {}
            @Override public void close() {}
        }) {
            reader.writeText(document, sink);
        }
        if (reader.pageNumber == 0) throw new IOException("東証日報の立会日を確認できなかった");
        return reader.table;
    }

    static String readText(Context context, File file, int maxPages) throws IOException {
        try (var document = open(context, file)) {
            int pages = document.getNumberOfPages();
            if (pages == 0 || pages > maxPages) return "";
            var reader = new PDFTextStripper();
            reader.setSortByPosition(true);
            return reader.getText(document);
        }
    }

    private static PDDocument open(Context context, File file) throws IOException {
        PDFBoxResourceLoader.init(context.getApplicationContext());
        var scratch = MemoryUsageSetting.setupMixed(8L * 1024 * 1024, 128L * 1024 * 1024);
        scratch.setTempDir(context.getCacheDir());
        return PDDocument.load(file, scratch);
    }

    // The loader must be initialized before PDFTextStripper loads font resources.
    private static final class ReportStripper extends PDFTextStripper {
        private final JpxCloseTable table;
        private final LocalDate expectedDate;
        private int pageNumber;
        private boolean outsideDomestic;
        private final List<JpxCloseTable.Word> words = new ArrayList<>();
        private final StringBuilder pageText = new StringBuilder();

        private ReportStripper(Set<String> codes, LocalDate expectedDate) throws IOException {
            this.table = new JpxCloseTable(codes);
            this.expectedDate = expectedDate;
            setSortByPosition(true);
        }

        @Override public void processPage(PDPage page) throws IOException {
            if (outsideDomestic) return;
            if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
            if (page.getRotation() != 0) throw new IOException("東証日報のページが回転している");
            pageNumber++;
            words.clear();
            pageText.setLength(0);
            super.processPage(page);
            String text = pageText.toString();
            if (pageNumber == 1) JpxPdfLayout.checkDate(text, expectedDate);
            outsideDomestic = JpxPdfLayout.OUTSIDE_DOMESTIC.matcher(text).find();
            if (!outsideDomestic) table.acceptPage(page.getCropBox().getWidth(), words);
        }

        @Override protected void writeLineSeparator() {
            pageText.append('\n');
        }

        @Override protected void writeWordSeparator() {
            pageText.append(' ');
        }

        @Override protected void writeString(String text, List<TextPosition> positions) {
            pageText.append(text);
            var match = JpxPdfLayout.CELL.matcher(text);
            // A ligature or differently encoded text can change the character-to-glyph mapping.
            // Leave that word out instead of guessing its geometry.
            if (text.length() != positions.size()) return;
            while (match.find()) {
                var first = positions.get(match.start());
                var last = positions.get(match.end() - 1);
                words.add(new JpxCloseTable.Word(first.getXDirAdj(), first.getYDirAdj() - first.getHeightDir(),
                        last.getXDirAdj() + last.getWidthDirAdj(), first.getYDirAdj(), match.group()));
            }
        }
    }
}
