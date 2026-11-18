package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.Locale;
import java.util.zip.ZipFile;

/** Desktop entry point using the same SEC-period checks as Android. */
public final class UsBulkLedger {
    private static final int MAX_FACTS_BYTES = 16 * 1024 * 1024;

    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 2) throw new IllegalArgumentException("Expected companyfacts ZIP and trading date");
        var day = LocalDate.parse(arguments[1]);
        var universe = new JSONObject(new String(System.in.readAllBytes(), StandardCharsets.UTF_8));
        var rows = universe.getJSONArray("listings");
        if (rows.length() > 12_000) throw new IllegalArgumentException("Unexpected listing count");
        try (var archive = new ZipFile(arguments[0])) {
            for (int offset = 0; offset < rows.length(); offset++) {
                var row = rows.getJSONObject(offset);
                if (row.has("hold")) continue;
                int cik = row.getInt("cik");
                String file = String.format(Locale.ROOT, "CIK%010d.json", cik);
                var entry = archive.getEntry(file);
                if (entry == null) {
                    row.put("hold", "no_companyfacts");
                    continue;
                }
                if (entry.getSize() <= 0 || entry.getSize() > MAX_FACTS_BYTES) {
                    row.put("hold", "companyfacts_size");
                    continue;
                }
                UsFinancialFacts.Facts facts;
                try (var input = archive.getInputStream(entry)) {
                    byte[] bytes = input.readNBytes(MAX_FACTS_BYTES + 1);
                    if (bytes.length != entry.getSize()) throw new IOException("Incomplete SEC ZIP entry");
                    var payload = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
                    if (payload.optJSONObject("facts") == null
                            || payload.getJSONObject("facts").optJSONObject("us-gaap") == null) {
                        row.put("hold", "no_us_gaap_facts");
                        continue;
                    }
                    if (!UsFinancialFacts.matchesIssuer(payload, cik)) {
                        row.put("hold", "companyfacts_issuer_mismatch");
                        continue;
                    }
                    facts = UsFinancialFacts.read(payload, cik, day);
                } catch (JSONException invalid) {
                    row.put("hold", "invalid_companyfacts");
                    continue;
                }
                if (facts == null) {
                    row.put("hold", "financial_period_or_class_unconfirmed");
                } else {
                    row.put("filed", facts.filed().toString()).put("share_date", facts.shareDate().toString())
                            .put("shares", facts.shares()).put("profit", facts.profit()).put("equity", facts.equity())
                            .put("accession", facts.accession()).put("shares_basis", facts.sharesBasis())
                            .put("reconciled_parent_amounts", facts.reconciledParentAmounts());
                }
            }
        }
        System.out.println(universe);
    }
}
