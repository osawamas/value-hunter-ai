package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertThrows;
import org.json.JSONException;

public class UsMonthlyHistoryTest {
    @Test public void displaysOnlyCompleteUnsplitRangesAndRejectsDuplicateRows() throws Exception {
        var first = YearMonth.of(2021, 11);
        var dates = new java.util.TreeSet<>(UsMonthlyHistory.monthEndDates(first, 60));
        var rows = new JSONArray();
        for (int i = 0; i < 60; i++) {
            var last = dates.floor(first.plusMonths(i).atEndOfMonth());
            rows.put(new JSONObject().put("symbol", "IBM").put("trading_date", last.toString()).put("close", i + 1));
        }
        var batches = List.of(rows);
        var text = UsMonthlyHistory.summarize(batches, first, Map.of(), Set.of("IBM", "AAPL"));
        assertTrue(text.contains("IBM · 1.00〜60.00 USD"));
        assertTrue(text.contains("AAPL · 0/60か月"));
        text = UsMonthlyHistory.summarize(batches, first, Map.of("IBM", LocalDate.of(2023, 3, 1)), Set.of("IBM"));
        assertTrue(text.contains("株式分割の調整を確認するまで保留"));
        rows.put(rows.getJSONObject(0));
        assertThrows(JSONException.class, () ->
                UsMonthlyHistory.summarize(batches, first, Map.of(), Set.of("IBM")));
    }
}
