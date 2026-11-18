package jp.valuehunter.privatewatch;

import android.content.Context;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;

import static java.nio.charset.StandardCharsets.UTF_8;

final class JpxHistoryReference {
    private static final String ASSET = "jpx-history.json";
    private static final int MAX_BYTES = 65_536;
    private static final JpxHistoryReference EMPTY = new JpxHistoryReference(Map.of());

    private record Range(LocalDate first, LocalDate last, int months, BigDecimal position) {}

    private final Map<String, Range> byCode;

    private JpxHistoryReference(Map<String, Range> byCode) {
        this.byCode = byCode;
    }

    static JpxHistoryReference empty() {
        return EMPTY;
    }

    static JpxHistoryReference load(Context context) {
        try (var stream = context.getAssets().open(ASSET)) {
            var bytes = stream.readNBytes(MAX_BYTES + 1);
            return bytes.length <= MAX_BYTES ? parse(new String(bytes, UTF_8)) : EMPTY;
        } catch (IOException | JSONException error) {
            return EMPTY;
        }
    }

    static JpxHistoryReference parse(String json) throws JSONException {
        var records = new JSONObject(json).getJSONObject("by_code");
        var ranges = new HashMap<String, Range>();
        var codes = records.keys();
        while (codes.hasNext()) {
            String code = codes.next();
            if (!code.matches("[0-9][0-9A-Z]{3}")) continue;
            var row = records.optJSONObject(code);
            if (row == null || !row.optString("status").equals("split_adjusted")) continue;
            try {
                var first = LocalDate.parse(row.getString("first_session"));
                var last = LocalDate.parse(row.getString("last_session"));
                int months = row.getInt("months_with_close");
                String rawPosition = row.getString("range_position");
                if (!rawPosition.matches("[01](?:[.][0-9]{1,4})?")) continue;
                var position = new BigDecimal(rawPosition);
                long calendarMonths = ChronoUnit.MONTHS.between(YearMonth.from(first), YearMonth.from(last)) + 1;
                if (first.isBefore(last) && months >= 2 && months <= calendarMonths && calendarMonths <= 60
                        && position.signum() >= 0 && position.compareTo(BigDecimal.ONE) <= 0) {
                    ranges.put(code, new Range(first, last, months, position));
                }
            } catch (JSONException | DateTimeException | NumberFormatException error) {
                // A malformed series leaves the other symbols and the daily screen usable.
            }
        }
        return new JpxHistoryReference(Map.copyOf(ranges));
    }

    void appendHtml(StringBuilder message, String code, LocalDate session) {
        var range = byCode.get(code);
        if (range == null || range.last().isAfter(session)) return;
        var percent = range.position().movePointRight(2).stripTrailingZeros().toPlainString();
        message.append("<br>月次終値レンジ内の位置 ").append(percent).append("%")
                .append("（下限0%・上限100%）")
                .append("<br>").append(range.first()).append("〜").append(range.last())
                .append(" · ").append(range.months()).append("か月分 · 株式分割・併合調整済み");
    }
}
