package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.function.BooleanSupplier;

/** A local forward test of delivered US financial alerts against the IWV ETF. */
final class UsAlertOutcomes {
    static final String BENCHMARK = "IWV";
    private static final int RETENTION_DAYS = 120;
    private static final int MAX_EVENTS = 500;
    static final int MAX_BATCH = 32;
    private static final String WAITING = "waiting";
    private static final String MISSING = "missing";
    private static final String COMPLETE = "complete";

    record Window(LocalDate entry, LocalDate exit) {}
    record Prices(double entry, double exit) {
        double percent() { return 100 * (exit / entry - 1); }
    }

    private UsAlertOutcomes() {}

    static Window window(long postedAt) {
        var date = Instant.ofEpochMilli(postedAt).atZone(UsDailyCloses.NEW_YORK).toLocalDate();
        LocalDate entry = advance(date, 1);
        return new Window(entry, advance(entry, 20));
    }

    private static LocalDate advance(LocalDate date, int sessions) {
        while (sessions > 0) {
            date = date.plusDays(1);
            if (UsDailyCloses.tradingDay(date)) sessions--;
        }
        return date;
    }

    static void record(Context context, int id, String title, String detail, Map<String, String> signals) {
        long now = System.currentTimeMillis();
        try {
            String receipt = id + "-" + ScanWorker.notificationReceipt(title, detail);
            for (var entry : NotificationHistory.recent(NotificationHistory.file(context), now)) {
                if (receipt.equals(entry.receipt())) {
                    add(file(context), entry, signals, now);
                    return;
                }
            }
        } catch (IOException | JSONException e) {
            DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, "米国株の試験記録を保存できず");
        }
    }

    private static AtomicFile file(Context context) {
        return new AtomicFile(new File(context.getNoBackupFilesDir(), "us-alert-outcomes-v1.json"));
    }

    static synchronized void add(AtomicFile file, NotificationHistory.Entry alert, Map<String, String> signals,
                                 long now) throws IOException, JSONException {
        var ledger = read(file);
        var dates = window(alert.postedAt());
        for (var signal : signals.entrySet()) {
            String symbol = signal.getKey();
            if (!validSymbol(symbol)) continue;
            String key = alert.receipt() + ":" + symbol;
            if (ledger.has(key)) continue;
            ledger.put(key, new JSONObject().put("symbol", symbol).put("rule", signal.getValue())
                    .put("at", alert.postedAt()).put("entry", dates.entry().toString())
                    .put("exit", dates.exit().toString()).put("status", WAITING));
        }
        var keys = keys(ledger);
        keys.sort(java.util.Comparator.comparingLong((String key) -> ledger.optJSONObject(key).optLong("at")).reversed()
                .thenComparing(java.util.Comparator.naturalOrder()));
        for (int i = 0; i < keys.size(); i++) {
            String key = keys.get(i);
            if (i >= MAX_EVENTS || now - ledger.getJSONObject(key).getLong("at")
                    >= java.util.concurrent.TimeUnit.DAYS.toMillis(RETENTION_DAYS)) ledger.remove(key);
        }
        UsDailyWorker.writeSnapshot(file, ledger);
    }

    static void update(Context context, LocalDate latestClose, BooleanSupplier stopped) {
        if (stopped.getAsBoolean()) return;
        try {
            evaluate(file(context), latestClose, stopped, address -> UsDailyWorker.fetch(address, ""));
        } catch (IOException | JSONException | java.time.format.DateTimeParseException e) {
            DiagnosticLog.record(context, DiagnosticLog.Area.US_CLOSE, "米国株の試験比較を取得できず · 次回確認");
        }
    }

    static void evaluate(AtomicFile file, LocalDate latestClose, BooleanSupplier stopped, UsDoltCloses.Download download)
            throws IOException, JSONException {
        JSONObject batch = new JSONObject();
        Window range = null;
        var ledger = read(file);
        var symbols = new HashSet<String>();
        symbols.add(BENCHMARK);
        for (String key : keys(ledger)) {
            var row = ledger.getJSONObject(key);
            if (!WAITING.equals(row.optString("status")) || latestClose.toString().equals(row.optString("checked"))) continue;
            var exit = LocalDate.parse(row.getString("exit"));
            if (exit.isAfter(latestClose)) continue;
            var candidate = new Window(LocalDate.parse(row.getString("entry")), exit);
            if (range == null) range = candidate;
            if (!range.equals(candidate)) continue;
            symbols.add(row.getString("symbol"));
            batch.put(key, row);
            if (symbols.size() >= MAX_BATCH) break;
        }
        if (range == null || stopped.getAsBoolean()) return;
        var prices = UsDoltCloses.outcomePrices(range, symbols, download);
        if (!stopped.getAsBoolean()) saveResults(file, latestClose, range, batch, prices);
    }

    private static synchronized void saveResults(AtomicFile file, LocalDate latestClose, Window range, JSONObject batch,
                                                 Map<String, Prices> prices) throws IOException, JSONException {
        var latest = read(file);
        var benchmark = prices.get(BENCHMARK);
        for (String key : keys(batch)) {
            var row = latest.optJSONObject(key);
            if (row == null || !WAITING.equals(row.optString("status"))) continue;
            var stock = prices.get(row.getString("symbol"));
            row.put("checked", latestClose.toString());
            if (stock != null && benchmark != null) {
                row.put("status", COMPLETE).put("stockReturn", stock.percent())
                        .put("benchmarkReturn", benchmark.percent());
            } else if (!latestClose.isBefore(range.exit().plusDays(7))) {
                row.put("status", MISSING);
            }
        }
        UsDailyWorker.writeSnapshot(file, latest);
    }

    private static synchronized JSONObject read(AtomicFile file) throws IOException, JSONException {
        try (var input = file.openRead()) {
            var output = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            for (int count; (count = input.read(buffer)) != -1;) {
                if (output.size() + count > 512_000) throw new IOException("US alert pilot ledger too large");
                output.write(buffer, 0, count);
            }
            return new JSONObject(new String(output.toByteArray(), StandardCharsets.UTF_8));
        } catch (FileNotFoundException absent) {
            return new JSONObject();
        }
    }

    static boolean validSymbol(String symbol) {
        return symbol.matches("[A-Z0-9.$+^=/_-]{1,24}");
    }

    private static ArrayList<String> keys(JSONObject object) {
        var keys = new ArrayList<String>();
        object.keys().forEachRemaining(keys::add);
        return keys;
    }

    static String report(Context context) throws IOException, JSONException {
        return report(file(context));
    }

    static String report(AtomicFile file) throws IOException, JSONException {
        var ledger = read(file);
        var keys = keys(ledger);
        keys.sort(java.util.Comparator.comparingLong((String key) -> ledger.optJSONObject(key).optLong("at")).reversed());
        if (keys.isEmpty()) return "これから届く米国株の財務条件・割安メーターの通知を記録する。";
        var report = new StringBuilder("通知後の次の取引日の終値から、20取引日後の終値まで。ドル建て・配当と手数料は含めない。\n"
                + "比較対象はRussell 3000連動ETFのIWV。分割・終値欠けなどは集計対象外。\n\n");
        int completed = 0;
        int outperformed = 0;
        int excluded = 0;
        double totalExcess = 0;
        for (String key : keys) {
            var row = ledger.getJSONObject(key);
            if (MISSING.equals(row.getString("status"))) excluded++;
            if (!COMPLETE.equals(row.getString("status"))) continue;
            double excess = row.getDouble("stockReturn") - row.getDouble("benchmarkReturn");
            totalExcess += excess;
            completed++;
            if (excess > 0) outperformed++;
        }
        report.append("計測済み ").append(completed).append("件 · 待ち ").append(keys.size() - completed - excluded)
                .append("件 · 集計対象外 ").append(excluded).append("件\n");
        if (completed > 0) report.append(String.format(Locale.JAPAN, "IWVを上回った通知 %d/%d件 · 平均差 %+.2fポイント\n",
                outperformed, completed, totalExcess / completed));
        report.append("\n直近の通知（最大50件）\n");
        for (int i = 0; i < Math.min(keys.size(), 50); i++) {
            var row = ledger.getJSONObject(keys.get(i));
            report.append("\n").append(row.getString("symbol")).append(" · ").append(row.getString("rule"))
                    .append("\n").append(row.getString("entry")).append(" → ").append(row.getString("exit")).append("\n");
            switch (row.getString("status")) {
                case COMPLETE -> {
                    double stock = row.getDouble("stockReturn");
                    double index = row.getDouble("benchmarkReturn");
                    report.append(String.format(Locale.JAPAN, "銘柄 %+.2f%% · IWV %+.2f%% · 差 %+.2fポイント\n",
                            stock, index, stock - index));
                }
                case MISSING -> report.append("集計対象外（終値欠け・分割など）\n");
                default -> report.append("計測待ち\n");
            }
        }
        return report.toString();
    }
}
