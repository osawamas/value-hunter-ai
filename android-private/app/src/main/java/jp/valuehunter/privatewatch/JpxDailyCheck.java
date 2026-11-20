package jp.valuehunter.privatewatch;

import android.annotation.TargetApi;
import android.content.Context;
import android.util.AtomicFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.FileInputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Comparator;
import java.util.List;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

import javax.net.ssl.HttpsURLConnection;

import org.json.JSONObject;

import jp.valuehunter.privatewatch.ValueCandidateScreen.Level;

@TargetApi(35)
final class JpxDailyCheck {
    private static final String REPORT_ROOT =
            "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/";
    private static final int MAX_PDF_BYTES = 32_000_000;
    static final List<String> WATCH_CODES = JpxReferenceFinancials.watchCodes();
    private static volatile Comparison cachedComparison;

    private static final BigDecimal BUDGET = BigDecimal.valueOf(JapanScreen.BUDGET);
    private static final BigDecimal LOT_PRICE_LIMIT = BUDGET.movePointLeft(2);

    record Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes,
                  Set<String> ambiguous, String edition, JpxStockUniverse universe) {
        Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes, Set<String> ambiguous) {
            this(date, source, quotes, ambiguous, "");
        }

        Report(LocalDate date, String source, Map<String, JpxCloseTable.Sessions> quotes,
               Set<String> ambiguous, String edition) {
            this(date, source, quotes, ambiguous, edition, null);
        }

        BigDecimal close(String code) {
            var sessions = quotes.get(code);
            if (ambiguous.contains(code) || sessions == null || sessions.close() == null
                    || sessions.close().signum() <= 0) return null;
            return sessions.close();
        }
    }

    record Comparison(Report latest, Report previous) {
        String processedKey(String rightsRevision) {
            if (previous == null) return "";
            return editionKey(latest.date(), latest.edition(), previous.date(), previous.edition(), rightsRevision);
        }
        String html(JpxShareRights rights) {
            return html(rights, JpxHistoryReference.empty());
        }

        String html(JpxShareRights rights, JpxHistoryReference history) {
            return html(rights, history, JpxAutomaticFinance.Batch.empty());
        }

        String html(JpxShareRights rights, JpxHistoryReference history, JpxAutomaticFinance.Batch finance) {
            var message = new StringBuilder("立会日 ").append(latest.date());
            if (previous == null) {
                message.append("<br>比較用の日報を取得できなかった");
            } else {
                message.append("<br>比較日 ").append(previous.date()).append("（分割等の調整前の終値）");
            }
            var screening = screen(rights, finance);
            appendCoverage(message, screening.assessed(), "<br>", finance);
            var automaticCandidates = screening.candidates().stream()
                    .filter(candidate -> !WATCH_CODES.contains(candidate.code())
                            && finance.entries().containsKey(candidate.code())).toList();
            if (!automaticCandidates.isEmpty()) message.append("<br><br>自動取得の割安候補");
            for (var candidate : automaticCandidates.subList(0, Math.min(50, automaticCandidates.size()))) {
                var annual = finance.entries().get(candidate.code()).annualFor(latest.date());
                var close = annual.onShareBasis(latest.date(), latest.close(candidate.code()), true);
                message.append("<br>").append(candidate.summary())
                        .append(" · 参考PER ").append(close.divide(annual.onShareBasis(latest.date(), annual.eps(), false), 2, RoundingMode.HALF_UP))
                        .append(" · 参考PBR ").append(close.divide(annual.onShareBasis(latest.date(), annual.bps(), false), 2, RoundingMode.HALF_UP))
                        .append(" · <a href='").append(annual.source()).append("'>通期決算 ")
                        .append(annual.end()).append("</a>");
            }
            if (automaticCandidates.size() > 50) {
                message.append("<br>ほか ").append(automaticCandidates.size() - 50).append("銘柄");
            }
            var ordered = new ArrayList<>(WATCH_CODES);
            ordered.sort(Comparator.comparingInt((String code) -> budgetQuantity(latest.close(code))).reversed());
            for (String code : ordered) {
                var close = latest.close(code);
                var sessions = latest.quotes().get(code);
                message.append("<br><br>").append(code).append("  ");
                if (latest.ambiguous().contains(code)) {
                    message.append("終値を一意に読み取れなかった");
                } else if (sessions == null) {
                    message.append("銘柄行が見つからなかった");
                } else if (close == null) {
                    message.append("終値なし");
                } else {
                    message.append(close.toPlainString()).append(" 円")
                            .append(sessions.afternoon() == null ? "（前場）" : "（後場）");
                    appendBudget(message, close);
                    history.appendHtml(message, code, latest.date(), close, rights);
                    if (previous != null) appendChange(message, code, close, rights);
                    // Missing monthly evidence is not evidence that no split occurred.
                    // Keep the displayed valuation on hold, not only its day-to-day transition.
                    String valuationHold = rights.holdReason(
                            code, JpxReferenceFinancials.periodEnd(code), latest.date());
                    if (valuationHold.isEmpty()) {
                        JpxReferenceFinancials.appendHtml(message, code, latest.date(), close);
                    } else {
                        message.append("<br>参考PER・PBRは保留（")
                                .append(valuationHold)
                                .append("）");
                        JpxReferenceFinancials.appendShareData(message, code, latest.date());
                    }
                    if (previous != null) appendReferenceTransition(message, code, rights);
                }
            }
            appendSource(message.append("<br>"), latest);
            if (previous != null) appendSource(message, previous);
            return message.toString();
        }

        void appendCoverage(StringBuilder message, int assessed, String newline) {
            appendCoverage(message, assessed, newline, JpxAutomaticFinance.Batch.empty());
        }

        void appendCoverage(StringBuilder message, int assessed, String newline, JpxAutomaticFinance.Batch finance) {
            var universe = latest.universe();
            if (universe == null) return;
            int closes = 0;
            int lots = 0;
            int single = 0;
            for (String code : latest.quotes().keySet()) {
                var close = latest.close(code);
                if (close == null) continue;
                closes++;
                int quantity = budgetQuantity(close);
                if (quantity == 100) lots++;
                if (quantity == 1) single++;
            }
            message.append(newline).append("終値取得 ").append(closes).append(" / ")
                    .append(universe.codes().size()).append("銘柄")
                    .append("（銘柄一覧 ").append(universe.asOf()).append("）")
                    .append(newline).append("購入額10万円以内 · 100株枠 ").append(lots)
                    .append("銘柄 · 1株枠 ").append(single).append("銘柄")
                    .append(newline).append("財務照合済み ").append(assessed)
                    .append(" / 登録 ").append(screenCodes(finance).size()).append("銘柄");
            String financeStatus = finance.status();
            if (!financeStatus.isEmpty()) message.append(newline).append(financeStatus.replace("\n", newline));
        }

        private Set<String> screenCodes(JpxAutomaticFinance.Batch finance) {
            var codes = new LinkedHashSet<>(WATCH_CODES);
            for (var entry : finance.entries().entrySet()) {
                if (entry.getValue().annual() != null) codes.add(entry.getKey());
            }
            return codes;
        }

        private static void appendBudget(StringBuilder message, BigDecimal close) {
            message.append("<br>100株 ").append(close.movePointRight(2).stripTrailingZeros().toPlainString())
                    .append("円 / 1株 ").append(close.toPlainString()).append("円（終値換算・手数料別）");
            int quantity = budgetQuantity(close);
            if (quantity == 100) {
                message.append("<br>予算10万円以内 · 100株");
            } else if (quantity == 1) {
                message.append("<br>予算10万円以内 · 単元未満株の取扱いは証券会社による");
            } else {
                message.append("<br>予算10万円超 · 1株でも対象外");
            }
        }

        private void appendChange(StringBuilder message, String code, BigDecimal close, JpxShareRights rights) {
            BigDecimal previousClose = previous.close(code);
            if (previousClose == null) {
                message.append("<br>比較日の終値を確認できなかった");
                return;
            }
            message.append("<br>比較日の終値 ").append(previousClose.toPlainString()).append("円");
            if (rights.firstChange(code, previous.date(), latest.date()) != null) {
                message.append(" · 値動きの比較は保留（期間内に権利落日）");
                return;
            }
            var change = close.subtract(previousClose);
            var percent = change.movePointRight(2).divide(previousClose, 2, RoundingMode.HALF_UP);
            message.append(" / ")
                    .append(change.signum() > 0 ? "+" : "").append(change.stripTrailingZeros().toPlainString())
                    .append("円（").append(percent.signum() > 0 ? "+" : "")
                    .append(percent.toPlainString()).append("%）");
        }

        Screening screen(JpxShareRights rights) {
            return screen(rights, JpxAutomaticFinance.Batch.empty());
        }

        Screening screen(JpxShareRights rights, JpxAutomaticFinance.Batch finance) {
            var candidates = new ArrayList<Candidate>();
            var entered = new ArrayList<Candidate>();
            var held = new ArrayList<Held>();
            var assessed = new HashSet<String>();
            for (String code : screenCodes(finance)) {
                var automatic = finance.entries().get(code);
                var change = automatic != null && automatic.annual() != null
                        ? automaticChange(code, rights, finance, automatic) : referenceChange(code, rights);
                if (change.now().level() != Level.HELD) assessed.add(code);
                if (change.now().qualifies()) candidates.add(change.now());
                if (!change.hold().isEmpty()) held.add(new Held(code, change.hold()));
                if (change.entered()) entered.add(change.now());
            }
            candidates.sort(CANDIDATE_ORDER);
            entered.sort(CANDIDATE_ORDER);
            return new Screening(List.copyOf(candidates), List.copyOf(entered), List.copyOf(held), Set.copyOf(assessed));
        }

        PriceOnlyScreen.Result priceOnly(Screening financial) {
            if (previous == null || !previous.date().isBefore(latest.date())) return PriceOnlyScreen.Result.empty();
            var codes = latest.universe() == null ? latest.quotes().keySet() : latest.universe().codes();
            return PriceOnlyScreen.budgetEntries(codes, financial.assessedCodes(), previous::close, latest::close);
        }

        // Do not infer a clean corporate-action interval from missing evidence.
        // Callers must supply independently verified split/consolidation and ex-dividend
        // coverage for the exact previous/latest trading-day interval.
        List<PriceOnlyScreen.RapidMove> verifiedRapidMoves(
                Screening financial, JpxAutomaticFinance.Batch finance,
                java.util.function.Predicate<String> splitIntervalVerifiedFree,
                java.util.function.Predicate<String> dividendIntervalVerifiedFree,
                BigDecimal minimumAbsolutePercent) {
            if (previous == null || !previous.date().isBefore(latest.date())) return List.of();
            var codes = latest.universe() == null ? latest.quotes().keySet() : latest.universe().codes();
            var registeredFinancial = new HashSet<>(screenCodes(finance));
            registeredFinancial.addAll(financial.assessedCodes());
            return PriceOnlyScreen.rapidMoves(codes, registeredFinancial,
                    previous::close, latest::close, splitIntervalVerifiedFree,
                    dividendIntervalVerifiedFree, minimumAbsolutePercent);
        }

        private ReferenceChange automaticChange(String code, JpxShareRights rights,
                                                JpxAutomaticFinance.Batch finance, JpxAutomaticFinance.Entry entry) {
            var held = new Candidate(code, 0, Level.HELD);
            String reason = entry.failure(code, latest.date(), finance.updates());
            if (!reason.isEmpty()) return new ReferenceChange(held, held, reason);
            var annual = entry.annualFor(latest.date());
            if (!rights.adjustments().containsAll(annual.adjustments())) {
                return new ReferenceChange(held, held, "JPX分割比率の再確認待ち");
            }
            var notice = rights.firstUnadjustedChange(code, annual.end(), latest.date(), annual.adjustments());
            if (notice != null) return new ReferenceChange(held, held, notice.description());
            var now = candidate(code, latest.close(code), annual.level(latest.date(), latest.close(code)));
            if (previous == null || !previous.date().isBefore(latest.date())) {
                return new ReferenceChange(held, now, "比較用の日報なし");
            }
            var previousAnnual = entry.annualFor(previous.date());
            if (previousAnnual == null) return new ReferenceChange(held, now, "比較日時点の通期決算なし");
            if (!rights.adjustments().containsAll(previousAnnual.adjustments())) {
                return new ReferenceChange(held, now, "比較日のJPX分割比率の再確認待ち");
            }
            var previousNotice = rights.firstUnadjustedChange(
                    code, previousAnnual.end(), previous.date(), previousAnnual.adjustments());
            if (previousNotice != null) return new ReferenceChange(held, now, previousNotice.description());
            var before = candidate(code, previous.close(code),
                    previousAnnual.level(previous.date(), previous.close(code)));
            if (before.level() == Level.HELD || now.level() == Level.HELD) {
                return new ReferenceChange(before, now, "比較に必要な終値または通期決算なし");
            }
            return new ReferenceChange(before, now, "");
        }

        private ReferenceChange referenceChange(String code, JpxShareRights rights) {
            String reason = rights.holdReason(code, JpxReferenceFinancials.periodEnd(code), latest.date());
            if (!reason.isEmpty()) {
                var held = new Candidate(code, 0, Level.HELD);
                return new ReferenceChange(held, held, reason);
            }
            var now = assess(latest, code);
            if (previous == null || !previous.date().isBefore(latest.date())) {
                return new ReferenceChange(new Candidate(code, 0, Level.HELD), now, "比較用の日報なし");
            }
            var before = assess(previous, code);
            if (before.level() == Level.HELD || now.level() == Level.HELD) {
                return new ReferenceChange(before, now, "比較に必要な終値または通期決算なし");
            }
            return new ReferenceChange(before, now, "");
        }

        private void appendReferenceTransition(StringBuilder message, String code, JpxShareRights rights) {
            if (!previous.date().isBefore(latest.date())) return;
            var comparison = referenceChange(code, rights);
            var before = comparison.before();
            var now = comparison.now();
            String change;
            if (!comparison.hold().isEmpty()) {
                change = "保留（" + comparison.hold() + "）";
            } else if (before.equals(now)) {
                change = "条件の変化なし";
            } else if (!now.qualifies()) {
                change = "条件から外れた";
            } else if (comparison.entered()) {
                change = "新たに" + now.level().label + "（" + now.quantity() + "株）";
            } else if (before.level() != now.level()) {
                change = now.level().label + "へ変更（" + now.quantity() + "株）";
            } else {
                change = before.quantity() + "株枠から" + now.quantity() + "株枠へ";
            }
            message.append("<br>参考判定の変化 · ").append(change);
        }

        private static void appendSource(StringBuilder message, Report report) {
            message.append("<br><a href='").append(report.source()).append("'>JPX 株式相場表 ")
                    .append(report.date()).append("（PDF）</a>");
        }
    }

    record Candidate(String code, int quantity, Level level) {
        boolean qualifies() { return level.qualifies(); }

        String summary() {
            return code + " · " + quantity + "株枠 · " + level.label;
        }
    }

    private static final Comparator<Candidate> CANDIDATE_ORDER =
            Comparator.comparingInt(Candidate::quantity).reversed()
                    .thenComparing(candidate -> candidate.level() != Level.PRIORITY)
                    .thenComparing(Candidate::code);

    record Held(String code, String reason) {}

    record Screening(List<Candidate> candidates, List<Candidate> entered, List<Held> holds,
                     Set<String> assessedCodes) {
        int assessed() { return assessedCodes.size(); }
        int held() { return holds.size(); }
    }

    private record ReferenceChange(Candidate before, Candidate now, String hold) {
        boolean entered() {
            return hold.isEmpty() && (now.level().entersFrom(before.level())
                    || before.qualifies() && now.qualifies() && before.quantity() == 1 && now.quantity() == 100);
        }
    }

    private static Candidate assess(Report report, String code) {
        var close = report.close(code);
        var level = JpxReferenceFinancials.level(code, report.date(), close);
        return candidate(code, close, level);
    }

    private static Candidate candidate(String code, BigDecimal close, Level level) {
        int quantity = budgetQuantity(close);
        if (level.qualifies() && quantity == 0) level = Level.OUTSIDE;
        return new Candidate(code, level.qualifies() ? quantity : 0, level);
    }

    static int budgetQuantity(BigDecimal close) {
        if (close == null || close.signum() <= 0 || close.compareTo(BUDGET) > 0) return 0;
        return close.compareTo(LOT_PRICE_LIMIT) <= 0 ? 100 : 1;
    }

    @FunctionalInterface
    interface ReportLoader {
        Report load(LocalDate day) throws IOException;
    }

    static Comparison check(Context context) throws IOException {
        return check(context, JpxDailyCheck::head);
    }

    private static Comparison check(Context context, EditionLoader editions) throws IOException {
        var today = LocalDate.now(ZoneId.of("Asia/Tokyo"));
        var universe = JpxStockUniverse.load(context);
        var listings = JpxStockUniverse.listings();
        var delistings = JpxStockUniverse.delistings();
        var cache = new AtomicFile(new File(context.getNoBackupFilesDir(), "jpx-report-quotes-v1.json"));
        var saved = JpxQuoteCache.read(cache);
        return checkRecent(today, day -> {
            var listed = universe.forTradingDay(day, listings, delistings);
            return cachedReport(day, listed, saved.optJSONObject(day.toString()), editions, requested -> {
                var pdf = File.createTempFile("jpx-daily-", ".pdf", context.getCacheDir());
                try {
                    var response = download(reportUrl(requested), pdf);
                    if (!response.exists()) return null;
                    var report = readReport(pdf, requested, listed, response.version());
                    JpxQuoteCache.save(cache, report);
                    return report;
                } finally {
                    pdf.delete();
                }
            });
        });
    }

    static Report cachedReport(LocalDate day, JpxStockUniverse universe, JSONObject saved,
                               EditionLoader editions, ReportLoader download) throws IOException {
        if (saved != null) {
            try {
                var cached = JpxQuoteCache.restore(saved, day, reportUrl(day), universe, editions.load(day));
                if (cached != null) return cached;
            } catch (IOException unavailable) {
                // Retry through the normal GET when HEAD cannot validate a cached report.
            }
        }
        return download.load(day);
    }

    static Comparison checkWatch(Context context, String processedKey, String rightsRevision) throws IOException {
        var today = LocalDate.now(ZoneId.of("Asia/Tokyo"));
        var observed = new HashMap<LocalDate, Edition>();
        EditionLoader editions = day -> {
            var saved = observed.get(day);
            if (saved != null) return saved;
            var fresh = head(day);
            observed.put(day, fresh);
            return fresh;
        };
        if (unchanged(today, processedKey, rightsRevision, editions)) return null;
        var saved = cachedComparison;
        if (saved != null && unchanged(today, saved.processedKey("quotes"), "quotes", editions)) {
            return saved;
        }
        var comparison = check(context, editions);
        cachedComparison = comparison;
        return comparison;
    }

    record Edition(boolean exists, String version) {}

    @FunctionalInterface
    interface EditionLoader {
        Edition load(LocalDate day) throws IOException;
    }

    static boolean unchanged(LocalDate today, String processedKey, String rightsRevision, EditionLoader loader) {
        if (processedKey.isEmpty() || rightsRevision.isEmpty()) return false;
        LocalDate latest = null;
        String latestEdition = "";
        try {
            for (LocalDate date : candidateDays(today)) {
                if (Thread.currentThread().isInterrupted()) return false;
                var edition = loader.load(date);
                if (!edition.exists()) continue;
                if (edition.version().isEmpty()) return false;
                if (latest != null) {
                    return processedKey.equals(editionKey(latest, latestEdition, date, edition.version(), rightsRevision));
                }
                latest = date;
                latestEdition = edition.version();
            }
        } catch (IOException ignored) {
            // A failed header probe must go through the normal PDF acquisition.
        }
        return false;
    }

    private static String editionKey(LocalDate latest, String latestEdition, LocalDate previous,
                                     String previousEdition, String rightsRevision) {
        if (latestEdition.isEmpty() || previousEdition.isEmpty() || rightsRevision.isEmpty()) return "";
        String identity = "bulk-quotes-v2|" + latest + "|" + latestEdition + "|" + previous + "|" + previousEdition + "|" + rightsRevision;
        try {
            var digest = MessageDigest.getInstance("SHA-256").digest(identity.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(error);
        }
    }

    static Comparison checkRecent(LocalDate today, ReportLoader load) throws IOException {
        Report latest = null;
        for (LocalDate day : candidateDays(today)) {
            if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
            Report report;
            try {
                report = load.load(day);
            } catch (IOException error) {
                if (latest == null || Thread.currentThread().isInterrupted()) throw error;
                return new Comparison(latest, null);
            }
            if (report == null) continue;
            // A stale cache or a mismatched response must not masquerade as the
            // requested trading day. Reject it rather than comparing false dates.
            if (report.date() == null || !report.date().equals(day)) {
                throw new IOException("東証日報の取引日が要求日と一致しない: " + day);
            }
            if (latest != null) {
                if (!report.date().isBefore(latest.date())) {
                    throw new IOException("東証日報の比較日が最新日より前ではない");
                }
                return new Comparison(latest, report);
            }
            latest = report;
        }
        if (latest != null) return new Comparison(latest, null);
        throw new IOException("直近10日間に公表された株式相場表が見つからなかった");
    }

    static Report readReport(File pdf, LocalDate day, JpxStockUniverse universe, String edition) throws IOException {
        try {
            var table = JpxAndroidPdfReader.read(pdf, universe.codes(), day);
            var quotes = table.prices();
            var ambiguous = table.ambiguousCodes();
            // A valid PDF header does not guarantee a usable equity table. A layout
            // change or a partial CDN response must not advance the watch baseline.
            if (!hasUsableClose(quotes, ambiguous)) {
                throw new IOException("東証日報から普通株の有効な終値を取得できなかった");
            }
            return new Report(day, reportUrl(day), quotes, ambiguous, edition, universe);
        } catch (IllegalArgumentException | SecurityException error) {
            throw new IOException("東証日報のPDFを読み取れなかった", error);
        }
    }

    static boolean hasUsableClose(Map<String, JpxCloseTable.Sessions> quotes, Set<String> ambiguous) {
        for (var entry : quotes.entrySet()) {
            var sessions = entry.getValue();
            if (!ambiguous.contains(entry.getKey()) && sessions != null && sessions.close() != null
                    && sessions.close().signum() > 0) return true;
        }
        return false;
    }

    static List<LocalDate> candidateDays(LocalDate today) {
        var days = new ArrayList<LocalDate>();
        // Include today's report when JPX has already published it; 404 means not yet available.
        // Starting at yesterday silently leaves a published same-day close one session stale.
        for (int offset = 0; offset <= 10; offset++) {
            var day = today.minusDays(offset);
            if (day.getDayOfWeek() != DayOfWeek.SATURDAY && day.getDayOfWeek() != DayOfWeek.SUNDAY) {
                days.add(day);
            }
        }
        return days;
    }

    private static String reportUrl(LocalDate day) {
        String digits = day.format(DateTimeFormatter.BASIC_ISO_DATE);
        return REPORT_ROOT + digits.substring(0, 6) + "/stq_" + digits + ".pdf";
    }

    private static HttpsURLConnection open(String source) throws IOException {
        var connection = (HttpsURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(12_000);
        connection.setReadTimeout(20_000);
        connection.setInstanceFollowRedirects(false);
        connection.setUseCaches(false);
        return connection;
    }

    private static Edition head(LocalDate day) throws IOException {
        var connection = open(reportUrl(day));
        try {
            connection.setRequestMethod("HEAD");
            return edition(connection);
        } finally {
            connection.disconnect();
        }
    }

    private static Edition edition(HttpsURLConnection connection) throws IOException {
        int status = connection.getResponseCode();
        if (status == 404) return new Edition(false, "");
        if (status != 200) throw new IOException("JPXの応答 HTTP " + status);
        String version = connection.getHeaderField("x-amz-version-id");
        if (version != null && !version.equals("null") && version.matches("[A-Za-z0-9_.-]{1,128}")) {
            return new Edition(true, "version:" + version);
        }
        String tag = connection.getHeaderField("ETag");
        return new Edition(true, tag != null && tag.matches("\"[A-Za-z0-9_.-]{1,128}\"") ? "etag:" + tag : "");
    }

    private static Edition download(String source, File pdf) throws IOException {
        var connection = open(source);
        try {
            var result = edition(connection);
            if (!result.exists()) return result;
            if (connection.getContentLengthLong() > MAX_PDF_BYTES) {
                throw new IOException("東証日報のPDFが上限サイズを超えている");
            }
            try (var input = connection.getInputStream(); var output = new FileOutputStream(pdf)) {
                byte[] buffer = new byte[32_768];
                int total = 0;
                for (int count; (count = input.read(buffer)) != -1;) {
                    if (Thread.currentThread().isInterrupted()) throw new IOException("東証日報の確認を中断");
                    total += count;
                    if (total > MAX_PDF_BYTES) {
                        throw new IOException("東証日報のPDFが上限サイズを超えている");
                    }
                    output.write(buffer, 0, count);
                }
            }
            // A CDN or proxy can return an HTML error page with HTTP 200.
            // Never pass such a response to the Android PDF engine.
            try (var header = new FileInputStream(pdf)) {
                byte[] signature = new byte[5];
                if (header.read(signature) != signature.length
                        || signature[0] != '%' || signature[1] != 'P'
                        || signature[2] != 'D' || signature[3] != 'F'
                        || signature[4] != '-') {
                    throw new IOException("東証日報の取得内容がPDFではない");
                }
            }
            return result;
        } finally {
            connection.disconnect();
        }
    }
}
