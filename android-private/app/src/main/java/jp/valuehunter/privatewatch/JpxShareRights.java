package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.math.BigDecimal;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.Instant;
import java.time.ZoneId;
import java.time.YearMonth;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

record JpxShareRights(Set<String> coveredCodes, Set<YearMonth> months, List<Notice> notices,
                      Map<String, JpxIssuerArchive.Review> issuerReviews, List<Adjustment> adjustments) {
    record Adjustment(String code, LocalDate exDay, LocalDate recordDay, BigDecimal oldShares, BigDecimal newShares) {}

    JpxShareRights(Set<String> coveredCodes, Set<YearMonth> months, List<Notice> notices,
                   Map<String, JpxIssuerArchive.Review> issuerReviews) {
        this(coveredCodes, months, notices, issuerReviews, List.of());
    }
    JpxShareRights(Set<String> coveredCodes, Set<YearMonth> months, List<Notice> notices) {
        this(coveredCodes, months, notices, Map.of());
    }
    private static final String ASSET = "jpx-share-rights.json";
    private static final String ONLINE =
            "https://raw.githubusercontent.com/osawamas/value-hunter-ai/main/android-private/app/src/main/assets/"
                    + ASSET;
    private static final int MAX_BYTES = 262_144;
    private static final String JPX_MONTHLY =
            "https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html";

    record Notice(String code, LocalDate exDay, String source) {
        String description() {
            return "権利落日 " + exDay + " · <a href='" + source + "'>JPX原本</a>";
        }
    }

    record Selection(JpxShareRights rights, String status, String revision) {}

    record Snapshot(Instant revision, JpxShareRights rights, String body) {}

    static JpxShareRights load(Context context) {
        var asset = readBundled(context);
        return asset == null ? empty() : asset.rights();
    }

    static synchronized JpxShareRights cached(Context context) {
        var cache = new AtomicFile(new File(context.getFilesDir(), ASSET));
        Snapshot saved = null;
        try (var input = cache.openRead()) {
            saved = read(input);
        } catch (IOException | JSONException | DateTimeException unavailable) {
            // Use the bundled copy if the downloaded snapshot cannot be read.
        }
        var selected = cachedOrBundled(saved, readBundled(context));
        return selected == null ? empty() : selected.rights();
    }

    boolean splitMonthsCovered(LocalDate from, LocalDate to) {
        for (var month = YearMonth.from(from.plusDays(1)); !month.isAfter(YearMonth.from(to)); month = month.plusMonths(1)) {
            if (!months.contains(month)) return false;
        }
        return true;
    }

    @FunctionalInterface
    interface FetchSnapshot {
        String fetch() throws IOException;
    }

    static Selection refresh(Context context) {
        return JpxIssuerArchive.extend(context, refresh(context, () -> UsScanWorker.get(ONLINE, null)));
    }

    static synchronized Selection refresh(Context context, FetchSnapshot sourceLoader) {
        var bundled = readBundled(context);
        var cache = new AtomicFile(new File(context.getFilesDir(), ASSET));
        Snapshot saved = null;
        try (var input = cache.openRead()) {
            saved = read(input);
        } catch (IOException | JSONException | DateTimeException ignored) {
            // A missing or invalid cache can be recovered from the bundled or online copy.
        }
        var local = cachedOrBundled(saved, bundled);
        boolean online = false;
        try {
            var remote = parse(sourceLoader.fetch());
            if (isNewer(remote, local)) {
                var output = cache.startWrite();
                try {
                    output.write(remote.body().getBytes(StandardCharsets.UTF_8));
                    cache.finishWrite(output);
                } catch (IOException error) {
                    cache.failWrite(output);
                    throw error;
                }
                local = remote;
                online = true;
            } else if (remote.revision().equals(local.revision()) && remote.body().equals(local.body())) {
                online = true;
            }
        } catch (IOException | JSONException | DateTimeException ignored) {
            // Keep the newest valid local copy when the online copy cannot be used.
        }
        if (local == null) return new Selection(empty(), "権利落ち資料を確認できなかった", "");
        String source = online ? "オンライン資料"
                : (local == saved ? "端末に保存した資料" : "アプリ同梱資料");
        var checkedOn = local.revision().atZone(ZoneId.of("Asia/Tokyo")).toLocalDate();
        return new Selection(local.rights(), "権利落ち資料 " + checkedOn + "（" + source + "）", local.revision().toString());
    }

    static Snapshot cachedOrBundled(Snapshot saved, Snapshot bundled) {
        return isNewer(saved, bundled) ? saved : bundled;
    }

    static boolean isNewer(Snapshot candidate, Snapshot current) {
        return candidate != null && (current == null || candidate.revision().isAfter(current.revision()));
    }

    private static JpxShareRights empty() {
        return new JpxShareRights(Set.of(), Set.of(), List.of());
    }

    private static Snapshot readBundled(Context context) {
        try (var asset = context.getAssets().open(ASSET)) {
            return read(asset);
        } catch (IOException | JSONException | DateTimeException error) {
            return null;
        }
    }

    private static Snapshot read(InputStream input) throws IOException, JSONException {
        var bytes = new ByteArrayOutputStream();
        byte[] buffer = new byte[8_192];
        for (int length; (length = input.read(buffer)) != -1;) {
            if (bytes.size() + length > MAX_BYTES) throw new IOException("JPX rights snapshot is too large");
            bytes.write(buffer, 0, length);
        }
        return parse(bytes.toString(StandardCharsets.UTF_8.name()));
    }

    static Snapshot parse(String body) throws JSONException {
        if (body.getBytes(StandardCharsets.UTF_8).length > MAX_BYTES) {
            throw new JSONException("JPX rights snapshot is too large");
        }
        var payload = new JSONObject(body);
        var revision = Instant.parse(payload.getString("revision"));
        var codes = new HashSet<String>();
        var covered = payload.getJSONArray("coveredCodes");
        for (int index = 0; index < covered.length(); index++) {
            String code = covered.getString(index);
            if (!code.matches("[0-9][0-9A-Z]{3}")) throw new JSONException("Invalid JPX security code");
            codes.add(code);
        }
        var months = new HashSet<YearMonth>();
        var coverage = payload.getJSONObject("monthlySources");
        var keys = coverage.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            officialSource(coverage.getString(key));
            months.add(YearMonth.parse(key));
        }
        var entries = payload.getJSONArray("notices");
        var notices = new ArrayList<Notice>();
        for (int index = 0; index < entries.length(); index++) {
            var entry = entries.getJSONObject(index);
            String code = entry.getString("code");
            if (!codes.contains(code)) throw new JSONException("JPX notice outside snapshot scope");
            notices.add(new Notice(code, LocalDate.parse(entry.getString("exDay")),
                    officialSource(entry.getString("source"))));
        }
        if (codes.isEmpty()) throw new JSONException("JPX rights snapshot has no covered codes");
        var adjustments = new ArrayList<Adjustment>();
        var actions = payload.optJSONArray("adjustments");
        if (actions != null) for (int index = 0; index < actions.length(); index++) {
            var row = actions.getJSONArray(index);
            String code = row.getString(0);
            var exDay = LocalDate.parse(row.getString(1));
            var recordDay = LocalDate.parse(row.getString(2));
            var oldShares = shares(row.getString(3));
            var newShares = shares(row.getString(4));
            if (!code.matches("[0-9][0-9A-Z]{3}") || !months.contains(YearMonth.from(exDay))
                    || exDay.isAfter(recordDay) || oldShares.compareTo(newShares) == 0) {
                throw new JSONException("Invalid JPX share adjustment");
            }
            adjustments.add(new Adjustment(code, exDay, recordDay, oldShares, newShares));
        }
        var rights = new JpxShareRights(Set.copyOf(codes), Set.copyOf(months), List.copyOf(notices),
                Map.of(), List.copyOf(adjustments));
        return new Snapshot(revision, rights, body);
    }

    private static BigDecimal shares(String value) throws JSONException {
        if (!value.matches("[0-9]{1,10}(?:\\.[0-9]{1,10})?")) throw new JSONException("Invalid share ratio");
        var number = new BigDecimal(value);
        if (number.signum() <= 0) throw new JSONException("Invalid share ratio");
        return number;
    }

    Adjustment adjustment(String code, JpxIssuerArchive.Disclosure disclosure, LocalDate recordDay) {
        Adjustment match = null;
        boolean split = disclosure.title().contains("分割");
        for (var action : adjustments) {
            if (!action.code().equals(code) || !action.recordDay().equals(recordDay)
                    || !disclosure.day().isBefore(action.exDay())
                    || split != (action.oldShares().compareTo(action.newShares()) < 0)) continue;
            if (match != null && !match.equals(action)) return null;
            match = action;
        }
        return match;
    }

    private static String officialSource(String url) throws JSONException {
        if (!url.matches("https://www\\.jpx\\.co\\.jp/[A-Za-z0-9./_-]+")) {
            throw new JSONException("Invalid JPX rights source");
        }
        return url;
    }

    Notice firstChange(String code, LocalDate fromExclusive, LocalDate through) {
        return firstNotice(code, fromExclusive, through, List.of());
    }

    Notice firstUnadjustedChange(String code, LocalDate fromExclusive, LocalDate through, List<Adjustment> applied) {
        for (var action : adjustments) {
            if (action.code().equals(code) && action.exDay().isAfter(fromExclusive)
                    && !action.exDay().isAfter(through) && !applied.contains(action)) {
                return new Notice(code, action.exDay(), JPX_MONTHLY);
            }
        }
        return firstNotice(code, fromExclusive, through, applied);
    }

    private Notice firstNotice(String code, LocalDate fromExclusive, LocalDate through, List<Adjustment> applied) {
        for (var notice : notices) {
            if (notice.code().equals(code) && notice.exDay().isAfter(fromExclusive)
                    && !notice.exDay().isAfter(through)
                    && applied.stream().noneMatch(action -> action.exDay().equals(notice.exDay()))) return notice;
        }
        return null;
    }

    String holdReason(String code, LocalDate fromExclusive, LocalDate through) {
        var notice = firstChange(code, fromExclusive, through);
        return notice == null ? coverageHold(code, fromExclusive, through) : notice.description();
    }

    private String coverageHold(String code, LocalDate fromExclusive, LocalDate through) {
        if (!through.isAfter(fromExclusive)) return "";
        if (!coveredCodes.contains(code)) return "対象銘柄の分割・併合資料なし";
        var missing = new ArrayList<YearMonth>();
        for (var month = YearMonth.from(fromExclusive.plusDays(1));
             !month.isAfter(YearMonth.from(through)); month = month.plusMonths(1)) {
            if (months.contains(month)) continue;
            var review = issuerReviews.get(code);
            LocalDate begin = month.atDay(1).isAfter(fromExclusive) ? month.atDay(1) : fromExclusive.plusDays(1);
            LocalDate end = month.atEndOfMonth().isBefore(through) ? month.atEndOfMonth() : through;
            if (review == null || !review.covers(begin, end)) missing.add(month);
        }
        if (missing.isEmpty()) return "";
        return "権利落月報の未確認月 " + missing.stream().map(YearMonth::toString)
                .collect(java.util.stream.Collectors.joining("、"))
                + " · <a href='" + JPX_MONTHLY + "'>JPX統計月報</a>";
    }
}
