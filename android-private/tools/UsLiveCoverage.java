package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
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
            var options = java.util.Arrays.asList(args).subList(1, args.length);
            assess(directory, report, options.contains("--probe-nasdaq-close"), options.contains("--alpaca"));
        } catch (HttpFailure denied) {
            report.put("error", "HttpFailure").put("http_status", denied.status);
        } catch (IOException | org.json.JSONException unavailable) {
            report.put("error", unavailable.getClass().getSimpleName());
        } finally {
            Files.writeString(directory.resolve("us-public-coverage.json"), report.toString(2));
            System.out.println(new JSONObject(report, new String[]{"status", "stage", "error", "trade_date", "scope", "closes", "valuation"}));
        }
    }

    private static void assess(Path directory, JSONObject report, boolean probeNasdaq, boolean useAlpaca) throws Exception {
        var nyse = UsMarketCoverage.directory(Files.readString(directory.resolve("otherlisted.txt")), false);
        var nasdaq = UsMarketCoverage.directory(Files.readString(directory.resolve("nasdaqlisted.txt")), true);
        var day = nyse.date();
        report.put("trade_date", day.toString()).put("listing_inputs", new JSONObject()
                .put("nyse_date", nyse.date().toString()).put("nyse_time", String.valueOf(nyse.timestamp()))
                .put("nasdaq_date", nasdaq.date().toString()).put("nasdaq_time", String.valueOf(nasdaq.timestamp())));
        if (probeNasdaq && UsDailyCloses.tradingDay(day)) report.put("nasdaq_official_preview", probeNasdaqClose(day));
        if (!day.equals(nasdaq.date()) || !UsDailyCloses.tradingDay(day)
                || !UsMarketCoverage.sessionSnapshot(nyse.timestamp())
                || !UsMarketCoverage.sessionSnapshot(nasdaq.timestamp())) {
            report.put("status", "dated_listing_pair_unverified");
            return;
        }
        var scope = new TreeSet<>(nyse.symbols());
        scope.addAll(nasdaq.symbols());
        report.put("scope", scope.size()).put("stage", "closing_prices");
        var alpacaSplits = new java.util.HashMap<String, java.time.LocalDate>();
        var closes = useAlpaca ? alpacaCloses(day, scope, report, alpacaSplits) : null;
        String closeSource = closes == null ? UsDoltCloses.SOURCE : "alpaca_delayed_sip_raw";
        if (closes != null) report.put("quote_path", closeSource);
        UsDoltCloses.Download download = url -> new JSONObject(read(url, ""));
        if (closes == null) try {
            try {
                closes = UsDoltCloses.fetch(day, download);
            } catch (java.net.SocketTimeoutException timeout) {
                closes = null;
            }
            if (closes == null || closes.length() == 0) {
                report.put("quote_path", "dolt_scoped_symbol_batches");
                var scoped = UsDoltCloses.fetchScoped(day, scope, download);
                closes = scoped.rows();
                report.put("quote_symbols_queried", scoped.queriedSymbols())
                        .put("quote_pass_timed_out", scoped.timedOut());
            } else {
                report.put("quote_path", "dolt_date_manifest");
            }
        } catch (org.json.JSONException invalidCloses) {
            report.put("status", "dated_close_provider_response_unverified");
            return;
        }
        if (closes.length() == 0) {
            report.put("closes", 0).put("status", report.optBoolean("quote_pass_timed_out")
                    ? "scoped_close_timeout" : "dated_closes_unavailable");
            return;
        }
        var prices = UsDeviceFinancials.prices(closes);
        long matchingCloses = scope.stream().filter(prices::containsKey).count();
        report.put("closes", matchingCloses);
        var missingClose = new TreeSet<>(scope);
        missingClose.removeAll(prices.keySet());
        report.put("missing_close_count", missingClose.size());
        if (!missingClose.isEmpty() && missingClose.size() <= 100) {
            report.put("missing_close_symbols", new JSONArray(missingClose));
            if (useAlpaca && closeSource.equals("alpaca_delayed_sip_raw")) {
                try {
                    var repairs = UsDoltCloses.supplement(day, missingClose,
                            url -> new JSONObject(read(url, "", Duration.ofSeconds(12))));
                    report.put("dolt_missing_close_candidates", repairs.length());
                } catch (IOException | JSONException unavailable) {
                    report.put("dolt_missing_close_error", unavailable.getClass().getSimpleName());
                }
            }
        }
        if (matchingCloses == 0) {
            report.put("status", "no_dated_closes_for_listed_scope");
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
        var splits = alpacaSplits.isEmpty()
                ? UsDoltCloses.allSplits(day.minusMonths(16), day, url -> new JSONObject(read(url, ""))) : alpacaSplits;
        report.put("split_source", alpacaSplits.isEmpty() ? UsDoltCloses.SOURCE : "alpaca_corporate_actions");
        report.put("stage", "sec_facts");
        var registry = new JSONObject(read(UsDeviceFinancials.SEC_DIRECTORY, contact));
        var targets = UsDeviceFinancials.targets(nyse, nasdaq, registry, prices.keySet());
        var rows = new JSONArray();
        var checkpoint = new JSONObject().put("coverage_listing_date", day.toString())
                .put("coverage_symbols", new JSONArray(scope)).put("results", rows);
        var deadline = Instant.now().plus(Duration.ofMinutes(useAlpaca ? 3 : 7));
        int processed = 0;
        var factsByIssuer = new java.util.HashMap<Integer, JSONObject>();
        try (var archive = companyFactsArchive(report)) {
            for (; processed < targets.length() && Instant.now().isBefore(deadline); processed++) {
                var target = targets.getJSONObject(processed);
                int cik = target.getInt("cik");
                var payload = factsByIssuer.get(cik);
                if (payload == null) {
                    try {
                        payload = archive == null
                                ? new JSONObject(read(String.format(Locale.ROOT, FACTS, cik), contact))
                                : archiveFacts(archive, cik);
                        if (payload == null) {
                            UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"),
                                    new UsDeviceFinancials.FetchAssessment(null, "sec_not_in_bulk_archive"));
                            continue;
                        }
                        if (archive == null && factsByIssuer.size() < 64) factsByIssuer.put(cik, payload);
                    } catch (HttpFailure denied) {
                        if (denied.status != 404) break;
                        UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"),
                                new UsDeviceFinancials.FetchAssessment(null, "sec_not_found"));
                        if (archive == null) Thread.sleep(350);
                        continue;
                    } catch (org.json.JSONException invalidIssuer) {
                        UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"),
                                new UsDeviceFinancials.FetchAssessment(null, "sec_invalid_payload"));
                        if (archive == null) Thread.sleep(350);
                        continue;
                    } catch (IOException unavailable) {
                        report.put("financial_stop", unavailable.getClass().getSimpleName());
                        break;
                    }
                    if (archive == null) Thread.sleep(350);
                }
                var result = UsDeviceFinancials.assessFetch(target, payload, day);
                if (result.row() != null) rows.put(result.row());
                UsDeviceFinancials.recordFetchOutcome(checkpoint, target.getString("symbol"), result);
            }
        }
        var hash = UsReferenceAlerts.sha256(closes.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        var measured = UsDeviceFinancials.scopedAssessment(day, closeSource, hash, checkpoint, prices, fx, splits);
        String status = processed != targets.length() ? "partial_financial_pass"
                : report.optBoolean("quote_pass_timed_out") ? "partial_quote_pass" : "completed_scope";
        report.put("stage", "valuation").put("status", status)
                .put("financial_targets", targets.length()).put("financial_processed", processed)
                .put("valuation", measured);
    }

    private static java.util.zip.ZipFile companyFactsArchive(JSONObject report) {
        String path = System.getenv().getOrDefault("SEC_COMPANYFACTS_ZIP", "");
        if (!path.isEmpty()) {
            try {
                var archive = new java.util.zip.ZipFile(path);
                report.put("financial_source", "sec_nightly_companyfacts_zip");
                return archive;
            } catch (IOException invalid) {
                report.put("financial_archive", "unavailable");
            }
        }
        report.put("financial_source", "sec_companyfacts_per_issuer");
        return null;
    }

    private static JSONObject archiveFacts(java.util.zip.ZipFile archive, int cik) throws IOException {
        var entry = archive.getEntry(String.format(Locale.ROOT, "CIK%010d.json", cik));
        if (entry == null) return null;
        final int maxBytes = 16_000_000;
        if (entry.getSize() > maxBytes) throw new JSONException("SEC company facts entry too large");
        try (var stream = archive.getInputStream(entry)) {
            var bytes = stream.readNBytes(maxBytes + 1);
            if (bytes.length > maxBytes) throw new JSONException("SEC company facts entry too large");
            var facts = new JSONObject(new String(bytes, java.nio.charset.StandardCharsets.UTF_8));
            if (facts.optInt("cik") != cik) throw new JSONException("SEC company facts issuer mismatch");
            return facts;
        }
    }

    private static JSONArray alpacaCloses(java.time.LocalDate day, TreeSet<String> scope, JSONObject report,
            java.util.Map<String, java.time.LocalDate> splits)
            throws IOException, InterruptedException {
        var scratch = Files.createTempDirectory("us-alpaca-");
        var scopeFile = scratch.resolve("scope.json");
        var closeFile = scratch.resolve("close.json");
        var summaryFile = scratch.resolve("summary.json");
        try {
            Files.writeString(scopeFile, new JSONObject().put("trade_date", day.toString())
                    .put("symbols", new JSONArray(scope)).toString());
            var process = new ProcessBuilder("python", "android-private/tools/us_alpaca_close_probe.py",
                    "--scope", scopeFile.toString(), "--close-output", closeFile.toString())
                    .redirectOutput(summaryFile.toFile()).redirectError(ProcessBuilder.Redirect.DISCARD).start();
            if (!process.waitFor(100, java.util.concurrent.TimeUnit.SECONDS)) {
                process.destroyForcibly().waitFor();
                report.put("alpaca", new JSONObject().put("status", "transport_deadline"));
                return null;
            }
            if (process.exitValue() != 0 || Files.size(summaryFile) > 16_384) {
                report.put("alpaca", new JSONObject().put("status", "probe_incomplete"));
                return null;
            }
            var summary = new JSONObject(Files.readString(summaryFile));
            report.put("alpaca", summary);
            if (!"sample_verified".equals(summary.optString("status")) || !Files.isRegularFile(closeFile))
                return null;
            if (Files.size(closeFile) > 1_000_000) throw new JSONException("Oversized Alpaca input");
            var input = new JSONObject(Files.readString(closeFile));
            var rows = input.getJSONArray("closes");
            var daily = summary.getJSONObject("daily");
            if (!day.toString().equals(input.getString("trade_date"))
                    || daily.getInt("scope") != scope.size() || daily.getInt("closes") != rows.length()
                    || !scope.containsAll(UsDeviceFinancials.prices(rows).keySet())) {
                throw new JSONException("Unverified Alpaca listing scope");
            }
            var datedSplits = input.optJSONObject("splits");
            if (datedSplits != null && summary.getJSONObject("splits").getInt("scoped_symbols") == datedSplits.length()) {
                for (String symbol : datedSplits.keySet()) {
                    var effective = java.time.LocalDate.parse(datedSplits.getString(symbol));
                    if (!scope.contains(symbol) || effective.isAfter(day)) {
                        throw new JSONException("Unverified Alpaca corporate action");
                    }
                    splits.put(symbol, effective);
                }
            }
            report.put("quote_symbols_queried", daily.getInt("queried"))
                    .put("quote_pass_timed_out", !"complete_request_pass".equals(daily.optString("status")));
            return rows;
        } finally {
            Files.deleteIfExists(closeFile);
            Files.deleteIfExists(scopeFile);
            Files.deleteIfExists(summaryFile);
            Files.deleteIfExists(scratch);
        }
    }

    private static JSONObject probeNasdaqClose(java.time.LocalDate day) {
        var result = new JSONObject().put("symbol", "AAPL").put("trade_date", day.toString());
        var previous = UsDailyCloses.onOrBeforeTradingDay(day.minusDays(1));
        try {
            var pair = UsNasdaqOfficialClose.read(
                    new JSONObject(read(UsNasdaqOfficialClose.url("AAPL"), "", Duration.ofSeconds(8))),
                    "AAPL", previous, day);
            return result.put("status", pair == null ? "requested_dates_unavailable" : "dated_sample_verified");
        } catch (HttpFailure denied) {
            return result.put("status", "http_failure").put("http_status", denied.status);
        } catch (IOException | org.json.JSONException unverified) {
            return result.put("status", "unverified").put("error", unverified.getClass().getSimpleName());
        }
    }

    private static String read(String url, String contact) throws IOException {
        return read(url, contact, Duration.ofSeconds(25));
    }

    private static String read(String url, String contact, Duration requestTimeout) throws IOException {
        var request = HttpRequest.newBuilder(URI.create(url)).timeout(requestTimeout)
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
