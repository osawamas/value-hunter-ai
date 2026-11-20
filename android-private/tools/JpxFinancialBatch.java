package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONObject;

import javax.net.ssl.HttpsURLConnection;
import java.io.IOException;
import java.math.BigDecimal;
import java.net.URI;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.StandardCharsets;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Desktop replay of Android's financial acquisition with byte-level evidence. */
public final class JpxFinancialBatch {
    private record Original(String url, String sha256) {}

    private static final class Sources implements JpxAutomaticFinance.Sources {
        final JpxIssuerArchive.Session session;
        final LocalDate day;
        final JpxShareRights rights;
        Original original;

        Sources(JpxIssuerArchive.Session session, LocalDate day, JpxShareRights rights) {
            this.session = session;
            this.day = day;
            this.rights = rights;
        }

        @Override public JpxIssuerArchive.Page archive(String symbol) throws IOException {
            var page = session.archive(symbol);
            return page == null ? null : new JpxIssuerArchive.Page(page.disclosures().stream()
                    .filter(row -> !row.day().isAfter(day)).toList());
        }

        @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
            var address = disclosure.annualLink();
            byte[] bytes = download(address, 2_000_000);
            original = new Original(address.toString(), UsReferenceAlerts.sha256(bytes));
            try {
                return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();
            } catch (CharacterCodingException legacy) {
                return new String(bytes, Charset.forName("windows-31j"));
            }
        }

        @Override public LocalDate effective(JpxIssuerArchive.Disclosure disclosure) throws IOException {
            return JpxCorporateActionDate.effective(pdfText(disclosure.pdfLink()), disclosure);
        }

        @Override public JpxShareRights.Adjustment adjustment(String symbol, JpxIssuerArchive.Disclosure disclosure)
                throws IOException {
            if (rights.adjustments().stream().noneMatch(action -> action.code().equals(symbol))) return null;
            var body = pdfText(disclosure.pdfLink());
            var effective = JpxCorporateActionDate.effective(body, disclosure);
            return rights.adjustment(symbol, disclosure, JpxCorporateActionDate.recordDay(body, disclosure, effective));
        }
    }

    public static void main(String[] args) throws Exception {
        boolean serial = args.length == 6 && args[5].equals("--serial");
        if (args.length != 5 && !serial)
            throw new IllegalArgumentException("Expected date, closes TSV, rights JSON, starting code, limit and optional --serial");
        var day = LocalDate.parse(args[0]);
        var rights = JpxShareRights.parse(Files.readString(Path.of(args[2]))).rights();
        var closes = new TreeMap<String, BigDecimal>();
        for (String line : Files.readAllLines(Path.of(args[1]))) {
            String[] fields = line.split("\t", -1);
            if (fields.length != 2 || !fields[0].matches("[0-9][0-9A-Z]{3}"))
                throw new IllegalArgumentException("Invalid closing row");
            var price = fields[1].isEmpty() ? null : new BigDecimal(fields[1]);
            if ((price != null && price.signum() <= 0) || closes.containsKey(fields[0]))
                throw new IllegalArgumentException("Nonpositive or duplicate close");
            closes.put(fields[0], price);
        }
        int limit = Integer.parseInt(args[4]);
        if (limit < 1 || limit > 200 || !args[3].matches("[0-9][0-9A-Z]{3}"))
            throw new IllegalArgumentException("Invalid batch parameters");
        var eligible = closes.tailMap(args[3], true).entrySet().stream()
                .limit(limit).toList();
        var executor = Executors.newFixedThreadPool(serial ? 1 : 4);
        var sessions = ThreadLocal.withInitial(JpxIssuerArchive.Session::new);
        var limited = new AtomicBoolean();
        var records = new JSONArray();
        long started = System.nanoTime();
        try {
            var jobs = eligible.stream().map(row -> executor.submit(() ->
                    inspect(row.getKey(), row.getValue(), day, rights, limited, sessions.get()))).toList();
            for (var job : jobs) {
                records.put(job.get());
                if (serial && !limited.get() && (records.length() % 12 == 0 || records.length() == jobs.size()))
                    System.err.printf(java.util.Locale.ROOT, "%d rows in %.3f seconds%n", records.length(),
                            (System.nanoTime() - started) / 1_000_000_000.0);
            }
        } finally {
            executor.shutdownNow();
        }
        System.out.println(new JSONObject().put("date", day.toString()).put("universe", closes.keySet())
                .put("paused", limited.get()).put("records", records));
    }

    private static JSONObject inspect(String code, BigDecimal price, LocalDate day, JpxShareRights rights,
                                      AtomicBoolean limited, JpxIssuerArchive.Session session) {
        var row = new JSONObject().put("ticker", code);
        if (limited.get()) return row.put("reason", "rate_limited_before_request");
        var sources = new Sources(session, day, rights);
        try {
            var entry = JpxAutomaticFinance.acquire(code, day, null, sources);
            var report = new JpxDailyCheck.Report(day, "", Map.of(code, new JpxCloseTable.Sessions(null, price)), Set.of());
            var finance = new JpxAutomaticFinance.Batch(Map.of(code, entry), Map.of(), 1, 1);
            var screen = new JpxDailyCheck.Comparison(report, null).screen(rights, finance);
            boolean assessed = entry.annual() != null && screen.assessedCodes().contains(code) && sources.original != null;
            row.put("annual_verified", entry.annual() != null)
                    .put("financial_eligible", assessed).put("on_hold", !assessed);
            if (!assessed) {
                var reason = screen.holds().stream().filter(hold -> code.equals(hold.code()))
                        .map(JpxDailyCheck.Held::reason).findFirst().orElse(entry.hold());
                row.put("reason", price == null ? "当日の終値なし"
                        : reason.isEmpty() ? "財務条件の確認待ち" : reason);
            }
        } catch (IOException unavailable) {
            if (unavailable instanceof JpxIssuerArchive.HttpFailure failure) {
                row.put("http_status", failure.status);
                if (failure.status == 429 || failure.status == 503) limited.set(true);
            }
            row.put("on_hold", true).put("reason", "source_unavailable");
        } catch (IllegalArgumentException | java.time.DateTimeException invalid) {
            row.put("on_hold", true).put("reason", "東証の決算開示を確認できなかった");
        }
        if (sources.original != null) row.put("source_url", sources.original.url()).put("source_sha256", sources.original.sha256());
        return row;
    }

    private static String pdfText(URI address) throws IOException {
        if (!JpxIssuerArchive.disclosureSource(address)) throw new IOException("Unexpected JPX PDF source");
        var file = Files.createTempFile("jpx-financial-batch-", ".pdf");
        try {
            Files.write(file, download(address, 8_000_000));
            var process = new ProcessBuilder("pdftotext", "-layout", file.toString(), "-").start();
            byte[] text = process.getInputStream().readAllBytes();
            return process.waitFor() == 0 ? new String(text, StandardCharsets.UTF_8) : "";
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IOException(interrupted);
        } finally {
            Files.deleteIfExists(file);
        }
    }

    private static byte[] download(URI address, int max) throws IOException {
        var connection = (HttpsURLConnection) address.toURL().openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(8_000);
        connection.setReadTimeout(10_000);
        try {
            int status = connection.getResponseCode();
            if (status != 200) throw new JpxIssuerArchive.HttpFailure(status);
            try (var input = connection.getInputStream()) {
                byte[] data = input.readNBytes(max + 1);
                if (data.length == 0 || data.length > max) throw new IOException("Invalid JPX original length");
                return data;
            }
        } finally {
            connection.disconnect();
        }
    }

    private JpxFinancialBatch() {}
}
