package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.Map;
import java.util.function.BooleanSupplier;

/** Incrementally acquires public annual summaries for affordable JPX ordinary shares. */
final class JpxAutomaticFinance {
    private static final int BATCH_SIZE = 24;
    private static final int RECHECK_DAYS = 21;
    private static final int RETRY_MISSING_DAYS = 7;
    private static final ZoneId TOKYO = ZoneId.of("Asia/Tokyo");
    private static final String PREFIX = "annual-";
    private static final String RETRY_PREFIX = "retry-after-";

    record Entry(LocalDate checkedThrough, JpxAnnualSummary.Annual annual, String hold,
                 JpxAnnualSummary.Annual previousAnnual) {
        Entry(LocalDate checkedThrough, JpxAnnualSummary.Annual annual, String hold) {
            this(checkedThrough, annual, hold, null);
        }

        JpxAnnualSummary.Annual annualFor(LocalDate day) {
            if (annual != null && annual.usable(day)) return annual;
            return previousAnnual != null && previousAnnual.usable(day) ? previousAnnual : null;
        }

        String failure(String code, LocalDate day, Map<LocalDate, JpxDisclosureCalendar.Day> updates) {
            if (annual == null || !hold.isEmpty()) return hold;
            var asOf = annualFor(day);
            if (asOf == null) return "立会日時点の通期決算なし";
            if (asOf.eps().signum() <= 0 || asOf.bps().signum() <= 0) return "実績EPS・BPSのいずれかがゼロ以下";
            for (LocalDate next = checkedThrough.plusDays(1); !next.isAfter(day); next = next.plusDays(1)) {
                var update = updates.get(next);
                if (update == null) return "TDnet日次開示の確認待ち";
                if (update.rights().contains(code)) return "新しい分割・併合等の開示を確認中";
                if (next.isBefore(day) && update.annual().contains(code)) return "新しい通期決算の取得待ち";
            }
            return "";
        }
    }

    record Batch(Map<String, Entry> entries, Map<LocalDate, JpxDisclosureCalendar.Day> updates,
                 int budget, int fetched) {
        static Batch empty() { return new Batch(Map.of(), Map.of(), 0, 0); }

        String status() {
            if (budget == 0) return "";
            long financials = entries.values().stream().filter(entry -> entry.annual() != null).count();
            var message = new StringBuilder("通期決算の自動取得 ").append(financials)
                    .append(" / 予算内 ").append(budget).append("銘柄 · 取得保留 ")
                    .append(entries.size() - financials).append("銘柄 · 今回 ").append(fetched).append("銘柄確認");
            var holds = new java.util.TreeMap<String, Integer>();
            for (var entry : entries.values()) {
                if (entry.annual() == null) holds.merge(entry.hold(), 1, Integer::sum);
            }
            holds.forEach((reason, count) -> message.append("\n").append(reason).append(" ").append(count).append("銘柄"));
            return message.toString();
        }
    }

    private JpxAutomaticFinance() {}

