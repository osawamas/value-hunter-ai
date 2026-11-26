package jp.valuehunter.privatewatch;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.AtomicFile;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;


public final class UsDailyWorker extends Worker {
    private static final String WORK = "us-daily-closes";
    private static final String KEY_FILE = "massive-key.txt";
    private static final String VALUATION_DATE = "us_pilot_valuation_day";
    private static final String VALUATION_SOURCE = "us_pilot_valuation_source";
    private static final String VALUATION_TEXT = "us_pilot_valuation_text";
    private static final String VALUATION_RETRY = "us_pilot_valuation_retry";
    private static final String HISTORY_MONTH = "us_pilot_history_month";
    private static final String HISTORY_TEXT = "us_pilot_history_text";
    private static final String HISTORY_CURSOR = "us_pilot_history_cursor";
    private static final String MARKET_DATE = "us_market_coverage_date";
    private static final String MARKET_SOURCE = "us_market_coverage_source";
    private static final String MARKET_TEXT = "us_market_coverage_text";
    private static final String STATUS = "us_massive_daily_status";
    private static final String PROVIDER = "us_daily_close_provider";
    private static final String MASSIVE = UsDailyCloses.MASSIVE_SOURCE;
    private static final Object CHECK_LOCK = new Object();
    private static final String ARCHIVE_RECHECK_DAY = "listing_recheck_date";
    static final String ON_WIFI = "us-daily-closes-wifi-resume";
    static final Object QUOTE_LOCK = new Object();
    static final String PRIVATE_STATUS = "us_private_sec_status";
    private static final String PRIVATE_BASELINE = "us_private_sec_baseline";
    private static final String PRIVATE_PRIOR_BASELINE = "us_private_sec_prior_baseline";
    private static final String PRIVATE_SENT = "us_private_sec_sent";
    private static final String QUOTE_REPAIR_DAY = "us_quote_repair_day";
    private static final String QUOTE_REPAIR_CURSOR = "us_quote_repair_cursor";
    private static final String REPAIRED_SYMBOLS = "supplemented_symbols";
    private static final String REPAIR_CLOSES = "us_listing_repair_closes";
    private static final String REPAIR_SCREENED = "us_listing_repair_screened";
    private static final String REPAIR_METRICS_DAY = "us_listing_repair_metrics_day";
    private static final String QUOTE_REPAIR_AFTER = "us_quote_repair_after";
    private static final String PRIVATE_PENDING = "us_private_sec_pending";
    private static final String PRIVATE_PENDING_SIGNALS = "us_private_sec_pending_signals";
    private static final String PRIVATE_SCREEN_RECEIPT = "us_private_sec_screen_receipt_v2";
    private static final int US_NOTIFICATION_ID = 6;
    static final String PREVIOUS_QUOTE_FILE = "us-previous-daily-closes.json";
    static final String PRICE_ONLY_STATUS = "us_price_only_status";
    static final String PRICE_ONLY_DAY = "us_price_only_day";
    private static final String DATE = "us_massive_daily_close_date";
    private static final String COUNT = "us_massive_daily_close_count";
    private static final String ENDPOINT =
            "https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/";

    private final UsDoltCloses.Download repairSource;

