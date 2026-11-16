package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

final class SgShareLedger {
    static final String URL = "https://raw.githubusercontent.com/osawamas/value-hunter-ai/main/docs/data/android-s63-shares.json";

    static long readShares(JSONObject payload, LocalDate session) throws JSONException {
        if (payload.getInt("schema") != 1 || !"S63".equals(payload.getString("symbol"))) {
            throw new JSONException("Unexpected S63 share ledger");
        }
        var rows = payload.getJSONArray("records");
        long shares = 0;
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            if (!session.toString().equals(row.getString("date"))) continue;
            try {
                var disclosed = OffsetDateTime.parse(row.getString("disclosed_at"));
                if (!disclosed.getOffset().equals(ZoneOffset.ofHours(8))
                        || !disclosed.toLocalDate().equals(session)) {
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
            if (shares != 0 || count <= 0 || count > 10_000_000_000L
                    || !row.getString("source").matches(
                            "https://links[.]sgx[.]com/1[.]0[.]0/corporate-announcements/[A-Z0-9]+/[a-f0-9]{64}")) {
                throw new JSONException("Invalid or conflicting S63 share evidence");
            }
            shares = count;
        }
        return shares;
    }
}
