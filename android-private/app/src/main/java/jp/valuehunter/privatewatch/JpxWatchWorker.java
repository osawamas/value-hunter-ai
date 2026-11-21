package jp.valuehunter.privatewatch;

import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.text.Html;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.io.IOException;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.HashSet;
import java.util.List;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class JpxWatchWorker extends Worker {
    static final String WORK = "jpx-daily-watch";
    static final String MANUAL = "jpx-daily-check-now";
    private static final String FINANCE = "jpx-annual-finance";
    private static final String FINANCE_PASS = "jpx_finance_pass";
    private static final String PERIODIC_FINANCE = "jpx_periodic_finance";
    private static final String TOKEN = "jpx_watch_token";
    private static final String BASELINE = "jpx_watch_baseline";
    private static final String LATEST = "jpx_watch_latest";
    private static final String PROCESSED = "jpx_watch_processed";
    private static final String ALERTED = "jpx_watch_alerted";
    private static final String PENDING = "jpx_watch_pending";
    private static final String CHECKED_AT = "jpx_watch_checked_at";
    private static final String OUTCOME = "jpx_watch_outcome";
    private static final DateTimeFormatter JAPAN_TIME = DateTimeFormatter.ofPattern("M月d日 HH:mm", Locale.JAPAN)
            .withZone(ZoneId.of("Asia/Tokyo"));
    static final String STATUS = "jpx_watch_status";
    private static final int NOTIFICATION_ID = 5;
    private static final int PRICE_NOTIFICATION_ID = 7;
    private static final int RAPID_NOTIFICATION_ID = 9;
    private static final BigDecimal RAPID_THRESHOLD = BigDecimal.valueOf(8);
    private static final String PRICE_ALERT_PREFIX = "price-budget:";
    private static final Object STATE_LOCK = new Object();
    private static final Object CHECK_LOCK = new Object();

    @FunctionalInterface
    interface ComparisonLoader {
        JpxDailyCheck.Comparison load(Context context, String processedKey, String rightsRevision) throws IOException;
    }

    @FunctionalInterface
    interface AlertSender {
        boolean post(Context context, int id, String title, String detail);
    }

    private final ComparisonLoader comparisons;
    private final Function<Context, JpxShareRights.Selection> rights;
    private final AlertSender alerts;
    private final boolean automaticFinance;

    public JpxWatchWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, (app, key, revision) -> JpxDailyCheck.checkWatch(app, key, revision),
                JpxShareRights::refresh, ScanWorker::postNotification, true);
    }

    JpxWatchWorker(Context context, WorkerParameters parameters, ComparisonLoader comparisons,
                   Function<Context, JpxShareRights.Selection> rights, AlertSender alerts) {
        this(context, parameters, comparisons, rights, alerts, false);
    }

    private JpxWatchWorker(Context context, WorkerParameters parameters, ComparisonLoader comparisons,
                           Function<Context, JpxShareRights.Selection> rights, AlertSender alerts,
                           boolean automaticFinance) {
        super(context, parameters);
        this.comparisons = comparisons;
        this.rights = rights;
        this.alerts = alerts;
        this.automaticFinance = automaticFinance;
    }

    static boolean enabled(Context context) {
        return !ScanWorker.prefs(context).getString(TOKEN, "").isEmpty();
    }

    static void setEnabled(Context context, boolean enabled) {
        if (enabled && !MarketNetwork.requested()) return;
        synchronized (STATE_LOCK) {
            var state = ScanWorker.prefs(context);
            var work = WorkManager.getInstance(context);
            if (enabled) {
                if (!enabled(context)) {
                    state.edit().putString(TOKEN, UUID.randomUUID().toString())
                            .putString(STATUS, "東証日報の確認を予約した").apply();
                }
                var request = new PeriodicWorkRequest.Builder(JpxWatchWorker.class, 6, TimeUnit.HOURS)
                        .setConstraints(connected()).build();
                work.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
                scheduleFinance(work, 0);
            } else {
                state.edit().remove(TOKEN).remove(BASELINE).remove(LATEST).remove(ALERTED).remove(PROCESSED)
                        .remove(STATUS).remove(CHECKED_AT).remove(OUTCOME).remove(PENDING).remove(MarketUpdate.JPX.lastUpdate).apply();
                work.cancelUniqueWork(WORK);
                work.cancelUniqueWork(MANUAL);
                work.cancelUniqueWork(FINANCE);
                var notifications = context.getSystemService(NotificationManager.class);
                notifications.cancel(NOTIFICATION_ID);
                notifications.cancel(PRICE_NOTIFICATION_ID);
                notifications.cancel(RAPID_NOTIFICATION_ID);
            }
        }
    }

    static boolean checkNow(Context context) {
        synchronized (STATE_LOCK) {
            if (!MarketNetwork.allowed() || !enabled(context)) return false;
            var request = new OneTimeWorkRequest.Builder(JpxWatchWorker.class)
                    .setConstraints(connected()).setInputData(financePass()).build();
            WorkManager.getInstance(context).enqueueUniqueWork(MANUAL, ExistingWorkPolicy.KEEP, request);
            return true;
        }
    }

    private static Data financePass() {
        return new Data.Builder().putBoolean(FINANCE_PASS, true).build();
    }

    private static void scheduleFinance(WorkManager work, long nextStart) {
        if (!MarketNetwork.requested()) return;
        var request = new PeriodicWorkRequest.Builder(JpxWatchWorker.class, 30, TimeUnit.MINUTES)
                .setConstraints(connected()).setInitialDelay(30, TimeUnit.MINUTES)
                .setInputData(new Data.Builder().putBoolean(FINANCE_PASS, true)
                        .putBoolean(PERIODIC_FINANCE, true).build());
        if (nextStart > 0) request.setNextScheduleTimeOverride(nextStart);
        work.enqueueUniquePeriodicWork(FINANCE, ExistingPeriodicWorkPolicy.UPDATE, request.build());
    }

    static long nextFinanceStart(long completed, boolean financePass, boolean periodicFinance,
                                 JpxAutomaticFinance.Batch batch) {
        boolean scheduled = !financePass || periodicFinance;
        return scheduled && batch.continueInitial() ? completed + TimeUnit.MINUTES.toMillis(15) : 0;
    }

    private static Constraints connected() {
        return MarketNetwork.constraints(NetworkType.CONNECTED);
    }

    private long networkGeneration;

    private boolean networkStopped() {
        return isStopped() || MarketNetwork.interrupted(networkGeneration);
    }

    private Result paused() {
        return MarketNetwork.pausedWork(networkGeneration);
    }

    @NonNull @Override public Result doWork() {
        synchronized (CHECK_LOCK) {
            networkGeneration = MarketNetwork.generation();
            if (networkStopped()) return paused();
            MarketUpdate.JPX.started();
            try {
                return check();
            } finally {
                MarketUpdate.JPX.finished();
            }
        }
    }

    private Result check() {
        if (networkStopped()) return paused();
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        String token = state.getString(TOKEN, "");
        if (token.isEmpty()) return Result.success();

        try {
            synchronized (STATE_LOCK) {
                if (!token.equals(state.getString(TOKEN, ""))) return Result.success();
                Result waiting = deliverPending(context, state, pendingAlerts(state));
                if (waiting != null) return waiting;
            }
            var evidence = rights.apply(context);
            var rapidEvidence = automaticFinance ? JpxRapidEvidence.refresh() : JpxRapidEvidence.unavailable();
            String revision = automaticFinance ? evidence.revision() + "|" + rapidEvidence.revision() : evidence.revision();
            if (networkStopped()) return paused();
            String processedKey = ScanWorker.alertsEnabled(context) ? state.getString(PROCESSED, "") : "";
            if (automaticFinance && getInputData().getBoolean(FINANCE_PASS, false)) processedKey = "";
            var comparison = comparisons.load(context, processedKey, revision);
            if (networkStopped()) return paused();
            if (comparison != null) {
                synchronized (STATE_LOCK) {
                    if (!token.equals(state.getString(TOKEN, ""))) return Result.success();
                    var recorded = dateOrNull(state.getString(LATEST, ""));
                    if (recorded != null && comparison.latest().date().isBefore(recorded)) {
                        recordCheck(state.edit(), "取得した日報が保存済みより古いため、前回の判定を保持").apply();
                        return Result.success();
                    }
                }
            }
            var finance = automaticFinance && comparison != null
                    ? JpxAutomaticFinance.refresh(context, comparison, evidence.rights(), this::networkStopped)
                    : JpxAutomaticFinance.Batch.empty();
            synchronized (STATE_LOCK) {
                if (networkStopped()) return paused();
                if (!token.equals(state.getString(TOKEN, ""))) return Result.success();
                if (comparison == null) {
                    MarketUpdate.JPX.completed(recordCheck(state.edit(), "日報と照合資料の版に変更なし · PDFの再取得を省略")).apply();
                    return Result.success();
                }
                var screen = comparison.screen(evidence.rights(), finance);
                LocalDate date = comparison.latest().date();
                var baseline = dateOrNull(state.getString(BASELINE, ""));
                var last = dateOrNull(state.getString(LATEST, ""));
                if (comparison.previous() == null) {
                    var partial = new StringBuilder("比較用の日報を取得できなかった");
                    partial.append("\n").append(date).append("の当日判定");
                    comparison.appendCoverage(partial, screen.assessed(), "\n", finance);
                    appendCandidates(partial, screen);
                    return retryReport(state, partial.toString());
                }
                var alerted = date.equals(last)
                        ? new HashSet<>(state.getStringSet(ALERTED, Set.of())) : new HashSet<String>();
                boolean notifyEnabled = ScanWorker.alertsEnabled(context);
                var added = notifyEnabled ? pending(baseline, last, date, screen.entered(), alerted)
                        : List.<JpxDailyCheck.Candidate>of();
                var priceOnly = comparison.priceOnly(screen);
                var budgetAdded = notifyEnabled && automaticFinance
                        ? pendingBudget(baseline, last, date, priceOnly.entered(), alerted)
                        : List.<PriceOnlyScreen.BudgetEntry>of();
                var exclusions = rapidEvidence.excluded(comparison.previous().date(), date);
                var rapid = rapidCandidates(comparison, screen, finance, exclusions);
                var rapidAdded = notifyEnabled ? pendingRapid(baseline, last, date, rapid, alerted)
                        : List.<PriceOnlyScreen.RapidMove>of();
                var summary = new StringBuilder(date + " 東証日報を確認 · 比較保留 " + screen.held() + "銘柄");
                summary.append("\n比較日 ").append(comparison.previous().date());
                comparison.appendCoverage(summary, screen.assessed(), "\n", finance);
                appendCandidates(summary, screen);
                appendHolds(summary, screen);
                summary.append("\n財務または株価で一次判定 ")
                        .append(screen.assessed() + priceOnly.assessed());
                if (comparison.latest().universe() != null) {
                    summary.append(" / ").append(comparison.latest().universe().codes().size());
                }
                summary.append("銘柄");
                summary.append("\n株価だけで予算判定 ").append(priceOnly.assessed())
                        .append("銘柄 · 100株10万円以下に入った ").append(priceOnly.entered().size()).append("銘柄");
                if (!priceOnly.entered().isEmpty()) {
                    summary.append("\n予算入り ").append(String.join("、",
                            priceOnly.entered().stream().map(PriceOnlyScreen.BudgetEntry::code).collect(Collectors.toUnmodifiableList())));
                }
                if (automaticFinance) summary.append("\n株価急変（前日比±8%以上） ")
                        .append(exclusions == null ? "権利落ち資料の確認待ち" : rapid.size() + "銘柄");
                if (!ScanWorker.notificationsRequested(context)) summary.append("\n無音通知はオフ");
                else if (!notifyEnabled) summary.append("\n通知設定を確認");
                LocalDate savedBaseline = baseline == null || last == null ? date : baseline;
                var update = recordCheck(state.edit(), "日報を取得して再判定")
                        .putString(BASELINE, savedBaseline.toString())
                        .putString(LATEST, date.toString()).putStringSet(ALERTED, alerted)
                        .putString(STATUS, summary.toString());
                var pending = pendingAlerts(state);
                queueAlerts(pending, date, added, budgetAdded, rapidAdded);
                String processed = notifyEnabled ? comparison.processedKey(revision) : "";
                // Commit the alert payload with its comparison before attempting Android delivery.
                update.putString(PROCESSED, pending.length() == 0 ? processed : "")
                        .putString(PENDING, pending.toString());
                if (!MarketUpdate.JPX.completed(update).commit()) return Result.retry();
                long nextFinance = nextFinanceStart(System.currentTimeMillis(),
                        getInputData().getBoolean(FINANCE_PASS, false),
                        getInputData().getBoolean(PERIODIC_FINANCE, false), finance);
                if (nextFinance > 0) scheduleFinance(WorkManager.getInstance(context), nextFinance);
                Result waiting = deliverPending(context, state, pending);
                if (waiting != null) return waiting;
                if (pending.length() == 0 && !state.edit().putString(PROCESSED, processed).commit()) {
                    return Result.retry();
                }
            }
            return Result.success();
        } catch (IOException error) {
            if (networkStopped()) return paused();
            synchronized (STATE_LOCK) {
                if (networkStopped()) return paused();
                if (!token.equals(state.getString(TOKEN, ""))) return Result.success();
                return retryReport(state, "日報を取得できなかった");
            }
        }
    }

    private static JSONArray pendingAlerts(SharedPreferences state) throws IOException {
        try {
            return new JSONArray(state.getString(PENDING, "[]"));
        } catch (JSONException invalid) {
            // Recover from a corrupt local queue using the saved report and sent-code list.
            if (!state.edit().remove(PENDING).remove(PROCESSED).commit()) throw new IOException(invalid);
            return new JSONArray();
        }
    }

    private Result deliverPending(Context context, SharedPreferences state, JSONArray pending) throws IOException {
        if (networkStopped()) return paused();
        if (pending.length() == 0) return null;
        if (!ScanWorker.notificationsRequested(context)) {
            if (!state.edit().remove(PENDING).commit()) return Result.retry();
            while (pending.length() > 0) pending.remove(pending.length() - 1);
            return null;
        }
        if (!ScanWorker.alertsEnabled(context)) return null;
        try {
            while (pending.length() > 0) {
                if (networkStopped()) return paused();
                var alert = pending.getJSONObject(0);
                if (!alerts.post(context, alert.getInt("id"), alert.getString("title"), alert.getString("detail"))) {
                    return networkStopped() ? paused() : retryReport(state, alert.getString("error"));
                }
                var sent = new HashSet<>(state.getStringSet(ALERTED, Set.of()));
                if (alert.getString("day").equals(state.getString(LATEST, ""))) {
                    var codes = alert.getJSONArray("codes");
                    for (int index = 0; index < codes.length(); index++) sent.add(codes.getString(index));
                }
                pending.remove(0);
                if (!state.edit().putString(PENDING, pending.toString()).putStringSet(ALERTED, sent).commit()) {
                    return Result.retry();
                }
            }
            return null;
        } catch (JSONException invalid) {
            if (!state.edit().remove(PENDING).remove(PROCESSED).commit()) return Result.retry();
            throw new IOException("Invalid JPX notification queue", invalid);
        }
    }

    private static void queueAlerts(JSONArray pending, LocalDate day,
                                    List<JpxDailyCheck.Candidate> added,
                                    List<PriceOnlyScreen.BudgetEntry> budget,
                                    List<PriceOnlyScreen.RapidMove> rapid) {
        if (!added.isEmpty()) {
            var detail = new StringBuilder(day + "の終値（参考）");
            for (var entry : added) detail.append("\n").append(entry.summary());
            queueAlert(pending, day, NOTIFICATION_ID, "東証日報で参考条件入り " + added.size() + "銘柄",
                    detail, added.stream().map(JpxDailyCheck.Candidate::code).collect(Collectors.toList()),
                    "無音通知を送信できなかった");
        }
        if (!budget.isEmpty()) {
            var detail = new StringBuilder(day + "の終値で100株の購入額を計算（手数料別）");
            for (var entry : budget) {
                detail.append("\n").append(entry.code()).append(" · ")
                        .append(entry.yen().stripTrailingZeros().toPlainString()).append("円");
            }
            queueAlert(pending, day, PRICE_NOTIFICATION_ID,
                    "東証・参考 100株10万円以下に入った " + budget.size() + "銘柄", detail,
                    budget.stream().map(entry -> PRICE_ALERT_PREFIX + entry.code()).collect(Collectors.toList()),
                    "予算入りの無音通知を送信できなかった");
        }
        if (!rapid.isEmpty()) {
            var detail = new StringBuilder(day + "の東証終値 · 分割・併合・配当落ち等を除外");
            for (var entry : rapid) {
                detail.append("\n").append(entry.code()).append(" · ")
                        .append(entry.percent().stripTrailingZeros().toPlainString()).append("%");
            }
            queueAlert(pending, day, RAPID_NOTIFICATION_ID, "東証・参考 株価急変 " + rapid.size() + "銘柄",
                    detail, rapid.stream().map(entry -> RAPID_ALERT_PREFIX + entry.code()).collect(Collectors.toList()),
                    "急変の無音通知を送信できなかった");
        }
    }

    private static void queueAlert(JSONArray pending, LocalDate day, int id, String title,
                                   StringBuilder detail, List<String> codes, String error) {
        pending.put(new JSONObject(java.util.Map.of("day", day.toString(), "id", id, "title", title,
                "detail", detail.toString(), "codes", new JSONArray(codes), "error", error)));
    }

    private Result retryReport(SharedPreferences state, String message) {
        boolean retry = getRunAttemptCount() < 2;
        recordCheck(state.edit(), retry ? message + " · 再試行を予約した" : message).apply();
        return retry ? Result.retry() : Result.success();
    }

    private static SharedPreferences.Editor recordCheck(SharedPreferences.Editor edit, String outcome) {
        return edit.putLong(CHECKED_AT, System.currentTimeMillis()).putString(OUTCOME, outcome);
    }

    static String displayStatus(SharedPreferences state) {
        var check = new StringBuilder();
        long last = state.getLong(CHECKED_AT, 0L);
        if (last > 0) {
            check.append("最終確認 ").append(JAPAN_TIME.format(Instant.ofEpochMilli(last))).append("（日本時間）");
            check.append("\n").append(state.getString(OUTCOME, ""));
        }
        String summary = state.getString(STATUS, "");
        if (!summary.isEmpty()) {
            if (check.length() > 0) check.append("\n");
            check.append(summary);
        }
        return check.toString();
    }

    private static void appendCandidates(StringBuilder message, JpxDailyCheck.Screening screen) {
        long priority = screen.candidates().stream()
                .filter(candidate -> candidate.level() == ValueCandidateScreen.Level.PRIORITY).count();
        message.append("\n優先候補 ").append(priority).append("銘柄 · 参考候補 ")
                .append(screen.candidates().size() - priority).append("銘柄");
        for (var candidate : screen.candidates()) message.append("\n").append(candidate.summary());
    }

    private static void appendHolds(StringBuilder message, JpxDailyCheck.Screening screen) {
        var byReason = new LinkedHashMap<String, List<String>>();
        for (var hold : screen.holds()) {
            String reason = Html.fromHtml(hold.reason(), Html.FROM_HTML_MODE_LEGACY).toString();
            byReason.computeIfAbsent(reason, ignored -> new ArrayList<>()).add(hold.code());
        }
        byReason.forEach((reason, codes) ->
                message.append("\n").append(String.join("・", codes)).append(" · ").append(reason));
    }

    static List<JpxDailyCheck.Candidate> pending(LocalDate baseline, LocalDate last, LocalDate date,
                                             List<JpxDailyCheck.Candidate> entered, Set<String> alerted) {
        if (baseline == null || last == null || !date.isAfter(baseline) || date.isBefore(last)) return List.of();
        if (!date.equals(last)) return entered;
        return entered.stream().filter(entry -> !alerted.contains(entry.code())).collect(Collectors.toUnmodifiableList());
    }

    static List<PriceOnlyScreen.BudgetEntry> pendingBudget(LocalDate baseline, LocalDate last, LocalDate date,
                                                             List<PriceOnlyScreen.BudgetEntry> entered,
                                                             Set<String> alerted) {
        if (baseline == null || last == null || !date.isAfter(baseline) || date.isBefore(last)) return List.of();
        if (!date.equals(last)) return entered;
        return entered.stream().filter(entry -> !alerted.contains(PRICE_ALERT_PREFIX + entry.code())).collect(Collectors.toUnmodifiableList());
    }

    private static final String RAPID_ALERT_PREFIX = "price-rapid:";

    static List<PriceOnlyScreen.RapidMove> rapidCandidates(JpxDailyCheck.Comparison comparison,
            JpxDailyCheck.Screening screen, JpxAutomaticFinance.Batch finance, Set<String> exclusions) {
        if (exclusions == null) return List.of();
        return comparison.verifiedRapidMoves(screen, finance,
                code -> !exclusions.contains(code), code -> !exclusions.contains(code), RAPID_THRESHOLD);
    }

    static List<PriceOnlyScreen.RapidMove> pendingRapid(LocalDate baseline, LocalDate last,
            LocalDate date, List<PriceOnlyScreen.RapidMove> entered, Set<String> alerted) {
        if (baseline == null || last == null || date == null || !date.isAfter(baseline)
                || date.isBefore(last)) return List.of();
        if (!date.equals(last)) return entered;
        return entered.stream().filter(entry ->
                !alerted.contains(RAPID_ALERT_PREFIX + entry.code())).collect(Collectors.toUnmodifiableList());
    }

    private static LocalDate dateOrNull(String text) {
        try {
            return LocalDate.parse(text);
        } catch (DateTimeParseException error) {
            return null;
        }
    }
}
