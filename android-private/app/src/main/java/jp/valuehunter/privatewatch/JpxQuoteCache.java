package jp.valuehunter.privatewatch;

import android.util.AtomicFile;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/** Stores parsed JPX reports privately across process restarts. */
final class JpxQuoteCache {
    private static final int MAX_BYTES = 2_000_000;
    private static final int RETAIN_REPORTS = 4;
    private static final Pattern PRICE = Pattern.compile("[0-9]{1,16}(?:\\.[0-9]{1,8})?");

    private JpxQuoteCache() {}

    static synchronized JSONObject read(AtomicFile file) {
        try (var input = file.openRead()) {
            var output = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            while (output.size() <= MAX_BYTES) {
                int count = input.read(buffer, 0, Math.min(buffer.length, MAX_BYTES + 1 - output.size()));
                if (count < 0) break;
                output.write(buffer, 0, count);
            }
            byte[] content = output.toByteArray();
            if (content.length <= MAX_BYTES) return new JSONObject(new String(content, StandardCharsets.UTF_8));
        } catch (IOException | JSONException unavailable) {
            // A missing or broken cache can be rebuilt from the official PDFs.
        }
        return new JSONObject();
    }

    static synchronized void save(AtomicFile file, JpxDailyCheck.Report report) {
        if (report.edition().isEmpty() || report.universe() == null) return;
        try {
            var reports = read(file);
            reports.put(report.date().toString(), encode(report));
            var dates = new ArrayList<String>();
            reports.keys().forEachRemaining(dates::add);
            dates.sort(Comparator.reverseOrder());
            for (int i = RETAIN_REPORTS; i < dates.size(); i++) reports.remove(dates.get(i));
            if (reports.toString().getBytes(StandardCharsets.UTF_8).length <= MAX_BYTES)
                UsDailyWorker.writeSnapshot(file, reports);
        } catch (IOException | JSONException unavailable) {
            // The original parsed report remains available in this run.
        }
    }

    static JSONObject encode(JpxDailyCheck.Report report) throws JSONException {
        var rows = new JSONArray();
        for (var row : report.quotes().entrySet()) {
            rows.put(new JSONArray().put(row.getKey()).put(price(row.getValue().morning()))
                    .put(price(row.getValue().afternoon())));
        }
        String payload = new JSONObject().put("day", report.date().toString()).put("edition", report.edition())
                .put("universe", universeKey(report.universe())).put("rows", rows)
                .put("ambiguous", new JSONArray(report.ambiguous())).toString();
        return new JSONObject().put("payload", payload).put("sha256", sha(payload));
    }

    static JpxDailyCheck.Report restore(JSONObject saved, LocalDate day, String source,
                                        JpxStockUniverse universe, JpxDailyCheck.Edition edition) {
        if (saved == null || !edition.exists() || edition.version().isEmpty()) return null;
        try {
            String payload = saved.getString("payload");
            if (!sha(payload).equals(saved.optString("sha256"))) return null;
            var data = new JSONObject(payload);
            if (!day.toString().equals(data.getString("day")) || !edition.version().equals(data.getString("edition"))
                    || !universeKey(universe).equals(data.getString("universe"))) return null;
            var rows = data.getJSONArray("rows");
            var conflicts = data.getJSONArray("ambiguous");
            if (rows.length() + conflicts.length() > universe.codes().size()) return null;
            var quotes = new HashMap<String, JpxCloseTable.Sessions>();
            for (int i = 0; i < rows.length(); i++) {
                var row = rows.getJSONArray(i);
                if (row.length() != 3) return null;
                String code = row.getString(0);
                if (!universe.codes().contains(code) || quotes.put(code,
                        new JpxCloseTable.Sessions(value(row, 1), value(row, 2))) != null) return null;
            }
            var ambiguous = new HashSet<String>();
            for (int i = 0; i < conflicts.length(); i++) {
                String code = conflicts.getString(i);
                if (!universe.codes().contains(code) || quotes.containsKey(code) || !ambiguous.add(code)) return null;
            }
            if (!JpxDailyCheck.hasUsableClose(quotes, ambiguous)) return null;
            return new JpxDailyCheck.Report(day, source, Map.copyOf(quotes), Set.copyOf(ambiguous),
                    edition.version(), universe);
        } catch (JSONException | IllegalArgumentException invalid) {
            return null;
        }
    }

    private static Object price(BigDecimal price) {
        return price == null ? JSONObject.NULL : price.toPlainString();
    }

    private static BigDecimal value(JSONArray row, int index) throws JSONException {
        if (row.isNull(index)) return null;
        String price = row.getString(index);
        if (!PRICE.matcher(price).matches()) throw new JSONException("Invalid cached JPX price");
        return new BigDecimal(price);
    }

    private static String universeKey(JpxStockUniverse universe) {
        return sha(universe.asOf() + "\n" + String.join("\n", universe.codes().stream().sorted().collect(Collectors.toUnmodifiableList())));
    }

    private static String sha(String text) {
        return UsReferenceAlerts.sha256(text.getBytes(StandardCharsets.UTF_8));
    }
}
