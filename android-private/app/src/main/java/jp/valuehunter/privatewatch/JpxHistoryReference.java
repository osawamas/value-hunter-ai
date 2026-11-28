package jp.valuehunter.privatewatch;

import android.content.Context;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;

import static java.nio.charset.StandardCharsets.UTF_8;

final class JpxHistoryReference {
    private static final String ASSET = "jpx-history.json";
    private static final int MAX_BYTES = 2_097_152;
    private static final JpxHistoryReference EMPTY = new JpxHistoryReference(Map.of());

    private record Bounds(BigDecimal low, BigDecimal high) {}

    private record Range(LocalDate first, LocalDate last, int months, BigDecimal position, Bounds bounds) {}

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
                    ranges.put(code, new Range(first, last, months, position, bounds(row)));
                }
            } catch (JSONException | DateTimeException | NumberFormatException error) {
                // A malformed series leaves the other symbols and the daily screen usable.
            }
        }
        return new JpxHistoryReference(Map.copyOf(ranges));
    }

    private static Bounds bounds(JSONObject row) {
        String lowText = row.optString("range_low");
        String highText = row.optString("range_high");
        String pattern = "[0-9]{1,16}(?:[.][0-9]{1,40})?";
        if (!lowText.matches(pattern) || !highText.matches(pattern)) return null;
        var low = new BigDecimal(lowText);
        var high = new BigDecimal(highText);
        return low.signum() > 0 && low.compareTo(high) < 0 ? new Bounds(low, high) : null;
    }

    ValueAlertMeter.Score corroborateEarnings(String code, LocalDate session, BigDecimal close,
            BigDecimal earningsPerShare, JpxShareRights rights) {
        var range = byCode.get(code);
        if (range == null || range.bounds() == null || range.months() != 60
                || !range.last().isBefore(session) || range.last().isBefore(session.minusDays(45))
                || !rights.holdReason(code, range.last(), session).isEmpty()
                || earningsPerShare.signum() <= 0 || close.signum() <= 0) return null;
        var bounds = range.bounds();
        var span = bounds.high().subtract(bounds.low());
        var reboundFloor = bounds.low().add(span.multiply(range.position().add(new BigDecimal("0.02"))));
        var lowerThird = bounds.low().add(span.multiply(new BigDecimal("0.33")));
        boolean supported = close.compareTo(reboundFloor) >= 0 && close.compareTo(lowerThird) <= 0
                && close.compareTo(earningsPerShare.multiply(BigDecimal.valueOf(10))) <= 0;
        return supported ? new ValueAlertMeter.Score(65, 1, 2) : null;
    }

    void appendHtml(StringBuilder message, String code, LocalDate session,
                    BigDecimal close, JpxShareRights rights) {
        var range = byCode.get(code);
        if (range == null || range.last().isAfter(session)) return;
        var percent = range.position().movePointRight(2).stripTrailingZeros().toPlainString();
        message.append("<br>月次終値レンジ内の位置 ").append(percent).append("%")
                .append("（下限0%・上限100%）")
                .append("<br>").append(range.first()).append("〜").append(range.last())
                .append(" · ").append(range.months()).append("か月分 · 株式分割・併合調整済み");
        var bounds = range.bounds();
        if (bounds == null) return;
        String holdReason = rights.holdReason(code, range.last(), session);
        if (!holdReason.isEmpty()) {
            message.append("<br>直近終値との比較は保留（").append(holdReason).append("）");
        } else if (close.compareTo(bounds.low()) < 0) {
            message.append("<br>直近終値は過去のレンジ下限を下回る");
        } else if (close.compareTo(bounds.high()) > 0) {
            message.append("<br>直近終値は過去のレンジ上限を上回る");
        } else {
            var current = close.subtract(bounds.low()).movePointRight(2)
                    .divide(bounds.high().subtract(bounds.low()), 1, RoundingMode.HALF_UP);
            message.append("<br>直近終値のレンジ位置 ").append(current.stripTrailingZeros().toPlainString())
                    .append("%（下限0%・上限100%）");
        }
    }
}
