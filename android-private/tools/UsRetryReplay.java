package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** Runs the app's date, issuer, valuation and notification checks against local historical inputs. */
public final class UsRetryReplay {
    record Stage(int closes, int facts, UsReferenceAlerts.Screen screen) {
        JSONObject counts() {
            return new JSONObject().put("closes", closes).put("financial_rows", facts)
                    .put("screened", screen.rows().size())
                    .put("candidates", screen.rows().values().stream().filter(UsReferenceAlerts.Observation::candidate).count());
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 3 && "--coverage".equals(args[0])) {
            byte[] quoteBytes = Files.readAllBytes(Path.of(args[1]));
            var quote = new JSONObject(new String(quoteBytes, StandardCharsets.UTF_8));
            byte[] checkpointBytes = Files.readAllBytes(Path.of(args[2]));
            var checkpoint = new JSONObject(new String(checkpointBytes, StandardCharsets.UTF_8));
            System.out.println(coverage(quote, checkpoint, UsReferenceAlerts.sha256(quoteBytes))
                    .put("checkpoint_sha256", UsReferenceAlerts.sha256(checkpointBytes))
                    .toString(2));
            return;
        }
        if (args.length != 5 || args[3].equals(args[4])) {
            throw new IllegalArgumentException("Usage: UsRetryReplay INPUT_DIR PRIOR_DATE DATE WITHHELD_CLOSE WITHHELD_FACTS");
        }
        var input = Path.of(args[0]);
        var prior = LocalDate.parse(args[1]);
        var day = LocalDate.parse(args[2]);
        if (!prior.isBefore(day)) throw new IllegalArgumentException("Comparison day must come first");
        String withheldClose = args[3];
        String withheldFacts = args[4];
        var bars = response(input, "closes.json").getJSONArray("rows");
        var closeByDay = new HashMap<LocalDate, Map<String, BigDecimal>>();
        closeByDay.put(prior, closes(bars, prior));
        closeByDay.put(day, closes(bars, day));
        var nyse = UsMarketCoverage.directory(Files.readString(input.resolve("nyse.txt")), false);
        var nasdaq = UsMarketCoverage.directory(Files.readString(input.resolve("nasdaq.txt")), true);
        var dir = json(input, "sec.json");
        var targets = UsDeviceFinancials.targets(nyse, nasdaq, dir, closeByDay.get(day).keySet());
        var issuers = new LinkedHashMap<String, JSONObject>();
        for (int index = 0; index < targets.length(); index++) {
            var target = targets.getJSONObject(index);
            issuers.put(target.getString("symbol"), target);
        }
        if (!issuers.keySet().containsAll(Set.of(withheldClose, withheldFacts))) {
            throw new IllegalArgumentException("Withheld tickers must match both directories. Eligible sample: " + issuers.keySet());
        }
        var rates = new JSONArray(Files.readString(input.resolve("fx.json")));
        var splitRows = response(input, "splits.json").getJSONArray("rows");
        var splits = new HashMap<String, LocalDate>();
        for (int index = 0; index < splitRows.length(); index++) {
            var row = splitRows.getJSONObject(index);
            splits.put(row.getString("symbol"), LocalDate.parse(row.getString("split_date")));
        }
        var priorQuotes = filteredCloses(closeByDay.get(prior), issuers.keySet());
        var stagePrior = screen(prior, priorQuotes, facts(input, issuers, prior, priorQuotes.keySet()), rates, splits);
        var quotes = filteredCloses(closeByDay.get(day), issuers.keySet());
        quotes.remove(withheldClose);
        var firstTargets = new java.util.HashSet<>(quotes.keySet());
        firstTargets.remove(withheldFacts);
        var firstFacts = facts(input, issuers, day, firstTargets);
        var before = screen(day, quotes, firstFacts, rates, splits);

        var reply = response(input, "supplement.json");
        var supplement = UsDoltCloses.supplement(day, Set.of(withheldClose), ignored -> reply);
        if (supplement.length() > 0) quotes.putAll(UsDeviceFinancials.prices(supplement));
        var recoveryTargets = new java.util.HashSet<>(Set.of(withheldClose, withheldFacts));
        recoveryTargets.retainAll(quotes.keySet());
        var recovered = facts(input, issuers, day, recoveryTargets, "-retry.json");
        for (int index = 0; index < recovered.length(); index++) firstFacts.put(recovered.getJSONObject(index));
        var after = screen(day, quotes, firstFacts, rates, splits);
        var nonPositive = new java.util.TreeSet<String>();
        for (int index = 0; index < firstFacts.length(); index++) {
            var row = firstFacts.getJSONObject(index);
            if (UsDeviceFinancials.nonPositiveFinancials(row)) nonPositive.add(row.getString("symbol"));
        }
        var initialAlerts = UsReferenceAlerts.entrantRows(stagePrior.screen(), before.screen(), Set.of());
        var retryAlerts = UsReferenceAlerts.entrantRows(stagePrior.screen(), after.screen(), initialAlerts.keySet());
        System.out.println(new JSONObject().put("date", day.toString()).put("comparison_date", prior.toString())
                .put("listing_snapshot", nyse.date().toString()).put("eligible_sample", issuers.size())
                .put("withheld_close", withheldClose).put("withheld_facts", withheldFacts)
                .put("before", before.counts()).put("after", after.counts())
                .put("additional_screened", after.screen().rows().size() - before.screen().rows().size())
                .put("quote_retry_targets", 1).put("issuer_retry_targets", recoveryTargets.size())
                .put("initial_alert_candidates", initialAlerts.size()).put("additional_alert_candidates", retryAlerts.size())
                .put("nonpositive_financials", nonPositive)
                .put("screening_holds_after_retry", quotes.keySet().stream()
                        .filter(symbol -> !after.screen().rows().containsKey(symbol)).sorted().toList()).toString(2));
    }

