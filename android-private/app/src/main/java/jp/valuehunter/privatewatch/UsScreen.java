package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Iterator;

final class UsScreen {
    // IBM FY2025 10-K and September 2026 10-Q, verified in market-research-v315.json.
    static final String FILING = "https://www.sec.gov/Archives/edgar/data/51143/000005114326000095/ibm-20260930.htm";
    static final LocalDate SHARES_DATE = LocalDate.of(2026, 9, 30);
    private static final LocalDate FILED = LocalDate.of(2026, 10, 22);
    private static final long SHARES = 945_120_805;
    private static final long TTM_PROFIT = 10_593_000_000L + 5_571_000_000L - 4_993_000_000L;
    private static final long PARENT_EQUITY = 35_537_000_000L;

    record Close(LocalDate date, double usd) {}
    record Fx(LocalDate date, double yenPerDollar) {}
    record Trial(int quantity, double yen, double per, double pbr) {
        boolean qualifies() {
            return yen <= JapanScreen.BUDGET && per <= JapanScreen.MAX_PER && pbr <= JapanScreen.MAX_PBR;
        }
    }

    static Close readClose(JSONObject payload, LocalDate latestAllowed) throws JSONException {
        var metadata = payload.optJSONObject("Meta Data");
        var series = payload.optJSONObject("Time Series (Daily)");
        if (metadata == null || !"IBM".equals(metadata.optString("2. Symbol")) || series == null) {
            throw new JSONException("IBMの日足を取得できなかった。キーと利用上限を確認");
        }
        LocalDate latest = null;
        for (Iterator<String> keys = series.keys(); keys.hasNext();) {
            LocalDate date = date(keys.next());
            if (!date.isAfter(latestAllowed) && (latest == null || date.isAfter(latest))) latest = date;
        }
        if (latest == null || latest.isBefore(latestAllowed.minusDays(7))) {
            throw new JSONException("直近のIBM終値が見つからない");
        }
        return new Close(latest, positive(series.getJSONObject(latest.toString()).optDouble("4. close")));
    }

    static Fx readFx(JSONArray payload, LocalDate closeDate) throws JSONException {
        return readFx(payload, closeDate, "USD");
    }

    static Fx readFx(JSONArray payload, LocalDate closeDate, String base) throws JSONException {
        Fx latest = null;
        for (int i = 0; i < payload.length(); i++) {
            var row = payload.getJSONObject(i);
            if (!base.equals(row.optString("base")) || !"JPY".equals(row.optString("quote"))) continue;
            LocalDate date = date(row.getString("date"));
            if (date.isAfter(closeDate) || date.isBefore(closeDate.minusDays(4))) continue;
            if (latest == null || date.isAfter(latest.date())) latest = new Fx(date, positive(row.optDouble("rate")));
        }
        if (latest == null) throw new JSONException("株価基準日までの円換算レートが見つからない");
        return latest;
    }

    static Trial trial(Close close, Fx fx) {
        // The filing date has no verified release time. Only use it from the following date.
        if (!close.date().isAfter(FILED) || close.date().isAfter(SHARES_DATE.plusDays(150))) return null;
        double yen = close.usd() * fx.yenPerDollar();
        int quantity = yen <= JapanScreen.BUDGET / 100.0 ? 100 : 1;
        double cap = close.usd() * SHARES;
        return new Trial(quantity, yen * quantity, cap / TTM_PROFIT, cap / PARENT_EQUITY);
    }

    static boolean shouldAlert(boolean hasBaseline, boolean previouslyQualified, boolean qualifies) {
        return hasBaseline && !previouslyQualified && qualifies;
    }

    private static LocalDate date(String value) throws JSONException {
        try {
            return LocalDate.parse(value);
        } catch (DateTimeParseException error) {
            throw new JSONException("取得データに不正な日付がある");
        }
    }

    private static double positive(double value) throws JSONException {
        if (!Double.isFinite(value) || value <= 0) throw new JSONException("終値か為替レートが不正");
        return value;
    }
}
