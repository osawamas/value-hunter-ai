package jp.valuehunter.privatewatch;

import java.time.LocalDate;

import org.junit.Test;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class JpxIssuerArchiveTest {
    private static final LocalDate SINCE = LocalDate.of(2025, 10, 1);
    private static final String ARCHIVE = """
            上場会社詳細（適時開示情報）
            <td>94320</td>
            決定事実 / 発生事実
            displayMore('1101', '0', '1')
            displayMore('1102', '1', '1')
            displayMore('1103', '0', '1')
            displayMore('1104', '0', '1')
            <tr id="1102_0"><td align="center">2026/11/12</td>
            <td><a href="/disc/94320/140120261112572676.pdf">%s</a></td></tr>
            """;

    @Test public void verifiesCompleteMatchingArchiveAndRejectsWrongOrIncompletePage() {
        String clear = ARCHIVE.formatted("自己株式の取得状況に関するお知らせ");
        assertTrue(JpxIssuerArchive.clear(clear, "9432", SINCE));
        assertFalse(JpxIssuerArchive.clear(clear, "9434", SINCE));
        assertFalse(JpxIssuerArchive.clear(clear.replace("'1102', '1'", "'1102', '2'"), "9432", SINCE));
        assertFalse(JpxIssuerArchive.clear(clear.replace("'1104', '0', '1'", ""), "9432", SINCE));
    }

    @Test public void unresolvedShareChangesHoldAndPastDisclosuresOutsideLookbackDoNot() {
        String split = ARCHIVE.formatted("株式 <strong>分割</strong>に関するお知らせ");
        assertFalse(JpxIssuerArchive.clear(split, "9432", SINCE));
        assertFalse(JpxIssuerArchive.clear(ARCHIVE.formatted("株式の併合に関するお知らせ"), "9432", SINCE));
        assertTrue(JpxIssuerArchive.clear(split.replace("2026/11/12", "2025/09/30"), "9432", SINCE));
    }
}
