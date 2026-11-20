package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

record JpxRapidEvidence(String revision, Map<Interval, Set<String>> exclusions) {
    private static final String ONLINE = "https://raw.githubusercontent.com/osawamas/value-hunter-ai/main/"
            + "android-private/app/src/main/assets/jpx-rapid-rights.json";
    private static final String OFFICIAL = "https://www\\.jpx\\.co\\.jp/listing/others/ex-rights/";

    record Interval(LocalDate previous, LocalDate latest) {}

    static JpxRapidEvidence unavailable() {
        return new JpxRapidEvidence("unavailable", Map.of());
    }

    static JpxRapidEvidence refresh() {
        try {
            return parse(UsScanWorker.get(ONLINE, null));
        } catch (IOException | JSONException | DateTimeParseException ignored) {
            return unavailable();
        }
    }

    static JpxRapidEvidence parse(String body) throws JSONException {
        byte[] content = body.getBytes(StandardCharsets.UTF_8);
        if (content.length > 128_000) throw new JSONException("JPX rapid evidence too large");
        var entries = new JSONObject(body).getJSONArray("intervals");
        if (entries.length() < 1 || entries.length() > 7) throw new JSONException("Unexpected JPX interval count");
        var intervals = new HashMap<Interval, Set<String>>();
        for (int index = 0; index < entries.length(); index++) {
            var entry = entries.getJSONObject(index);
            var previous = LocalDate.parse(entry.getString("previousDay"));
            var latest = LocalDate.parse(entry.getString("latestDay"));
            if (!previous.isBefore(latest) || latest.isAfter(previous.plusDays(7)))
                throw new JSONException("Invalid JPX rapid interval");
            var sources = entry.getJSONObject("sources");
            if (sources.length() != 2) throw new JSONException("Both JPX editions are required");
            verifySource(sources.getJSONObject(previous.toString()), previous);
            verifySource(sources.getJSONObject(latest.toString()), latest);
            var codes = entry.getJSONArray("excludedCodes");
            if (codes.length() > 5_000) throw new JSONException("Too many JPX exclusion codes");
            var excluded = new HashSet<String>();
            for (int i = 0; i < codes.length(); i++) {
                String code = codes.getString(i);
                if (!code.matches("[0-9][0-9A-Z]{3}") || !excluded.add(code))
                    throw new JSONException("Invalid or duplicate JPX exclusion code");
            }
            if (intervals.putIfAbsent(new Interval(previous, latest), Set.copyOf(excluded)) != null)
                throw new JSONException("Duplicate JPX rapid interval");
        }
        return new JpxRapidEvidence(UsReferenceAlerts.sha256(content), Map.copyOf(intervals));
    }

    Set<String> excluded(LocalDate previous, LocalDate latest) {
        return exclusions.get(new Interval(previous, latest));
    }

    private static void verifySource(JSONObject source, LocalDate day) throws JSONException {
        String filename = day.format(java.time.format.DateTimeFormatter.BASIC_ISO_DATE);
        if (!source.getString("url").matches(OFFICIAL + "[A-Za-z0-9_-]+/" + filename + "\\.xls")
                || !source.getString("sha256").matches("[0-9a-f]{64}"))
            throw new JSONException("Invalid JPX workbook provenance");
    }
}