    static JSONObject coverage(JSONObject quote, JSONObject checkpoint, String hash) {
        var day = LocalDate.parse(quote.getString("trading_date_et"));
        String source = quote.getString("source");
        if (!UsDailyCloses.tradingDay(day) || !day.toString().equals(checkpoint.getString("day"))
                || !hash.equals(checkpoint.getString("hash")) || checkpoint.getInt("cursor")
                != checkpoint.getJSONArray("targets").length()) {
            throw new IllegalArgumentException("Expected matching closes and a completed SEC pass");
        }
        var evidence = checkpoint.getJSONObject("valuation_evidence");
        double rate = evidence.getDouble("fx_rate");
        if (evidence.getInt("split_window_version") != 2 || !Double.isFinite(rate) || rate <= 0) {
            throw new IllegalArgumentException("Expected verified split window and FX");
        }
        var splits = new HashMap<String, LocalDate>();
        var splitDates = evidence.getJSONObject("splits");
        for (var symbol : splitDates.keySet()) splits.put(symbol, LocalDate.parse(splitDates.getString(symbol)));

        return UsDeviceFinancials.scopedAssessment(day, source, hash, checkpoint,
                UsDeviceFinancials.prices(quote.getJSONArray("closes")), new UsScreen.Fx(day, rate), splits);
    }

    static Map<String, BigDecimal> closes(JSONArray bars, LocalDate day) throws JSONException {
        var rows = new JSONArray();
        for (int index = 0; index < bars.length(); index++) {
            var row = bars.getJSONObject(index);
            if (day.toString().equals(row.getString("trading_date"))) {
                rows.put(new JSONObject().put("symbol", row.getString("symbol")).put("close_usd", row.get("close")));
            }
        }
        return UsDeviceFinancials.prices(rows);
    }

    private static HashMap<String, BigDecimal> filteredCloses(Map<String, BigDecimal> prices, Set<String> symbols) {
        var chosen = new HashMap<>(prices);
        chosen.keySet().retainAll(symbols);
        return chosen;
    }

    private static JSONArray facts(Path input, Map<String, JSONObject> targets, LocalDate day, Set<String> requested)
            throws IOException, JSONException {
        return facts(input, targets, day, requested, ".json");
    }

    private static JSONArray facts(Path input, Map<String, JSONObject> targets, LocalDate day,
                                  Set<String> requested, String suffix) throws IOException, JSONException {
        var rows = new JSONArray();
        for (var symbol : requested) {
            var issuer = input.resolve(symbol + suffix);
            if (!Files.isRegularFile(issuer) && ".json".equals(suffix)) continue;
            var row = UsDeviceFinancials.financialRow(targets.get(symbol), new JSONObject(Files.readString(issuer)), day);
            if (row != null) rows.put(row);
        }
        return rows;
    }

    static Stage screen(LocalDate day, Map<String, BigDecimal> prices, JSONArray facts, JSONArray rates,
                                Map<String, LocalDate> splits) throws JSONException {
        var fx = UsScreen.readFx(rates, day);
        if (!day.equals(fx.date())) throw new JSONException("Missing trade-date FX for " + day);
        String hash = UsReferenceAlerts.sha256(day.toString().getBytes(StandardCharsets.UTF_8));
        var ledger = UsDeviceFinancials.screen(day, UsDoltCloses.SOURCE, hash, facts, prices, fx, splits);
        return new Stage(prices.size(), facts.length(), UsReferenceAlerts.read(ledger));
    }

    static JSONObject response(Path input, String name) throws IOException, JSONException {
        var result = json(input, name);
        if (!"Success".equals(result.optString("query_execution_status"))) {
            throw new JSONException("Unsuccessful Dolt response: " + name);
        }
        return result;
    }

    static JSONObject json(Path input, String name) throws IOException, JSONException {
        return new JSONObject(Files.readString(input.resolve(name)));
    }
}
