package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.DateTimeException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

final class SgShareLedger {
    static final String URL = "https://raw.githubusercontent.com/osawamas/value-hunter-ai/main/docs/data/android-s63-shares.json";

    record Disclosure(long shares, String source, OffsetDateTime disclosedAt) {}

    static JSONObject readAsset(InputStream input) throws IOException, JSONException {
        try (var reader = new InputStreamReader(input, StandardCharsets.UTF_8)) {
            var contents = new StringBuilder();
            var buffer = new char[4096];
            int read;
            while ((read = reader.read(buffer)) != -1) {
                contents.append(buffer, 0, read);
            }
            return new JSONObject(contents.toString());
        }
    }

    static Disclosure read(JSONObject payload, LocalDate session, Instant checkedAt) throws JSONException {
        if (payload.getInt("schema") != 1 || !"S63".equals(payload.getString("symbol"))) {
            throw new JSONException("Unexpected S63 share ledger");
        }
        var rows = payload.getJSONArray("records");
        Disclosure disclosure = null;
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            if (!session.toString().equals(row.getString("date"))) continue;
            OffsetDateTime disclosed;
            try {
                disclosed = OffsetDateTime.parse(row.getString("disclosed_at"));
                if (!disclosed.getOffset().equals(ZoneOffset.ofHours(8))
                        || disclosed.toLocalDate().isBefore(session)) {
                    throw new JSONException("S63 disclosure date mismatch");
                }
            } catch (DateTimeException error) {
                throw new JSONException("Invalid S63 disclosure time");
            }
            long count;
            try {
                count = Long.parseLong(row.get("shares").toString());
            } catch (NumberFormatException error) {
                throw new JSONException("Invalid share count");
            }
            String source = row.getString("source");
            if (disclosure != null || count <= 0 || count > 10_000_000_000L
                    || !source.matches(
                            "https://links[.]sgx[.]com/1[.]0[.]0/corporate-announcements/[A-Z0-9]+/[a-f0-9]{64}")) {
                throw new JSONException("Invalid or conflicting S63 share evidence");
            }
            disclosure = new Disclosure(count, source, disclosed);
        }
        return disclosure != null && !disclosure.disclosedAt().toInstant().isAfter(checkedAt)
                ? disclosure : null;
    }
}
