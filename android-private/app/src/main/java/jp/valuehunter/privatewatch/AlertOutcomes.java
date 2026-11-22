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
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;
import java.util.function.BooleanSupplier;

/** On-device forward measurements of delivered financial alerts against a market ETF. */
final class AlertOutcomes {
    private static final int RETENTION_DAYS = 120;
    private static final int MAX_EVENTS = 500;
    static final int MAX_BATCH = 32;
    private static final String WAITING = "waiting";
    private static final String MISSING = "missing";
    private static final String COMPLETE = "complete";

    enum Market {
        US("us", "米国株", "ドル", "IWV", "Russell 3000", UsDailyCloses.NEW_YORK, 7, MAX_BATCH),
        JPX("jpx", "東証株", "円", "1306", "TOPIX", ZoneId.of("Asia/Tokyo"), 45, MAX_EVENTS + 1);

        final String filePrefix;
        final String label;
        final String currency;
        final String benchmark;
        final String indexName;
        final ZoneId zone;
        final int missingGraceDays;
        final int batchSize;

        Market(String filePrefix, String label, String currency, String benchmark, String indexName, ZoneId zone,
               int missingGraceDays, int batchSize) {
            this.filePrefix = filePrefix;
            this.label = label;
            this.currency = currency;
            this.benchmark = benchmark;
            this.indexName = indexName;
            this.zone = zone;
            this.missingGraceDays = missingGraceDays;
            this.batchSize = batchSize;
        }
    }

    @FunctionalInterface
    interface PriceLoader {
        Map<String, Prices> load(Window range, Set<String> symbols) throws IOException, JSONException;
    }

    record Window(LocalDate entry, LocalDate exit) {}
    record Prices(double entry, double exit) {
        double percent() { return 100 * (exit / entry - 1); }
    }

    private AlertOutcomes() {}

    static Window window(Market market, long postedAt) {
        var date = Instant.ofEpochMilli(postedAt).atZone(market.zone).toLocalDate();
        LocalDate entry = advance(market, date, 1);
        if (entry == null) return null;
        LocalDate exit = advance(market, entry, 20);
        return exit == null ? null : new Window(entry, exit);
    }

    private static LocalDate advance(Market market, LocalDate date, int sessions) {
        while (sessions > 0) {
            date = date.plusDays(1);
            if (market == Market.US) {
                if (UsDailyCloses.tradingDay(date)) sessions--;
            } else {
                var trading = JpxTradingDays.onOrBefore(date);
                if (trading == null) return null;
                if (trading.equals(date)) sessions--;
            }
        }
        return date;
    }