    static Batch refresh(Context context, JpxDailyCheck.Comparison comparison, BooleanSupplier stopped) {
        var state = context.getSharedPreferences("jpx-automatic-finance-v1", Context.MODE_PRIVATE);
        var report = comparison.latest();
        var session = new JpxIssuerArchive.Session();
        // The company archive receives the current TDnet documents on the following day.
        // Use completed archive days and reconcile later dates against the dated TDnet lists.
        LocalDate through = LocalDate.now(TOKYO).minusDays(2);
        return refresh(state, report, through, new Sources() {
            @Override public JpxIssuerArchive.Page archive(String code) throws IOException {
                return session.archive(code);
            }

            @Override public String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                return session.annual(disclosure.annualLink());
            }

            @Override public LocalDate effective(JpxIssuerArchive.Disclosure disclosure) throws IOException {
                String key = "share-action-v1:" + disclosure.pdfLink();
                String saved = state.getString(key, "");
                try {
                    if (!saved.isEmpty()) return LocalDate.parse(saved);
                } catch (java.time.DateTimeException invalid) {
                    // Revalidate an invalid cached date from the official document.
                }
                var date = JpxCorporateActionDate.effective(
                        JpxCorporateActionDate.readPdf(disclosure.pdfLink(), context.getCacheDir()), disclosure);
                if (date != null && !stopped.getAsBoolean()) state.edit().putString(key, date.toString()).apply();
                return date;
            }
        }, stopped);
    }

    static Batch cached(Context context, JpxDailyCheck.Report report) {
        var state = context.getSharedPreferences("jpx-automatic-finance-v1", Context.MODE_PRIVATE);
        return refresh(state, report, LocalDate.now(TOKYO).minusDays(2), null, () -> true);
    }

    interface Sources {
        JpxIssuerArchive.Page archive(String code) throws IOException;
        String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException;
        default LocalDate effective(JpxIssuerArchive.Disclosure disclosure) throws IOException { return null; }
    }

    static Batch refresh(SharedPreferences state, JpxDailyCheck.Report report, LocalDate through,
                         Sources sources, BooleanSupplier stopped) {
        var entries = new HashMap<String, Entry>();
        var eligible = new ArrayList<String>();
        LocalDate earliest = report.date().isAfter(through) ? through.plusDays(1) : report.date().plusDays(1);
        for (String code : report.quotes().keySet()) {
            if (JpxDailyCheck.budgetQuantity(report.close(code)) == 0) continue;
            eligible.add(code);
            var entry = read(state, code, through);
            if (entry == null) continue;
            entries.put(code, entry);
            LocalDate tomorrow = entry.checkedThrough().plusDays(1);
            if (entry.annual() != null && entry.hold().isEmpty() && tomorrow.isBefore(earliest)) earliest = tomorrow;
        }
        var updates = JpxDisclosureCalendar.refresh(state, report.date(), earliest, stopped);
        long now = System.currentTimeMillis();
        var pending = eligible.stream()
                .filter(code -> state.getLong(RETRY_PREFIX + code, 0L) <= now)
                .filter(code -> due(entries.get(code), code, through, report.date(), updates))
                .sorted(Comparator.<String>comparingInt(code -> urgent(entries.get(code), code, report.date(), updates) ? 0 : 1)
                        // Finish first-time coverage before routine rechecks so the one-share queue can advance.
                        .thenComparingInt(code -> entries.containsKey(code) ? 1 : 0)
                        .thenComparingInt(code -> -JpxDailyCheck.budgetQuantity(report.close(code)))
                        .thenComparing(code -> entries.containsKey(code) ? entries.get(code).checkedThrough() : LocalDate.MIN)
                        .thenComparing(Comparator.naturalOrder()))
                .toList();

        int checked = 0;
        int attempted = 0;
        int consecutiveFailures = 0;
        long until = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(75);
        for (String code : pending) {
            if (attempted >= BATCH_SIZE || stopped.getAsBoolean() || System.nanoTime() >= until) break;
            attempted++;
            try {
                var entry = acquire(code, through, entries.get(code), sources);
                if (stopped.getAsBoolean()) break;
                state.edit().putString(PREFIX + code, encode(entry).toString()).remove(RETRY_PREFIX + code).apply();
                entries.put(code, entry);
                checked++;
                consecutiveFailures = 0;
            } catch (IOException unavailable) {
                if (unavailable instanceof JpxIssuerArchive.HttpFailure http
                        && (http.status == 429 || http.status == 503)) break;
                // Keep verified data and move on when an individual issuer stalls.
                state.edit().putLong(RETRY_PREFIX + code,
                        now + java.util.concurrent.TimeUnit.HOURS.toMillis(1)).apply();
                if (++consecutiveFailures >= 3) break;
            } catch (IllegalArgumentException | java.time.DateTimeException invalid) {
                var entry = new Entry(through, null, "東証の決算開示を確認できなかった");
                state.edit().putString(PREFIX + code, encode(entry).toString()).apply();
                entries.put(code, entry);
                checked++;
            }
        }
        return new Batch(Map.copyOf(entries), updates, eligible.size(), checked);
    }

    private static boolean urgent(Entry entry, String code, LocalDate day,
                                  Map<LocalDate, JpxDisclosureCalendar.Day> updates) {
        if (entry == null || entry.annual() == null || !entry.hold().isEmpty()) return false;
        for (var update : updates.entrySet()) {
            if (update.getKey().isAfter(entry.checkedThrough()) && !update.getKey().isAfter(day)
                    && (update.getValue().annual().contains(code) || update.getValue().rights().contains(code))) return true;
        }
        return false;
    }

    private static boolean due(Entry entry, String code, LocalDate through, LocalDate day,
                               Map<LocalDate, JpxDisclosureCalendar.Day> updates) {
        if (entry == null) return true;
        if (!entry.checkedThrough().isBefore(through)) return false;
        int retry = entry.annual() == null || !entry.hold().isEmpty() ? RETRY_MISSING_DAYS : RECHECK_DAYS;
        return urgent(entry, code, day, updates) || !entry.checkedThrough().plusDays(retry).isAfter(through);
    }

    static Entry acquire(String code, LocalDate through, Entry old, Sources sources) throws IOException {
        try {
            return fromPublicFiling(code, through, old, sources);
        } catch (JpxIssuerArchive.HttpFailure missing) {
            if (missing.status != 404 && missing.status != 410) throw missing;
            return new Entry(through, null, "公開の通期決算を取得できなかった");
        }
    }

    private static Entry fromPublicFiling(String code, LocalDate through, Entry old, Sources sources) throws IOException {
        var page = sources.archive(code);
        if (page == null) return new Entry(through, null, "東証の決算開示一覧を確認できなかった");
        LocalDate followingDay = through.plusDays(1);
        var filing = page.annualOn(followingDay);
        if (filing == null) return new Entry(through, null, "通期決算の開示を特定できなかった");
        if (filing.annualLink() == null) {
            String reason = filing.corrected() ? "訂正版のiXBRLなし" : "通期資料のiXBRLなし";
            return new Entry(through, null, reason);
        }
        String source = filing.annualLink().toString();
        var annual = old != null && old.annual() != null && source.equals(old.annual().source())
                && filing.day().equals(old.annual().released()) ? old.annual()
                : JpxAnnualSummary.read(sources.financial(filing), code, filing.day(), source, filing.corrected());
        if (annual == null || !annual.usable(followingDay)
                || filing.fiscalMonth() != null && !filing.fiscalMonth().equals(java.time.YearMonth.from(annual.end()))) return new Entry(through, null, "通期EPS・BPSを照合できなかった");
        JpxAnnualSummary.Annual previous = null;
        if (old != null) {
            // A session must only be valued with a filing that was already public.
            var last = old.annual();
            previous = last != null && last.released().isBefore(annual.released()) ? last : old.previousAnnual();
            if (previous != null && (!previous.released().isBefore(annual.released())
                    || !previous.usable(annual.released()))) previous = null;
        }
        var examined = new HashMap<java.net.URI, LocalDate>();
        if (previous != null && !consistentShareBasis(page, previous.end(), sources, examined)) previous = null;
        boolean clear = consistentShareBasis(page, annual.end(), sources, examined);
        return new Entry(through, annual, clear ? "" : "株式分割・併合等の開示を確認中", previous);
    }

    private static boolean consistentShareBasis(JpxIssuerArchive.Page page, LocalDate periodEnd,
                                                Sources sources, Map<java.net.URI, LocalDate> examined) {
        var since = periodEnd.minusYears(1);
        var relevant = page.disclosures().stream().filter(d -> !d.day().isBefore(since)
                && JpxIssuerArchive.shareChange(d.title())).distinct().toList();
        if (relevant.size() > 6) return false;
        for (var disclosure : relevant) {
            if (disclosure.day().isAfter(periodEnd) || disclosure.pdfLink() == null
                    || !JpxCorporateActionDate.supported(disclosure.title())) return false;
        }
        for (var disclosure : relevant) {
            var url = disclosure.pdfLink();
            if (!examined.containsKey(url)) {
                LocalDate date;
                try {
                    date = sources.effective(disclosure);
                } catch (IOException unavailable) {
                    date = null;
                }
                examined.put(url, date);
            }
            LocalDate date = examined.get(url);
            if (date == null || date.isBefore(disclosure.day()) || date.isAfter(periodEnd)) return false;
        }
        return true;
    }

    private static Entry read(SharedPreferences state, String code, LocalDate through) {
        try {
            var json = new JSONObject(state.getString(PREFIX + code, "{}"));
            LocalDate checked = LocalDate.parse(json.getString("checked"));
            if (checked.isAfter(through)) return null;
            String hold = json.getString("hold");
            var annual = decodeAnnual(json, code);
            var previous = json.optJSONObject("previous");
            return new Entry(checked, annual, hold, previous == null ? null : decodeAnnual(previous, code));
        } catch (JSONException | IllegalArgumentException | java.time.DateTimeException invalid) {
            return null;
        }
    }

    private static JpxAnnualSummary.Annual decodeAnnual(JSONObject object, String code) throws JSONException {
        if (!object.has("source")) return null;
        String source = object.getString("source");
        if (!JpxIssuerArchive.annualSource(source, code)) throw new JSONException("Invalid JPX filing source");
        return new JpxAnnualSummary.Annual(LocalDate.parse(object.getString("end")),
                LocalDate.parse(object.getString("released")), new BigDecimal(object.getString("eps")),
                new BigDecimal(object.getString("bps")), source);
    }

    private static JSONObject encode(Entry entry) {
        try {
            var json = new JSONObject().put("checked", entry.checkedThrough().toString()).put("hold", entry.hold());
            if (entry.annual() != null) encodeAnnual(json, entry.annual());
            if (entry.previousAnnual() != null) {
                json.put("previous", encodeAnnual(new JSONObject(), entry.previousAnnual()));
            }
            return json;
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    private static JSONObject encodeAnnual(JSONObject destination, JpxAnnualSummary.Annual annual) throws JSONException {
        return destination.put("end", annual.end().toString()).put("released", annual.released().toString())
                .put("eps", annual.eps().toPlainString()).put("bps", annual.bps().toPlainString())
                .put("source", annual.source());
    }
}