    public UsDailyWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, address -> fetch(address, ""));
    }

    UsDailyWorker(Context context, WorkerParameters parameters, UsDoltCloses.Download repairSource) {
        super(context, parameters);
        this.repairSource = repairSource;
    }

    static void schedule(Context context) {
        if (!MarketNetwork.requested()) return;
        var workManager = WorkManager.getInstance(context);
        var request = new PeriodicWorkRequest.Builder(UsDailyWorker.class, 6, TimeUnit.HOURS)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .build();
        workManager.enqueueUniquePeriodicWork(WORK, ExistingPeriodicWorkPolicy.KEEP, request);
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_CLOSE, "定期更新");
    }

    static void checkNow(Context context) {
        if (!MarketNetwork.allowed()) return;
        var request = new OneTimeWorkRequest.Builder(UsDailyWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED)).build();
        WorkManager.getInstance(context).enqueueUniqueWork(ON_WIFI, ExistingWorkPolicy.KEEP, request);
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_CLOSE, "追加の更新");
    }

    static void recheckSingleSessionBudget(Context context, LocalDate day) {
        var data = new androidx.work.Data.Builder().putString("single_session_budget_day", day.toString()).build();
        var request = new OneTimeWorkRequest.Builder(UsDailyWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .setInputData(data).build();
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_BUDGET, "上場一覧との再照合");
        WorkManager.getInstance(context).enqueueUniqueWork("us-single-session-budget-" + day,
                ExistingWorkPolicy.KEEP, request);
    }

    static androidx.work.Data archiveRecheckData(LocalDate day) {
        return new androidx.work.Data.Builder().putString(ARCHIVE_RECHECK_DAY, day.toString()).build();
    }

    static androidx.work.Operation recheckAfterArchive(Context context, LocalDate day) {
        var data = archiveRecheckData(day);
        var request = new OneTimeWorkRequest.Builder(UsDailyWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.CONNECTED))
                .setInputData(data).setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES).build();
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_CLOSE, "日付別の終値補完");
        return WorkManager.getInstance(context).enqueueUniqueWork(
                "us-listing-recheck-" + day, ExistingWorkPolicy.KEEP, request);
    }

    static String displayStatus(Context context, SharedPreferences state) {
        String status = state.getString(STATUS, "初回の自動更新待ち");
        var finance = MarketFreshness.US_FINANCE;
        String proven = finance.result(state);
        if (finance.day(state) == null) {
            var baseline = readPrivateBaseline(state);
            if (baseline != null && !baseline.rows().isEmpty()) {
                int candidates = (int) baseline.rows().values().stream().filter(UsReferenceAlerts.Observation::candidate).count();
                proven = MarketFreshness.result(baseline.day(), baseline.rows().size(), candidates);
            }
        }
        var recent = new StringBuilder(proven);
        String closeWait = MarketFreshness.US_CLOSE.waiting(state);
        String financeWait = finance.waiting(state);
        if (!closeWait.isEmpty()) recent.append("\n終値 · ").append(closeWait);
        if (!financeWait.isEmpty()) recent.append("\n財務 · ").append(financeWait);
        recent.append("\n").append(status);
        String day = state.getString(DATE, "");
        if (day.isEmpty()) return recent.toString();
        String source = MASSIVE.equals(state.getString(PROVIDER, "")) ? "Massive" : "DoltHub参考値";
        String result = recent + "\n取得済み " + day + "（米東部） · " + source + " "
                + state.getInt(COUNT, 0) + "件";
        if (day.equals(state.getString(MARKET_DATE, ""))
                && state.getString(PROVIDER, "").equals(state.getString(MARKET_SOURCE, ""))) {
            result += "\n\n" + state.getString(MARKET_TEXT, "");
        }
        if (day.equals(state.getString(VALUATION_DATE, ""))
                && state.getString(PROVIDER, "").equals(state.getString(VALUATION_SOURCE, ""))) {
            result += "\n\n" + state.getString(VALUATION_TEXT, "");
        }
        String privateStatus = state.getString(PRIVATE_STATUS, "米国株の財務取得はWi-Fi接続時に開始");
        if (!privateStatus.isEmpty()) result += "\n\n" + privateStatus;
        if (day.equals(state.getString(PRICE_ONLY_DAY, ""))) {
            result += "\n\n" + state.getString(PRICE_ONLY_STATUS, "");
        }
        if (day.length() >= 7 && day.substring(0, 7).equals(state.getString(HISTORY_MONTH, ""))) {
            result += "\n\n" + state.getString(HISTORY_TEXT, "");
        }
        String single = context == null ? "" : UsSingleSessionBudgetCheck.display(context, state, day, state.getString(PROVIDER, ""));
        if (!single.isEmpty()) result += "\n\n" + single;
        String repair = repairStatus(state, day);
        return repair.isEmpty() ? result : result + "\n\n" + repair;
    }

    static String displayStatus(SharedPreferences state) {
        return displayStatus(null, state);
    }

    static String repairStatus(SharedPreferences state, String day) {
        if (!day.equals(state.getString(REPAIR_METRICS_DAY, ""))) return "";
        int closed = state.getInt(REPAIR_CLOSES, 0);
        if (closed == 0) return "";
        return day + " 分の再取得 · 終値補完 " + closed + "銘柄 · 割安判定まで完了 "
                + state.getInt(REPAIR_SCREENED, 0) + "銘柄";
    }

    private long networkGeneration;

    private boolean networkStopped() {
        return isStopped() || MarketNetwork.interrupted(networkGeneration);
    }

    private Result paused() {
        return MarketNetwork.pausedWork(networkGeneration);
    }

    @NonNull @Override public Result doWork() {
        var area = getInputData().getString("single_session_budget_day") != null
                ? DiagnosticLog.Area.US_BUDGET : DiagnosticLog.Area.US_CLOSE;
        return DiagnosticLog.work(getApplicationContext(), area, getRunAttemptCount(), this::runUpdate);
    }

    private Result runUpdate() {
        synchronized (CHECK_LOCK) {
            networkGeneration = MarketNetwork.generation();
            if (networkStopped()) return paused();
            String singleSession = getInputData().getString("single_session_budget_day");
            if (singleSession != null) {
                try {
                    UsSingleSessionBudgetCheck.run(getApplicationContext(), LocalDate.parse(singleSession),
                            this::networkStopped, repairSource);
                    return networkStopped() ? paused() : Result.success();
                } catch (DateTimeParseException invalid) {
                    return Result.failure();
                } catch (IOException | JSONException unavailable) {
                    return networkStopped() ? paused() : Result.retry();
                }
            }
            MarketUpdate.US_CLOSE.started();
            try {
                return check();
            } finally {
                MarketUpdate.US_CLOSE.finished();
            }
        }
    }

    private void updateAlertOutcomes(Context context, LocalDate day) {
        AlertOutcomes.update(context, AlertOutcomes.Market.US, day, this::networkStopped, range -> true,
                (range, symbols) -> UsDoltCloses.outcomePrices(range, symbols, address -> fetch(address, "")));
    }

    private Result check() {
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        String archived = getInputData().getString(ARCHIVE_RECHECK_DAY);
        if (archived == null) AlertOutcomes.recoverDeferred(context, AlertOutcomes.Market.US);
        LocalDate target = archived == null
                ? UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(Instant.now()))
                : LocalDate.parse(archived);
        try {
            String key = readKey(context);
            String provider = key.isEmpty() ? UsDoltCloses.SOURCE : MASSIVE;
            var file = new AtomicFile(new File(context.getNoBackupFilesDir(), "us-daily-closes.json"));
            LocalDate previous = cachedDate(file, state, provider);
            if (archived != null) {
                if (key.isEmpty() && previous != null && archived.equals(previous.toString())) {
                    supplementCloses(state, file, previous);
                    UsSecFinanceWorker.ensureScheduled(context);
                }
                return networkStopped() ? paused() : Result.success();
            }
            for (int offset = 0; offset < 7; offset++) {
                if (networkStopped()) return paused();
                LocalDate day = target.minusDays(offset);
                if (previous != null && !day.isAfter(previous)) {
                    boolean assess = needsValuation(state, previous, provider);
                    boolean count = needsCoverage(state, previous, provider);
                    if (assess || count) {
                        var snapshot = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
                        var closes = snapshot.getJSONArray("closes");
                        if (count) updateCoverage(state, closes, previous, provider);
                        if (assess) assess(state, closes, previous, provider);
                    }
                    if (previous.equals(target)) {
                        try {
                            if (key.isEmpty()) supplementCloses(state, file, previous);
                        } catch (IOException | JSONException unavailable) {
                            if (!networkStopped()) UsSecFinanceWorker.ensureScheduled(context);
                            throw unavailable;
                        }
                        backfillPrevious(context, previous, provider, key);
                    }
                    UsSecFinanceWorker.ensureScheduled(context);
                    updateHistory(state, previous);
                    if (networkStopped()) return paused();
                    var update = MarketUpdate.US_CLOSE.completed(state.edit())
                            .putString(STATUS, previous.equals(target) ? "終値を取得済み" : "保存済みの終値を表示中");
                    markQuoteFreshness(update, previous, target).apply();
                    updateAlertOutcomes(context, previous);
                    return Result.success();
                }
                if (!UsDailyCloses.tradingDay(day)) continue;

                var closes = fetchCloses(day, key);
                if (closes.length() == 0) continue;
                var snapshot = quoteSnapshot(day, provider, key, closes);
                if (networkStopped()) return paused();
                synchronized (QUOTE_LOCK) {
                    if (UsPriceOnlyBudget.previousSession(day).equals(previous)) {
                        var old = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
                        var priorFile = new AtomicFile(new File(context.getNoBackupFilesDir(), PREVIOUS_QUOTE_FILE));
                        writeSnapshot(priorFile, old);
                    }
                    writeSnapshot(file, snapshot);
                    var update = state.edit().putString(DATE, day.toString()).putInt(COUNT, closes.length())
                            .putString(PROVIDER, provider).putString(STATUS, "終値の自動取得に成功");
                    MarketFreshness.US_FINANCE.waiting(update, MarketFreshness.Phase.FINANCE, day);
                    markQuoteFreshness(update, day, target).apply();
                }
                if (day.equals(target)) backfillPrevious(context, day, provider, key);
                UsSecFinanceWorker.ensureScheduled(context);
                updateCoverage(state, closes, day, provider);
                assess(state, closes, day, provider);
                updateHistory(state, day);
                if (networkStopped()) return paused();
                MarketUpdate.US_CLOSE.completed(state.edit()).apply();
                updateAlertOutcomes(context, day);
                return Result.success();
            }
            report(state, "直近7日間の終値を取得できず", MarketFreshness.Phase.PUBLICATION, target);
            return Result.success();
        } catch (HttpStatus e) {
            if (networkStopped()) return paused();
            // Preserve the HTTP status without recording an address or private key.
            DiagnosticLog.record(context, DiagnosticLog.Area.US_CLOSE,
                    "終値の取得先がHTTP " + e.code + "を返した");
            boolean retry = e.code == 429 || e.code >= 500;
            report(state, "終値を取得できず（HTTP " + e.code + "）",
                    retry ? MarketFreshness.Phase.ERROR : MarketFreshness.Phase.NEXT_CHECK, target);
            return retry ? Result.retry() : Result.success();
        } catch (IOException e) {
            if (networkStopped()) return paused();
            // A retry status alone obscures the real failing method. Keep the
            // application stack and exception type, without URLs or secrets.
            DiagnosticLog.recordError(context, DiagnosticLog.Area.US_CLOSE,
                    "終値の通信・保存", e);
            report(state, "終値を取得できず（通信または保存エラー）", MarketFreshness.Phase.ERROR, target);
            return Result.retry();
        } catch (JSONException e) {
            if (networkStopped()) return paused();
            DiagnosticLog.recordError(context, DiagnosticLog.Area.US_CLOSE,
                    "終値の配信形式・保存データ", e);
            var phase = archived == null ? MarketFreshness.Phase.NEXT_CHECK : MarketFreshness.Phase.ERROR;
            report(state, "終値を取得できず（配信形式を要確認）", phase, target);
            return archived == null ? Result.success() : Result.retry();
        }
    }

    private static SharedPreferences.Editor markQuoteFreshness(SharedPreferences.Editor edit, LocalDate available,
                                                                LocalDate target) {
        return MarketFreshness.US_CLOSE.waiting(edit,
                available.isBefore(target) ? MarketFreshness.Phase.PUBLICATION : null, target);
    }

    private JSONArray fetchCloses(LocalDate day, String key) throws IOException, JSONException {
        if (!key.isEmpty()) {
            return UsDailyCloses.parse(fetch(ENDPOINT + day + "?adjusted=false&include_otc=false", key), day);
        }
        return UsDoltCloses.fetch(day, address -> {
            if (networkStopped()) throw new IOException("Worker stopped");
            try {
                return fetch(address, "");
            } catch (IOException first) {
                // One bounded retry for transient socket/handshake drops. A provider's
                // HTTP status must still be handled by the existing HTTP policy.
                if (first instanceof HttpStatus || networkStopped()) throw first;
                DiagnosticLog.record(getApplicationContext(), DiagnosticLog.Area.US_CLOSE,
                        "DoltHub通信の一時失敗 · " + first.getClass().getSimpleName()
                                + " · 1回だけ再接続");
                try {
                    Thread.sleep(1500);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new IOException("DoltHub retry interrupted", interrupted);
                }
                if (networkStopped()) throw first;
                return fetch(address, "");
            }
        });
    }

    private void supplementCloses(SharedPreferences state, AtomicFile file, LocalDate day)
            throws IOException, JSONException {
        if (!day.equals(MarketCoverage.US.day(state))) return;
        String date = day.toString();
        boolean sameDay = date.equals(state.getString(QUOTE_REPAIR_DAY, ""));
        long now = System.currentTimeMillis();
        if (sameDay && state.getLong(QUOTE_REPAIR_AFTER, 0) > now) return;
        byte[] original = readQuote(file);
        var snapshot = new JSONObject(new String(original, StandardCharsets.UTF_8));
        var closes = snapshot.getJSONArray("closes");
        var saved = UsDeviceFinancials.prices(closes).keySet();
        var groups = MarketCoverage.US.groups(state);
        var missing = new ArrayList<>(groups.getOrDefault(MarketCoverage.Reason.CLOSE, List.of()));
        missing.addAll(groups.getOrDefault(MarketCoverage.Reason.DATED_LISTING, List.of()));
        missing.retainAll(UsListingHistory.verifiedSupplementSymbols(getApplicationContext().getNoBackupFilesDir(), day));
        missing.removeAll(saved);
        if (missing.isEmpty()) return;
        String cursor = sameDay ? state.getString(QUOTE_REPAIR_CURSOR, "") : "";
        missing.sort(java.util.Comparator.comparing((String code) -> code.compareTo(cursor) <= 0)
                .thenComparing(java.util.Comparator.naturalOrder()));
        var targets = missing.subList(0, Math.min(100, missing.size()));
        var found = UsDoltCloses.supplement(day, Set.copyOf(targets), address -> {
            if (networkStopped()) throw new IOException("Worker stopped");
            return repairSource.get(address);
        });
        if (networkStopped()) return;
        var progress = state.edit().putString(QUOTE_REPAIR_DAY, date)
                .putLong(QUOTE_REPAIR_AFTER, now + TimeUnit.HOURS.toMillis(1))
                .putString(QUOTE_REPAIR_CURSOR, targets.get(targets.size() - 1));
        if (found.length() == 0) {
            progress.apply();
            return;
        }
        var repaired = repairedSymbols(snapshot);
        for (int index = 0; index < found.length(); index++) {
            var row = found.getJSONObject(index);
            closes.put(row);
            repaired.add(row.getString("symbol"));
        }
        snapshot.put("supplement_base_sha", UsReferenceAlerts.sha256(original))
                .put(REPAIRED_SYMBOLS, new JSONArray(new java.util.TreeSet<>(repaired)));
        synchronized (QUOTE_LOCK) {
            if (networkStopped()) return;
            writeSnapshot(file, snapshot);
            var savedProgress = closeRepairProgress(state, progress.putInt(COUNT, closes.length()), snapshot, day);
            MarketFreshness.US_FINANCE.waiting(savedProgress, MarketFreshness.Phase.FINANCE, day).apply();
        }
    }

    private static JSONObject quoteSnapshot(LocalDate day, String provider, String key, JSONArray closes)
            throws JSONException {
        return new JSONObject().put("source", provider)
                .put("adjusted", key.isEmpty() ? JSONObject.NULL : Boolean.FALSE)
                .put("trading_date_et", day.toString()).put("fetched_at_utc", Instant.now().toString())
                .put("closes", closes);
    }

    private void backfillPrevious(Context context, LocalDate day, String provider, String key) {
        if (networkStopped()) return;
        var priorDay = UsPriceOnlyBudget.previousSession(day);
        var priorFile = new AtomicFile(new File(context.getNoBackupFilesDir(), PREVIOUS_QUOTE_FILE));
        try {
            var saved = new JSONObject(new String(readQuote(priorFile), StandardCharsets.UTF_8));
            if (matchesPriorSnapshot(saved, priorDay, provider)) return;
        } catch (IOException | JSONException unavailable) {
            // A missing prior close can be filled independently of the current close.
        }
        try {
            var closes = fetchCloses(priorDay, key);
            if (closes.length() == 0 || networkStopped()) return;
            var snapshot = quoteSnapshot(priorDay, provider, key, closes);
            synchronized (QUOTE_LOCK) {
                writeSnapshot(priorFile, snapshot);
            }
        } catch (IOException | JSONException unavailable) {
            // Keep the current session available for financial screening and retry the prior close next run.
        }
    }

    static boolean matchesPriorSnapshot(JSONObject snapshot, LocalDate expected, String provider) {
        var closes = snapshot.optJSONArray("closes");
        return expected.toString().equals(snapshot.optString("trading_date_et"))
                && provider.equals(snapshot.optString("source")) && closes != null && closes.length() > 0;
    }

    static boolean applyFinancialScreen(Context context, SharedPreferences state, JSONObject ledger,
                                     LocalDate day, String provider, String closeHash,
                                     java.util.function.BooleanSupplier stopped) {
        return applyFinancialScreen(context, state, ledger, day, provider, closeHash, stopped, ScanWorker::postNotification);
    }

    @FunctionalInterface
    interface FinancialAlertSender {
        boolean post(Context context, int id, String title, String detail);
    }

    static boolean applyFinancialScreen(Context context, SharedPreferences state, JSONObject ledger,
                                        LocalDate day, String provider, String closeHash,
                                        java.util.function.BooleanSupplier stopped, FinancialAlertSender sender) {
        if (stopped.getAsBoolean() || !recoverSubmittedFinancialAlert(context, state)) return false;
        try {
            if (!day.toString().equals(ledger.optString("trading_date_et"))
                    || !provider.equals(ledger.optString("close_provider"))
                    || !closeHash.equals(ledger.optString("close_sha256"))) return true;
            var coverage = ledger.getJSONObject("coverage");
            int financials = coverage.getJSONObject("NYSE").getInt("with_close_and_reference_financials")
                    + coverage.getJSONObject("Nasdaq").getInt("with_close_and_reference_financials");
            String status = day + " · SEC財務・株数の自動照合 " + financials + "銘柄";
            if (!ledger.has("reference_screen")) {
                MarketFreshness.US_FINANCE.waiting(state.edit(), MarketFreshness.Phase.FINANCE, day)
                        .putString(PRIVATE_STATUS, status + " · 為替・分割資料待ち").apply();
                return true;
            }
            var screen = UsReferenceAlerts.read(ledger);
            if (!provider.equals(screen.provider()) || !closeHash.equals(screen.hash())) {
                throw new JSONException("Reference screen does not match the daily close");
            }
            var previous = readPrivateBaseline(state);
            if (previous != null && day.isBefore(previous.day())) return true;
            if (screen.rows().isEmpty()) {
                MarketFreshness.US_FINANCE.waiting(state.edit(), MarketFreshness.Phase.FINANCE, day)
                        .putString(PRIVATE_STATUS, status + " · 判定に使える財務・株数が未確認").apply();
                return true;
            }
            var reference = ledger.getJSONObject("reference_screen");
            String screenReceipt = financialScreenReceipt(day, provider, closeHash, reference,
                    state.getBoolean(ValueAlertPreview.LIVE, true),
                    state.getString(ValueAlertPreview.SETTINGS, ""),
                    ScanWorker.notificationsRequested(context), ScanWorker.systemAllowsAlerts(context),
                    state.getLong(ScanWorker.ALERT_GENERATION, 0),
                    state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0));
            if (previous != null && day.equals(previous.day())
                    && !hasPendingFinancialAlert(state)
                    && screenReceipt.equals(state.getString(PRIVATE_SCREEN_RECEIPT, ""))) return true;
            status += " · 参考判定 " + screen.rows().size() + "銘柄";
            long count = 0;
            for (var observation : screen.rows().values()) if (observation.candidate()) count++;
            status += " · 条件該当 " + count + "銘柄";
            var reasons = ledger.getJSONObject("reference_screen").optJSONObject("diagnostics");
            if (reasons != null) {
                int total = reasons.optInt("financial_records");
                int distinct = reasons.optInt("missing_close") + reasons.optInt("split_hold")
                        + reasons.optInt("unusable_financials") + reasons.optInt("outside_budget")
                        + reasons.optInt("outside_valuation") + reasons.optInt("reference")
                        + reasons.optInt("priority");
                if (distinct != total) throw new JSONException("Financial screen counts do not reconcile");
                String breakdown = "判定内訳（SEC有効財務 " + total + "件）"
                        + "\n財務・純資産が判定不可 " + reasons.optInt("unusable_financials") + "件"
                        + " · PER/PBR条件外 " + reasons.optInt("outside_valuation") + "件"
                        + "\n購入予算外（単元未満でも10万円超） " + reasons.optInt("outside_budget") + "件"
                        + " · 株式分割の照合待ち " + reasons.optInt("split_hold") + "件"
                        + "\n終値の照合待ち " + reasons.optInt("missing_close") + "件"
                        + " · 参考候補 " + reasons.optInt("reference") + "件"
                        + " · 優先候補 " + reasons.optInt("priority") + "件"
                        + "\n100株で10万円以内 " + reasons.optInt("affordable_100") + "件"
                        + " · 1株購入枠 " + reasons.optInt("single_share") + "件";
                status += "\n" + breakdown;
                DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                        "割安判定の除外理由を集計 · " + breakdown.replace('\n', ' '));
            }
            String pending = "";
            // A quote-source switch is not a new trading session. Retain the
            // already-submitted symbols and original prior-day comparison anchor
            // across same-day provider or close-hash corrections.
            boolean sameDay = previous != null && day.equals(previous.day());
            boolean alertsRequested = ScanWorker.notificationsRequested(context);
            var sent = sameDay ? new HashSet<>(state.getStringSet(PRIVATE_SENT, Set.of())) : new HashSet<String>();
            var queued = new java.util.HashMap<String, String>();
            long alertGeneration = state.getLong(ScanWorker.ALERT_GENERATION, 0);
            long financialGeneration = state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0);
            // Recalculate from the current screen, including same-day corrections to SEC evidence.
            // The queue only signals outstanding work; only the delivery receipt suppresses repeats.
            var anchor = sameDay ? readPrivateScreen(state, PRIVATE_PRIOR_BASELINE) : previous;
            var meter = reference.optJSONObject("meter_rows");
            boolean useMeter = state.getBoolean(ValueAlertPreview.LIVE, true);
            var meterHistory = ValueAlertPreview.history(state, ValueAlertPreview.Market.US);
            var meterPrior = meterHistory.latest();
            if (meterPrior != null && day.equals(meterPrior.day())) meterPrior = meterHistory.previous();
            if (meterPrior != null && (!provider.equals(meterPrior.source())
                    || !UsPriceOnlyBudget.previousSession(day).equals(meterPrior.day()))) meterPrior = null;
            var verifiedSymbols = new java.util.HashMap<String,String>();
            screen.rows().forEach((symbol, observation) -> verifiedSymbols.put(
                    UsReferenceAlerts.meterKey(observation.exchange(), observation.cik(), symbol),symbol));
            var ranks = useMeter && meter != null
                    ? ValueAlertPreview.discoveries(state, day, provider, meter, meterPrior, sent, verifiedSymbols::get)
                    : java.util.Map.<String, ValueAlertPreview.Entry>of();
            var entrants = useMeter ? java.util.Map.<String, String>of() : UsReferenceAlerts.entrantRows(anchor, screen, ValueAlertPreview.previouslyNotified(sent));
            String notificationState = ScanWorker.alertBlockReason(context);
            DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, "米国株の財務条件入り "
                    + (entrants.size() + ranks.size()) + "件 · " + (notificationState.isEmpty() ? "通知許可あり" : notificationState));
            if (alertsRequested) {
                var issuerNames = UsCompanyNames.read(context);
                if (!entrants.isEmpty()) {
                    pending = "米国株の参考条件入り " + entrants.size() + "銘柄"
                            + "\n" + day + "の終値（参考）\n"
                            + entrants.values().stream().map(row -> UsCompanyNames.decorate(row, issuerNames))
                                    .collect(java.util.stream.Collectors.joining("\n"));
                    entrants.keySet().forEach(symbol -> queued.put(symbol, "priority".equals(screen.rows().get(symbol).status())
                            ? "優先候補" : "参考候補"));
                } else if (!ranks.isEmpty()) {
                    pending = ValueAlertPreview.title("米国株", ranks).replace("新規・昇格", "発掘・昇格") + "\n" + day + "の終値（参考）\n"
                            + ranks.values().stream().map(ValueAlertPreview.Entry::summary)
                                    .map(row -> UsCompanyNames.decorate(row, issuerNames))
                                    .collect(java.util.stream.Collectors.joining("\n"));
                    ranks.forEach((key, row) -> queued.put(key, ValueAlertMeter.LABELS.get(row.level())));
                }
            }
            var baseline = new JSONObject().put("trading_date_et", day.toString())
                    .put("reference_screen", new JSONObject(reference,
                            new String[]{"provider", "close_sha256", "fx_date", "observations"}));
            var update = state.edit().putString(PRIVATE_BASELINE, baseline.toString())
                    .putString(PRIVATE_PENDING, pending)
                    .putString(PRIVATE_PENDING_SIGNALS, new JSONObject(queued).toString())
                    .putString(PRIVATE_SCREEN_RECEIPT, screenReceipt)
                    .putStringSet(PRIVATE_SENT, sent).putString(PRIVATE_STATUS, status);
            if (!sameDay) update.putString(PRIVATE_PRIOR_BASELINE, state.getString(PRIVATE_BASELINE, ""));
            if (meter != null) {
                try {
                    ValueAlertPreview.save(state, update, ValueAlertPreview.Market.US, day, provider, meter);
                } catch (JSONException unavailable) {
                    // A preview formatting failure must not stop financial alerts.
                }
            }
            MarketFreshness.US_FINANCE.verified(update, day, screen.rows().size(), (int) count, "");
            MarketFreshness.US_FINANCE.waiting(update, null, day);
            if (stopped.getAsBoolean() || !MarketUpdate.US_FINANCE.completed(update).commit()) return false;
            if (pending.isEmpty()) return true;
            if (!ScanWorker.systemAllowsAlerts(context)) {
                state.edit().putString(PRIVATE_STATUS, status + "\n無音通知は端末の通知許可待ち").apply();
                return true;
            }
            if (stopped.getAsBoolean()) return false;
            return deliverFinancialAlert(context, state, pending, alertGeneration, financialGeneration,
                    sent, queued, sender);
        } catch (JSONException | DateTimeParseException e) {
            MarketFreshness.US_FINANCE.waiting(state.edit(), MarketFreshness.Phase.NEXT_CHECK, day)
                    .putString(PRIVATE_STATUS, "財務自動更新の結果を読み取れず · 次回確認").apply();
            return true;
        }
    }

    static LocalDate targetDay(String archived, Instant now) {
        return archived == null
                ? UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(now))
                : LocalDate.parse(archived);
    }

    static String financialScreenReceipt(LocalDate day, String provider, String hash, JSONObject evidence,
                                         boolean meter, String thresholds, boolean requested, boolean allowed,
                                         long alertGeneration, long financialGeneration) {
        String identity = day + "\n" + provider + "\n" + hash + "\n" + evidence
                + "\n" + meter + "\n" + thresholds + "\n" + requested + "\n" + allowed
                + "\n" + alertGeneration + "\n" + financialGeneration;
        return UsReferenceAlerts.sha256(identity.getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    static boolean hasPendingFinancialAlert(SharedPreferences state) {
        return !state.getString(PRIVATE_PENDING, "").isEmpty();
    }

    private static boolean deliverFinancialAlert(Context context, SharedPreferences state, String pending,
                                                  long alertGeneration, long financialGeneration,
                                                  Set<String> sent, java.util.Map<String, String> queued,
                                                  FinancialAlertSender sender) {
        int separator = pending.indexOf('\n');
        var edit = state.edit().remove(PRIVATE_PENDING).remove(PRIVATE_PENDING_SIGNALS);
        if (separator < 0 || !ScanWorker.notificationsRequested(context)
                || alertGeneration != state.getLong(ScanWorker.ALERT_GENERATION, 0)
                || financialGeneration != state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0)) {
            return edit.commit();
        }
        String title = pending.substring(0, separator);
        String detail = pending.substring(separator + 1);
        if (!sender.post(context, US_NOTIFICATION_ID, title, detail)) return false;
        if (!AlertOutcomes.record(context, AlertOutcomes.Market.US, US_NOTIFICATION_ID, title, detail,
                outcomeSignals(queued))) return false;
        var delivered = new HashSet<>(sent);
        delivered.addAll(queued.keySet());
        return edit.putStringSet(PRIVATE_SENT, delivered).commit();
    }

    static boolean recoverSubmittedFinancialAlert(Context context, SharedPreferences state) {
        String pending = state.getString(PRIVATE_PENDING, "");
        int separator = pending.indexOf('\n');
        if (separator < 0) return true;
        try {
            String title = pending.substring(0, separator);
            String detail = pending.substring(separator + 1);
            long now = System.currentTimeMillis();
            JSONObject stored;
            try {
                stored = new JSONObject(state.getString(PRIVATE_PENDING_SIGNALS, "{}"));
            } catch (JSONException malformed) {
                // A never-submitted queue can be rebuilt from the latest validated
                // screen. A posted receipt must instead retain its original evidence.
                if (AlertOutcomes.deliveredEntry(context, US_NOTIFICATION_ID, title, detail, now) == null) {
                    DiagnosticLog.record(context, DiagnosticLog.Area.ALERT,
                            "米国株の未送信保留データが不正 · 最新判定で再計算");
                    return true;
                }
                throw malformed;
            }
            if (stored.length() == 0) {
                // Legacy pending text may belong to an alert that was never delivered.
                // Only preserve empty-signal pending state when its actual delivery
                // receipt exists; otherwise the current screen can safely rebuild it.
                if (AlertOutcomes.deliveredEntry(context, US_NOTIFICATION_ID, title, detail, now) == null)
                    return true;
                DiagnosticLog.record(context, DiagnosticLog.Area.ALERT,
                        "米国株の送信済み保留通知の銘柄記録が空 · 次回確認");
                return false;
            }
            var delivered = AlertOutcomes.deliveredEntry(context, US_NOTIFICATION_ID, title, detail, now);
            if (delivered == null) return true;
            var queued = new java.util.HashMap<String, String>();
            for (var keys = stored.keys(); keys.hasNext();) {
                String key = keys.next();
                queued.put(key, stored.getString(key));
            }
            NotificationHistory.restore(NotificationHistory.file(context), delivered, now);
            if (!AlertOutcomes.record(context, AlertOutcomes.Market.US, delivered, outcomeSignals(queued), now)) {
                return false;
            }
            var sent = new HashSet<>(state.getStringSet(PRIVATE_SENT, Set.of()));
            sent.addAll(queued.keySet());
            return state.edit().putStringSet(PRIVATE_SENT, sent)
                    .remove(PRIVATE_PENDING).remove(PRIVATE_PENDING_SIGNALS).commit();
        } catch (JSONException invalid) {
            DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, "米国株の保留通知の銘柄記録が不正 · 次回確認");
            // A corrupt pending signal is not proof that the posted alert was recovered.
            // Preserve the pending receipt rather than overwriting the original outcome.
            return false;
        } catch (IOException unavailable) {
            DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, "米国株の通知履歴を復元できず · 次回確認");
            return false;
        }
    }

    private static java.util.Map<String, String> outcomeSignals(java.util.Map<String, String> queued) {
        var signals = new java.util.HashMap<String, String>();
        queued.forEach((key, label) -> {
            String symbol = key.startsWith("meter:") && key.length() > 8 ? key.substring(8) : key;
            if (AlertOutcomes.validSymbol(symbol)) signals.put(symbol, label);
        });
        return signals;
    }

    private static UsReferenceAlerts.Screen readPrivateBaseline(SharedPreferences state) {
        return readPrivateScreen(state, PRIVATE_BASELINE);
    }

    private static UsReferenceAlerts.Screen readPrivateScreen(SharedPreferences state, String key) {
        String saved = state.getString(key, "");
        if (saved.isEmpty()) return null;
        try {
            return UsReferenceAlerts.read(new JSONObject(saved));
        } catch (JSONException invalid) {
            return null;
        }
    }

    private static boolean needsCoverage(SharedPreferences state, LocalDate day, String provider) {
        return !day.toString().equals(state.getString(MARKET_DATE, ""))
                || !provider.equals(state.getString(MARKET_SOURCE, ""));
    }

    private void updateCoverage(SharedPreferences state, JSONArray closes, LocalDate day, String provider) {
        if (networkStopped()) return;
        try {
            var nasdaq = UsMarketCoverage.directory(fetchText(UsMarketCoverage.DIRECTORY + "nasdaqlisted.txt", ""), true);
            var nyse = UsMarketCoverage.directory(fetchText(UsMarketCoverage.DIRECTORY + "otherlisted.txt", ""), false);
            JSONObject ledger = null;
            try (var input = getApplicationContext().getAssets().open(UsMarketCoverage.ASSET)) {
                ledger = new JSONObject(readText(input));
            } catch (FileNotFoundException absent) {
                // Close monitoring uses the live exchange directories even without a private SEC ledger.
            }
            var context = getApplicationContext();
            if (!networkStopped()) UsListingHistory.remember(context.getNoBackupFilesDir(), nyse, nasdaq);
            String summary = UsMarketCoverage.summarize(nyse, nasdaq, closes, day, ledger);
            if (!networkStopped()) state.edit().putString(MARKET_DATE, day.toString())
                    .putString(MARKET_SOURCE, provider).putString(MARKET_TEXT, summary).apply();
        } catch (IOException | JSONException unable) {
            // Retry the coverage comparison on the next periodic run, keeping the saved closes.
        }
    }

    private static boolean needsValuation(SharedPreferences state, LocalDate day, String provider) {
        return !day.toString().equals(state.getString(VALUATION_DATE, ""))
                || !provider.equals(state.getString(VALUATION_SOURCE, ""))
                || state.getBoolean(VALUATION_RETRY, false);
    }

    private void assess(SharedPreferences state, JSONArray closes, LocalDate day, String provider) {
        if (networkStopped()) return;
        UsDailyValuation.Report result;
        try {
            result = UsDailyValuation.assess(closes, day,
                    MASSIVE.equals(provider) ? "Massive参考判定" : "DoltHub参考判定", new UsDailyValuation.Fetch() {
                @Override public JSONObject facts(String address) throws IOException, JSONException {
                    if (networkStopped()) throw new IOException("Worker stopped");
                    return fetch(address, "");
                }

                @Override public JSONArray rates(String address) throws IOException, JSONException {
                    return new JSONArray(UsScanWorker.get(address, null));
                }

                @Override public java.util.Map<String, LocalDate> splits(LocalDate since, LocalDate session)
                        throws IOException, JSONException {
                    return UsDoltCloses.pilotSplits(since, session, address -> fetch(address, ""));
                }
            });
        } catch (IOException | JSONException e) {
            result = new UsDailyValuation.Report("参考判定は次の更新で再試行（為替または分割情報を取得できず）", true);
        }
        if (networkStopped()) return;
        state.edit().putString(VALUATION_DATE, day.toString()).putString(VALUATION_SOURCE, provider)
                .putString(VALUATION_TEXT, result.text()).putBoolean(VALUATION_RETRY, result.retry()).apply();
    }

    private void updateHistory(SharedPreferences state, LocalDate session) {
        YearMonth month = YearMonth.from(session);
        if (networkStopped() || month.toString().equals(state.getString(HISTORY_MONTH, ""))) return;
        YearMonth first = month.minusMonths(UsMonthlyHistory.MONTHS);
        if (!month.toString().equals(state.getString(HISTORY_CURSOR, ""))) {
            var reset = state.edit().putString(HISTORY_CURSOR, month.toString());
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                reset.remove(HISTORY_CURSOR + offset);
            }
            reset.apply();
        }
        var batches = new ArrayList<JSONArray>();
        try {
            // Retain completed annual queries for retries within the same refresh month.
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                if (networkStopped()) return;
                String key = HISTORY_CURSOR + offset;
                String cached = state.getString(key, "");
                JSONArray batch = cached.isEmpty()
                        ? UsDoltCloses.monthlyRows(first.plusMonths(offset), address -> fetch(address, ""))
                        : new JSONArray(cached);
                batches.add(batch);
                if (cached.isEmpty()) state.edit().putString(key, batch.toString()).apply();
            }
            var splits = UsDoltCloses.pilotSplits(first.atDay(1), session, address -> fetch(address, ""));
            String text = UsMonthlyHistory.summarize(batches, first, splits, UsDailyValuation.pilotSymbols());
            var update = state.edit().putString(HISTORY_MONTH, month.toString()).putString(HISTORY_TEXT, text);
            for (int offset = 0; offset < UsMonthlyHistory.MONTHS; offset += 12) {
                update.remove(HISTORY_CURSOR + offset);
            }
            if (!networkStopped()) update.apply();
        } catch (IOException e) {
            // Resume any completed annual queries on the next periodic update.
        } catch (JSONException e) {
            // Restart after an invalid response or cache, keeping the daily close available.
            state.edit().remove(HISTORY_CURSOR).apply();
        }
    }

    private static LocalDate cachedDate(AtomicFile file, SharedPreferences state, String provider) {
        try {
            var snapshot = new JSONObject(new String(readQuote(file), StandardCharsets.UTF_8));
            var date = LocalDate.parse(snapshot.getString("trading_date_et"));
            String storedProvider = snapshot.getString("source");
            var update = state.edit().putString(DATE, date.toString()).putString(PROVIDER, storedProvider)
                    .putInt(COUNT, snapshot.getJSONArray("closes").length());
            closeRepairProgress(state, update, snapshot, date).apply();
            return provider.equals(storedProvider) ? date : null;
        } catch (IOException | JSONException | DateTimeParseException e) {
            state.edit().remove(DATE).remove(COUNT).remove(PROVIDER).apply();
            return null;
        }
    }

    private static Set<String> repairedSymbols(JSONObject snapshot) {
        var result = new HashSet<String>();
        var entries = snapshot.optJSONArray(REPAIRED_SYMBOLS);
        if (entries != null) {
            for (int index = 0; index < entries.length(); index++) {
                var symbol = entries.optString(index);
                if (!symbol.isEmpty()) result.add(symbol);
            }
        }
        return result;
    }

    private static SharedPreferences.Editor closeRepairProgress(SharedPreferences state, SharedPreferences.Editor edit,
                                                                JSONObject snapshot, LocalDate day) {
        int count = repairedSymbols(snapshot).size();
        if (count == 0) return edit;
        if (!day.toString().equals(state.getString(REPAIR_METRICS_DAY, ""))) edit.putInt(REPAIR_SCREENED, 0);
        return edit.putString(REPAIR_METRICS_DAY, day.toString()).putInt(REPAIR_CLOSES, count);
    }

    static void screenRepairProgress(SharedPreferences state, JSONObject snapshot, JSONObject ledger, LocalDate day)
            throws JSONException {
        var symbols = repairedSymbols(snapshot);
        if (symbols.isEmpty()) return;
        int closed = symbols.size();
        symbols.retainAll(UsReferenceAlerts.read(ledger).rows().keySet());
        state.edit().putString(REPAIR_METRICS_DAY, day.toString()).putInt(REPAIR_CLOSES, closed)
                .putInt(REPAIR_SCREENED, symbols.size()).apply();
    }

    static byte[] readQuote(AtomicFile file) throws IOException {
        synchronized (QUOTE_LOCK) {
            return file.readFully();
        }
    }

    static void writeSnapshot(AtomicFile file, JSONObject snapshot) throws IOException {
        byte[] expected = snapshot.toString().getBytes(StandardCharsets.UTF_8);
        var stream = file.startWrite();
        try {
            stream.write(expected);
            file.finishWrite(stream);
        } catch (IOException e) {
            file.failWrite(stream);
            throw e;
        }
        // Some Android versions report failed final renames only in the system log.
        // Never mark a daily close or SEC checkpoint saved without verifying the bytes.
        if (!java.util.Arrays.equals(expected, file.readFully())) {
            throw new IOException("Could not verify atomic snapshot write");
        }
    }

    static JSONObject fetch(String address, String key) throws IOException, JSONException {
        return new JSONObject(fetchText(address, key));
    }

    static String fetchText(String address, String key) throws IOException, JSONException {
        return fetchText(address, key, null);
    }

    static String fetchText(String address, String key, Context owner) throws IOException, JSONException {
        var url = new URL(address);
        boolean sec = SecAccess.isSecHost(url.getHost());
        // Never impersonate a generic bot or send an invented address to EDGAR.
        String secIdentity = sec ? SecAccess.userAgent(owner == null
                ? "" : SecAccess.contact(owner)) : "";
        var connection = MarketNetwork.open(url);
        try {
            connection.setConnectTimeout(15_000);
            connection.setReadTimeout("www.dolthub.com".equalsIgnoreCase(url.getHost())
                    ? 60_000 : 30_000);
            connection.setInstanceFollowRedirects(false);
            if (!key.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + key);
            if (sec) {
                connection.setRequestProperty("User-Agent", secIdentity);
                connection.setRequestProperty("Accept", "application/json");
            }
            if ("www.dolthub.com".equalsIgnoreCase(url.getHost())) {
                connection.setRequestProperty("Accept", "application/json");
            }
            if ("api.nasdaq.com".equals(url.getHost())) {
                connection.setConnectTimeout(7_000);
                connection.setReadTimeout(7_000);
                connection.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36");
                connection.setRequestProperty("Accept", "application/json, text/plain, */*");
            }
            int code = MarketNetwork.response(connection);
            if (code != 200) throw new HttpStatus(code);
            try (var input = MarketNetwork.input(connection)) {
                return readText(input);
            }
        } finally {
            MarketNetwork.close(connection);
        }
    }

    private static String readText(java.io.InputStream input) throws IOException, JSONException {
        var output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (output.size() + count > UsDailyCloses.MAX_BYTES) {
                throw new JSONException("Daily summary exceeds size limit");
            }
            output.write(buffer, 0, count);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String readKey(Context context) throws IOException {
        try (var input = context.getAssets().open(KEY_FILE)) {
            byte[] bytes = new byte[257];
            int length = 0;
            int count;
            while (length < bytes.length && (count = input.read(bytes, length, bytes.length - length)) > 0) {
                length += count;
            }
            if (length == bytes.length) return "";
            String key = new String(bytes, 0, length, StandardCharsets.UTF_8).trim();
            return key.matches("[A-Za-z0-9_-]+") ? key : "";
        } catch (FileNotFoundException e) {
            return "";
        }
    }

    private static void report(SharedPreferences state, String status, MarketFreshness.Phase phase, LocalDate target) {
        MarketFreshness.US_CLOSE.waiting(state.edit().putString(STATUS, status), phase, target).apply();
    }

    static final class HttpStatus extends IOException {
        final int code;

        HttpStatus(int code) {
            this.code = code;
        }
    }
}