    static void record(Context context, Market market, int id, String title, String detail, Map<String, String> signals) {
        long now = System.currentTimeMillis();
        try {
            String receipt = id + "-" + ScanWorker.notificationReceipt(title, detail);
            for (var entry : NotificationHistory.recent(NotificationHistory.file(context), now)) {
                if (receipt.equals(entry.receipt())) {
                    add(file(context, market), market, entry, signals, now);
                    return;
                }
            }
        } catch (IOException | JSONException e) {
            DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, market.label + "の試験記録を保存できず");
        }
    }

    private static AtomicFile file(Context context, Market market) {
        return new AtomicFile(new File(context.getNoBackupFilesDir(), market.filePrefix + "-alert-outcomes-v1.json"));
    }

    static synchronized void add(AtomicFile file, Market market, NotificationHistory.Entry alert, Map<String, String> signals,
                                 long now) throws IOException, JSONException {
        var ledger = read(file);
        var dates = window(market, alert.postedAt());
        if (dates == null) return;
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

    static void update(Context context, Market market, LocalDate latestClose, BooleanSupplier stopped,
                       Predicate<Window> evidenceReady, PriceLoader prices) {
        if (latestClose == null || stopped.getAsBoolean()) return;
        try {
            evaluate(file(context, market), market, latestClose, stopped, evidenceReady, prices);
        } catch (IOException | JSONException | java.time.format.DateTimeParseException e) {
            var area = market == Market.US ? DiagnosticLog.Area.US_CLOSE : DiagnosticLog.Area.JPX;
            DiagnosticLog.record(context, area, market.label + "の試験比較を取得できず · 次回確認");
        }
    }

    static void evaluate(AtomicFile file, Market market, LocalDate latestClose, BooleanSupplier stopped,
                         Predicate<Window> evidenceReady, PriceLoader loader) throws IOException, JSONException {
        JSONObject batch = new JSONObject();
        Window range = null;
        var ledger = read(file);
        var symbols = new HashSet<String>();
        symbols.add(market.benchmark);
        var ordered = keys(ledger);
        ordered.sort(java.util.Comparator.comparing(key -> ledger.optJSONObject(key).optString("exit")));
        for (String key : ordered) {
            var row = ledger.getJSONObject(key);
            if (!WAITING.equals(row.optString("status")) || latestClose.toString().equals(row.optString("checked"))) continue;
            var exit = LocalDate.parse(row.getString("exit"));
            if (exit.isAfter(latestClose)) continue;
            var candidate = new Window(LocalDate.parse(row.getString("entry")), exit);
            if (range == null) {
                if (!evidenceReady.test(candidate) && latestClose.isBefore(exit.plusDays(market.missingGraceDays))) continue;
                range = candidate;
            }
            if (!range.equals(candidate)) continue;
            symbols.add(row.getString("symbol"));
            batch.put(key, row);
            if (symbols.size() >= market.batchSize) break;
        }
        if (range == null || stopped.getAsBoolean()) return;
        var prices = evidenceReady.test(range) ? loader.load(range, symbols) : Map.<String, Prices>of();
        if (!stopped.getAsBoolean()) saveResults(file, market, latestClose, range, batch, prices);
    }

    private static synchronized void saveResults(AtomicFile file, Market market, LocalDate latestClose, Window range, JSONObject batch,
                                                 Map<String, Prices> prices) throws IOException, JSONException {
        var latest = read(file);
        var benchmark = prices.get(market.benchmark);
        for (String key : keys(batch)) {
            var row = latest.optJSONObject(key);
            if (row == null || !WAITING.equals(row.optString("status"))) continue;
            var stock = prices.get(row.getString("symbol"));
            row.put("checked", latestClose.toString());
            if (stock != null && benchmark != null) {
                row.put("status", COMPLETE).put("stockReturn", stock.percent())
                        .put("benchmarkReturn", benchmark.percent());
            } else if (!latestClose.isBefore(range.exit().plusDays(market.missingGraceDays))) {
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

    static String report(Context context, Market market) throws IOException, JSONException {
        return report(file(context, market), market);
    }

    static String report(AtomicFile file, Market market) throws IOException, JSONException {
        var ledger = read(file);
        var keys = keys(ledger);
        keys.sort(java.util.Comparator.comparingLong((String key) -> ledger.optJSONObject(key).optLong("at")).reversed());
        if (keys.isEmpty()) return "これから届く" + market.label + "の財務条件・割安メーターの通知を記録する。";
        var report = new StringBuilder("通知後の次の取引日の終値から、20取引日後の終値まで。"
                + market.currency + "建て・配当と手数料は含めない。\n比較対象は"
                + market.indexName + "連動ETFの" + market.benchmark + "。分割・終値欠けなどは集計対象外。\n");
        if (market == Market.JPX) report.append("20取引日後も、分割・併合の月報が出るまで待つ場合がある。比較には当該2日の日報を取得する。\n");
        report.append("\n");
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
        if (completed > 0) report.append(String.format(Locale.JAPAN, "%sを上回った通知 %d/%d件 · 平均差 %+.2fポイント\n",
                market.benchmark, outperformed, completed, totalExcess / completed));
        report.append("\n直近の通知（最大50件）\n");
        for (int i = 0; i < Math.min(keys.size(), 50); i++) {
            var row = ledger.getJSONObject(keys.get(i));
            report.append("\n").append(row.getString("symbol")).append(" · ").append(row.getString("rule"))
                    .append("\n").append(row.getString("entry")).append(" → ").append(row.getString("exit")).append("\n");
            switch (row.getString("status")) {
                case COMPLETE -> {
                    double stock = row.getDouble("stockReturn");
                    double index = row.getDouble("benchmarkReturn");
                    report.append(String.format(Locale.JAPAN, "銘柄 %+.2f%% · %s %+.2f%% · 差 %+.2fポイント\n",
                            stock, market.benchmark, index, stock - index));
                }
                case MISSING -> report.append("集計対象外（終値欠け・分割など）\n");
                default -> report.append("計測待ち\n");
            }
        }
        return report.toString();
    }
}
