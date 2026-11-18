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

    record Entry(LocalDate checkedThrough, JpxAnnualSummary.Annual annual, String hold) {
        String failure(String code, LocalDate day, Map<LocalDate, JpxDisclosureCalendar.Day> updates) {
            if (annual == null || !hold.isEmpty()) return hold;
            if (!annual.usable(day)) return "立会日時点の通期決算なし";
            if (annual.eps().signum() <= 0 || annual.bps().signum() <= 0) return "実績EPS・BPSのいずれかがゼロ以下";
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
            return "通期決算の自動取得 " + financials + " / 予算内 " + budget + "銘柄"
                    + " · 取得保留 " + (entries.size() - financials) + "銘柄 · 今回 " + fetched + "銘柄確認";
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
        }, stopped);
    }

    static Batch cached(Context context, JpxDailyCheck.Report report) {
        var state = context.getSharedPreferences("jpx-automatic-finance-v1", Context.MODE_PRIVATE);
        return refresh(state, report, LocalDate.now(TOKYO).minusDays(2), null, () -> true);
    }

    interface Sources {
        JpxIssuerArchive.Page archive(String code) throws IOException;
        String financial(JpxIssuerArchive.Disclosure disclosure) throws IOException;
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
        var pending = eligible.stream().filter(code -> due(entries.get(code), code, through, report.date(), updates))
                .sorted(Comparator.<String>comparingInt(code -> urgent(entries.get(code), code, report.date(), updates) ? 0 : 1)
                        .thenComparingInt(code -> -JpxDailyCheck.budgetQuantity(report.close(code)))
                        .thenComparing(code -> entries.containsKey(code) ? entries.get(code).checkedThrough() : LocalDate.MIN)
                        .thenComparing(Comparator.naturalOrder()))
                .toList();

        int checked = 0;
        long until = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(75);
        for (String code : pending) {
            if (checked >= BATCH_SIZE || stopped.getAsBoolean() || System.nanoTime() >= until) break;
            try {
                var entry = acquire(code, through, entries.get(code), sources);
                if (stopped.getAsBoolean()) break;
                state.edit().putString(PREFIX + code, encode(entry).toString()).apply();
                entries.put(code, entry);
                checked++;
            } catch (IOException unavailable) {
                // Preserve the last verified data and retry the interrupted batch at the next run.
                break;
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
        if (filing == null || filing.annualLink() == null) {
            return new Entry(through, null, "最新の通期決算サマリー未取得・訂正確認待ち");
        }
        String source = filing.annualLink().toString();
        var annual = old != null && old.annual() != null && source.equals(old.annual().source())
                && filing.day().equals(old.annual().released()) ? old.annual()
                : JpxAnnualSummary.read(sources.financial(filing), code, filing.day(), source);
        if (annual == null || !annual.usable(followingDay)) return new Entry(through, null, "通期EPS・BPSを照合できなかった");
        boolean clear = page.clearSince(annual.end().minusYears(1));
        return new Entry(through, annual, clear ? "" : "株式分割・併合等の開示を確認中");
    }

    private static Entry read(SharedPreferences state, String code, LocalDate through) {
        try {
            var json = new JSONObject(state.getString(PREFIX + code, "{}"));
            LocalDate checked = LocalDate.parse(json.getString("checked"));
            if (checked.isAfter(through)) return null;
            String hold = json.getString("hold");
            if (!json.has("source")) return new Entry(checked, null, hold);
            String source = json.getString("source");
            if (!JpxIssuerArchive.annualSource(source, code)) return null;
            var annual = new JpxAnnualSummary.Annual(LocalDate.parse(json.getString("end")),
                    LocalDate.parse(json.getString("released")), new BigDecimal(json.getString("eps")),
                    new BigDecimal(json.getString("bps")), source);
            return new Entry(checked, annual, hold);
        } catch (JSONException | IllegalArgumentException | java.time.DateTimeException invalid) {
            return null;
        }
    }

    private static JSONObject encode(Entry entry) {
        try {
            var json = new JSONObject().put("checked", entry.checkedThrough().toString()).put("hold", entry.hold());
            var annual = entry.annual();
            if (annual != null) json.put("end", annual.end().toString()).put("released", annual.released().toString())
                    .put("eps", annual.eps().toPlainString()).put("bps", annual.bps().toPlainString()).put("source", annual.source());
            return json;
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }
}
