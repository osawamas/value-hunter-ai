package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.Locale;
import java.util.TreeSet;

/** Public-source runner for the same US screening code used by the app. */
public final class UsLiveCoverage {
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build();
    private static final String FX = "https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY";
    private static final String FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json";
    private static final JSONArray SOURCES = new JSONArray();
    private static final java.util.Set<String> SEEN_HOSTS = new java.util.HashSet<>();

    public static void main(String[] args) throws Exception {
        var directory = Path.of(args[0]);
        var report = new JSONObject().put("status", "inputs_unavailable").put("stage", "listing_scope").put("sources", SOURCES);
        try {
            assess(directory, report);
        } catch (IOException | org.json.JSONException unavailable) {
            report.put("error", unavailable.getClass().getSimpleName());
        } finally {
            Files.writeString(directory.resolve("us-public-coverage.json"), report.toString(2));
            System.out.println(new JSONObject(report, new String[]{"status", "stage", "error", "trade_date", "scope", "closes", "valuation"}));
        }
    }

    private static void assess(Path directory, JSONObject report) throws Exception {
        var nyse = UsMarketCoverage.directory(Files.readString(directory.resolve("otherlisted.txt")), false);
        var nasdaq = UsMarketCoverage.directory(Files.readString(directory.resolve("nasdaqlisted.txt")), true);
        var day = nyse.date();
        report.put("trade_date", day.toString());
        if (!day.equals(nasdaq.date()) || !UsDailyCloses.tradingDay(day)
                || !UsMarketCoverage.sessionSnapshot(nyse.timestamp())
                || !UsMarketCoverage.sessionSnapshot(nasdaq.timestamp())) {
            report.put("status", "dated_listing_pair_unverified");
            return;
        }
        var scope = new TreeSet<>(nyse.symbols());
        scope.addAll(nasdaq.symbols());
        report.put("scope", scope.size()).put("stage", "closing_prices");
        JSONArray closes;
        try {
            closes = UsDoltCloses.fetch(day, url -> new JSONObject(read(url, "")));
        } catch (org.json.JSONException invalidCloses) {
            report.put("status", "dated_close_provider_response_unverified");
            return;
        }
        var prices = UsDeviceFinancials.prices(closes);
        report.put("closes", scope.stream().filter(prices::containsKey).count());
        if (prices.isEmpty()) {
            report.put("status", "dated_closes_unavailable");
            return;
        }
        var contact = System.getenv().getOrDefault("SEC_USER_AGENT", "").trim();
        if (!contact.contains("@") || contact.contains("\n") || contact.contains("\r")) {
            report.put("status", "sec_contact_unconfigured");
            return;
        }
        report.put("stage", "trade_date_fx");
        var rates = new JSONArray(read(FX + "&from=" + day.minusDays(7) + "&to=" + day, ""));
        var fx = UsScreen.readFx(rates, day);
        if (!day.equals(fx.date())) {
            report.put("status", "trade_date_fx_unavailable");
            return;
        }
        report.put("stage", "split_verification");
        var splits = UsDoltCloses.allSplits(day.minusMonths(16), day, url -> new JSONObject(read(url, "")));
        report.put("stage", "sec_facts");
        var registry = new JSONObject(read(UsDeviceFinancials.SEC_DIRECTORY, contact));
        var targets = UsDeviceFinancials.targets(nyse, nasdaq, registry, prices.keySet());
        var rows = new JSONArray();
        var checkpoint = new JSONObject().put("coverage_listing_date", day.toString())
                .put("coverage_symbols", new JSONArray(scope)).put("results", rows);
        var deadline = Instant.now().plus(Duration.ofMinutes(7));
        int processed = 0;
        var factsByIssuer = new java.util.HashMap<Integer, JSONObject>();
        for (; processed < targets.length() && Instant.now().isBefore(deadline); processed++) {
            var target = targets.getJSONObject(processed);
            int cik = target.getInt("cik");
            var payload = factsByIssuer.get(cik);
            if (payload == null) {
                try {
                    payload = new JSONObject(read(String.format(Locale.ROOT, FACTS, cik), contact));
                    factsByIssuer.put(cik, payload);
                } catch (HttpFailure denied) {
                    if (denied.status != 404) break;
                    UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"),
                            new UsDeviceFinancials.FetchAssessment(null, "sec_not_found"));
                    Thread.sleep(350);
                    continue;
                } catch (org.json.JSONException invalidIssuer) {
                    UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"),
                            new UsDeviceFinancials.FetchAssessment(null, "sec_invalid_payload"));
                    Thread.sleep(350);
                    continue;
                } catch (IOException unavailable) {
                    report.put("financial_stop", unavailable.getClass().getSimpleName());
                    break;
                }
                Thread.sleep(350);
            }
            var result = UsDeviceFinancials.assessFetch(target, payload, day);
            if (result.row() != null) rows.put(result.row());
            UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"), result);
        }
        var hash = UsReferenceAlerts.sha256(closes.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var measured = UsDeviceFinancials.scopedAssessment(day, UsDoltCloses.SOURCE, hash, checkpoint, prices, fx, splits);
        report.put("stage", "valuation").put("status", processed == targets.length() ? "completed_scope" : "partial_financial_pass")
                .put("financial_targets", targets.length()).put("financial_processed", processed)
                .put("valuation", measured);
    }

    private static String read(String url, String contact) throws IOException {
        var request = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(25))
                .header("User-Agent", contact.isEmpty() ? "ValueHunter-public-market-audit/1.0" : contact).build();
        try {
            var response = HTTP.send(request, HttpResponse.BodyHandlers.ofString());
            // SEC facts are uniform requests. Record the first response and every failure without
            // publishing the contact or a ticker-by-ticker issuer list.
            String host = request.uri().getHost();
            if (SEEN_HOSTS.add(host) || response.statusCode() != 200) {
                SOURCES.put(new JSONObject().put("host", host).put("http", response.statusCode())
                        .put("at", Instant.now().toString()));
            }
            if (response.statusCode() != 200) throw new HttpFailure(response.statusCode());
            return response.body();
        } catch (java.net.http.HttpTimeoutException timeout) {
            var failure = new java.net.SocketTimeoutException(timeout.getMessage());
            failure.initCause(timeout);
            throw failure;
        } catch (InterruptedException cancelled) {
            Thread.currentThread().interrupt();
            throw new IOException(cancelled);
        }
    }

    private static final class HttpFailure extends IOException {
        final int status;

        HttpFailure(int status) {
            this.status = status;
        }
    }
}
