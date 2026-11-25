package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;
import android.os.SystemClock;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/** Downloads SEC filings on-device and resumes through WorkManager between batches. */
public final class UsSecFinanceWorker extends Worker {
    private static final String WORK = "us-sec-financials-on-device";
    private static final String STATE = "us-sec-financials.json";
    private static final String QUOTES = "us-daily-closes.json";
    private static final String SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json";
    static final String FX = "https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY";
    private static final int BUDGET_NOTIFICATION_ID = 8;
    private static final int MAX_NASDAQ_CHECKS = 24;
    private static final int MAX_BUDGET_RETRIES = 3;
    private static final String BUDGET_CURSOR_DAY = "us_budget_cursor_day";
    private static final String BUDGET_CURSOR = "us_budget_cursor";
    static final String BUDGET_RESULTS_DAY = "us_budget_results_day";
    static final String BUDGET_RESULTS = "us_budget_results_json";
    private static final String BUDGET_SENT_DAY = "us_budget_sent_day";
    private static final String BUDGET_SENT_SYMBOLS = "us_budget_sent_symbols";
    private static final String NOCP_PAIR_KEY = "us_nocp_quote_pair";
    private static final String NOCP_RECEIPTS = "us_nocp_receipts";
    private static final Object CHECK_LOCK = new Object();
    private static final int BATCH = 40;
    private static final long REPAIR_DELAY = TimeUnit.HOURS.toMillis(1);
    private static final int REPAIR_ROUNDS = 2;
    private static final long BATCH_MILLIS = 45_000;
    private static final long BETWEEN_REQUESTS_MILLIS = 350;

    @FunctionalInterface
    interface Download {
        String get(String address) throws IOException, JSONException;
    }

    private final Download download;
    private String lastHttpErrorHost = "unknown";

    public UsSecFinanceWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        this(context, parameters, address -> UsDailyWorker.fetchText(address, "", context));
    }

    UsSecFinanceWorker(Context context, WorkerParameters parameters, Download download) {
        super(context, parameters);
        this.download = address -> {
            if (networkStopped()) throw new IOException("Worker stopped");
            try {
                return download.get(address);
            } catch (UsDailyWorker.HttpStatus error) {
                // Never save a complete URL, query string, API token or CIK in diagnostics.
                // Distinguish SEC, Nasdaq and other providers before investigating a 403.
                lastHttpErrorHost = new java.net.URL(address).getHost();
                throw error;
            }
        };
    }

    static void ensureScheduled(Context context) {
        enqueue(context, ExistingWorkPolicy.KEEP);
    }

    /** Append a fresh run after any in-flight SEC work instead of silently ignoring the save. */
    static void contactUpdated(Context context) {
        enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
    }

    private static void enqueue(Context context, ExistingWorkPolicy policy) {
        enqueue(context, policy, 0);
    }

    private static void enqueue(Context context, ExistingWorkPolicy policy, long delay) {
        if (!MarketNetwork.requested()) return;
        var request = new OneTimeWorkRequest.Builder(UsSecFinanceWorker.class)
                .setConstraints(MarketNetwork.constraints(NetworkType.UNMETERED))
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .setInitialDelay(delay, TimeUnit.MILLISECONDS).build();
        WorkManager.getInstance(context).enqueueUniqueWork(WORK, policy, request);
        DiagnosticLog.requested(context, DiagnosticLog.Area.US_FINANCE,
                delay == 0 ? "SEC財務の取得" : "SEC財務の再確認・待機 " + TimeUnit.MILLISECONDS.toMinutes(delay) + "分");
    }

    private long networkGeneration;

    private boolean networkStopped() {
        return isStopped() || MarketNetwork.interrupted(networkGeneration);
    }

    private Result paused() {
        return MarketNetwork.pausedWork(networkGeneration);
    }

    @NonNull @Override public Result doWork() {
        var area = DiagnosticLog.Area.US_FINANCE;
        return DiagnosticLog.work(getApplicationContext(), area, getRunAttemptCount(), this::runUpdate);
    }

    private Result runUpdate() {
        synchronized (CHECK_LOCK) {
            networkGeneration = MarketNetwork.generation();
            if (networkStopped()) return paused();
            MarketUpdate.US_FINANCE.started();
            try {
                return check();
            } finally {
                MarketUpdate.US_FINANCE.finished();
            }
        }
    }

    private Result check() {
        var context = getApplicationContext();
        var preferences = ScanWorker.prefs(context);
        AlertOutcomes.recoverDeferred(context, AlertOutcomes.Market.US);
        synchronized (UsDailyWorker.QUOTE_LOCK) {
            if (networkStopped()) return paused();
            if (!UsDailyWorker.recoverSubmittedFinancialAlert(context, preferences)) return Result.retry();
        }
        var directory = context.getNoBackupFilesDir();
        var closeFile = new AtomicFile(new File(directory, QUOTES));
        var checkpoint = new AtomicFile(new File(directory, STATE));
        LocalDate attemptedDay = null;
        try {
            byte[] bytes = UsDailyWorker.readQuote(closeFile);
            JSONObject quote = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            String hash = UsReferenceAlerts.sha256(bytes);
            var day = LocalDate.parse(quote.getString("trading_date_et"));
            attemptedDay = day;
            var provider = quote.getString("source");
            var prices = UsDeviceFinancials.prices(quote.getJSONArray("closes"));
            var verifiedListings = UsListingHistory.verifiedSupplementSymbols(directory, day);
            var scan = resume(checkpoint);
            if (scan == null || !hash.equals(scan.optString("hash"))) {
                var nasdaq = listings("nasdaqlisted.txt", true);
                var nyse = listings("otherlisted.txt", false);
                try {
                    UsCompanyNames.save(context, nyse, nasdaq);
                } catch (IOException unavailable) {
                    DiagnosticLog.record(context, DiagnosticLog.Area.ALERT,
                            "米国株の銘柄名保存を保留 · 銘柄コードでの通知は継続");
                }
                var scope = coverageScope(directory, day, nyse, nasdaq);
                var sec = new JSONObject(download.get(UsDeviceFinancials.SEC_DIRECTORY));
                var targets = UsDeviceFinancials.targets(nyse, nasdaq, sec, prices.keySet());
                var reuse = UsDeviceFinancials.reuseFrom(scan, day);
                boolean supplement = reuse != null && reuse.equals(day)
                        && scan.getString("hash").equals(quote.optString("supplement_base_sha"));
                var changed = targets.length() == 0 ? null : supplement ? Set.<Integer>of() : changedIssuers(reuse, day);
                var cachedEvidence = supplement ? scan.optJSONObject("valuation_evidence") : null;
                int repairRound = supplement ? scan.optInt("repair_round") : 0;
                if (networkStopped()) return paused();
                scan = UsDeviceFinancials.startScan(hash, day, targets, scan, changed);
                if (supplement) scan.put("valuation_evidence", cachedEvidence).put("repair_round", repairRound)
                        .put("supplement_recheck", true);
                saveCoverageScope(scan, scope);
                if (targets.length() == 0) {
                    publishCoverage(preferences, closeFile, scan, prices.keySet(), verifiedListings);
                    throw new IOException("No listed issuers matched the SEC directory");
                }
                int reused = scan.getInt("reused");
                updateProgress(day, 0, scan.getJSONArray("targets").length(), reused, reused);
                DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                        "SEC財務照合の対象を準備 " + (scan.getJSONArray("targets").length() + reused)
                                + "銘柄 · うち過去の有効財務を再利用 " + reused
                                + "件 · 新規または再確認 " + scan.getJSONArray("targets").length()
                                + "銘柄 · 取引日 " + day);
                UsDailyWorker.writeSnapshot(checkpoint, scan);
                publishCoverage(preferences, closeFile, scan, prices.keySet(), verifiedListings);
            } else if (!scan.has("coverage_listing_date")) {
                // Add a dated scope to a checkpoint created before coverage was available.
                saveCoverageScope(scan, UsListingHistory.retainedScope(directory, day));
                UsDailyWorker.writeSnapshot(checkpoint, scan);
            }
            boolean latestSession = day.equals(UsDailyCloses.onOrBeforeTradingDay(
                    UsDailyCloses.mostRecentEligibleDay(Instant.now())));
            long repairAfter = scan.optLong("repair_after");
            if (latestSession && repairAfter > 0 && repairAfter <= System.currentTimeMillis()
                    && prepareRepair(scan)) {
                DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                        "未取得・照合待ちの再確認を開始 · 前回の有効財務 "
                                + scan.optInt("reused") + "件を再利用 · 再確認対象 "
                                + scan.getJSONArray("targets").length() + "銘柄 · "
                                + scan.optInt("repair_round") + "/" + REPAIR_ROUNDS + "巡目");
                UsDailyWorker.writeSnapshot(checkpoint, scan);
            }
            var targets = scan.getJSONArray("targets");
            var results = scan.getJSONArray("results");
            int position = scan.getInt("cursor");
            int reused = scan.optInt("reused", 0);
            if (reused < 0 || reused > results.length() || position < 0 || position > targets.length()
                    || results.length() > position + reused) {
                checkpoint.delete();
                return Result.retry();
            }

            if (position < targets.length()) {
                long deadline = SystemClock.elapsedRealtime() + BATCH_MILLIS;
                try {
                    int end = Math.min(targets.length(), position + BATCH);
                    while (position < end && !networkStopped() && SystemClock.elapsedRealtime() < deadline) {
                        var target = targets.getJSONObject(position);
                        JSONObject row;
                        try {
                            row = facts(target, day);
                        } catch (IOException unavailable) {
                            if (!networkStopped()) scan.put("coverage_failed", target.getString("symbol"));
                            throw unavailable;
                        }
                        if (networkStopped()) break;
                        scan.remove("coverage_failed");
                        if (row != null) results.put(row);
                        scan.put("cursor", ++position);
                        if (position < end) Thread.sleep(BETWEEN_REQUESTS_MILLIS);
                    }
                } finally {
                    UsDailyWorker.writeSnapshot(checkpoint, scan);
                    updateProgress(day, position, targets.length(), results.length(), reused);
                    DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                            "SEC財務の分割取得 " + (position + reused) + " / "
                                    + (targets.length() + reused) + "銘柄 · 有効な財務 "
                                    + results.length() + "件 · " + (position < targets.length()
                                    ? "次のバッチへ" : "財務照合へ"));
                    publishCoverage(preferences, closeFile, scan, prices.keySet(), verifiedListings);
                }
                if (networkStopped()) return paused();
                if (position < targets.length()) {
                    enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
                    return Result.success();
                }
            }

            if (networkStopped()) return paused();
            var ledger = scan.optJSONObject("ledger");
            if (!UsReferenceAlerts.hasTradeDateFx(ledger, day)
                    || (!ledger.getJSONObject("reference_screen").has("meter_rows")
                    && scan.optJSONObject("valuation_evidence") != null)) {
                var evidence = scan.optJSONObject("valuation_evidence");
                if (evidence == null) {
                    var rates = new JSONArray(download.get(
                            FX + "&from=" + day.minusDays(UsScreen.FX_LOOKBACK_DAYS) + "&to=" + day));
                    var fx = tradeDateFx(rates, day);
                    var splits = UsDoltCloses.allSplits(day.minusDays(150), day,
                            url -> new JSONObject(download.get(url)));
                    var dates = new JSONObject();
                    for (var entry : splits.entrySet()) dates.put(entry.getKey(), entry.getValue().toString());
                    evidence = new JSONObject().put("fx_rate", fx.yenPerDollar()).put("splits", dates);
                    scan.put("valuation_evidence", evidence);
                }
                var fx = new UsScreen.Fx(day, evidence.getDouble("fx_rate"));
                var splitDates = evidence.getJSONObject("splits");
                var splits = new java.util.HashMap<String, LocalDate>();
                var symbols = splitDates.keys();
                while (symbols.hasNext()) {
                    var symbol = symbols.next();
                    splits.put(symbol, LocalDate.parse(splitDates.getString(symbol)));
                }
                ledger = UsDeviceFinancials.screen(day, provider, hash, results, prices, fx, splits);
                scan.put("ledger", ledger).remove("retained_ledger");
                scan.remove("supplement_recheck");
                UsDailyWorker.writeSnapshot(checkpoint, scan);
            }
            var budget = prepareBudget(quote, ledger, directory, day, hash, preferences);
            synchronized (UsDailyWorker.QUOTE_LOCK) {
                if (networkStopped()) return paused();
                if (!hash.equals(UsReferenceAlerts.sha256(closeFile.readFully()))) {
                    if (!networkStopped()) enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
                    return Result.success();
                }
                publishCoverage(preferences, closeFile, scan, prices.keySet(), verifiedListings);
                if (!UsDailyWorker.applyFinancialScreen(context, preferences, ledger, day, provider, hash, this::networkStopped)) {
                    return networkStopped() ? paused() : Result.retry();
                }
                if (!networkStopped()) {
                    UsDailyWorker.screenRepairProgress(preferences, quote, ledger, day);
                    if (!applyBudget(context, preferences, day, budget)) return networkStopped() ? paused() : Result.retry();
                    if (budget != null && budget.retry() && getRunAttemptCount() < MAX_BUDGET_RETRIES) {
                        return Result.retry();
                    }
                    if (budget != null && budget.official().more() && !budget.official().retry())
                        enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE);
                }
            }
            if (networkStopped()) return paused();
            if (latestSession && scan.optLong("repair_after") == 0 && scan.optInt("repair_round") < REPAIR_ROUNDS
                    && repairTargets(scan).length() > 0) {
                scan.put("repair_after", System.currentTimeMillis() + REPAIR_DELAY);
                UsDailyWorker.writeSnapshot(checkpoint, scan);
                enqueue(context, ExistingWorkPolicy.APPEND_OR_REPLACE, REPAIR_DELAY);
            }
            DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                    "SEC財務の今回の処理が完了 · 取引日 " + day + " · 判定記録を保存");
            return Result.success();
        } catch (FileNotFoundException absent) {
            // The US daily-close worker will enqueue us again after it saves quotes.
            // Keep this distinct from a genuine SEC fetch success in diagnostics.
            DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                    "米国株終値の保存待ち · SEC財務の取得は未開始");
            return Result.success();
        } catch (SecAccess.MissingContactException absent) {
            // A real SEC contact must be supplied in Settings; retrying cannot fix this.
            DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                    "SEC連絡先未設定 · 設定後に取得を再開");
            MarketFreshness.US_FINANCE.waiting(preferences.edit(),
                    MarketFreshness.Phase.FINANCE, attemptedDay).apply();
            return Result.success();
        } catch (InterruptedException cancelled) {
            Thread.currentThread().interrupt();
            return Result.retry();
        } catch (IOException | JSONException | DateTimeParseException unavailable) {
            if (networkStopped()) return paused();
            boolean secAccessDenied = unavailable instanceof UsDailyWorker.HttpStatus http
                    && http.code == 403 && SecAccess.isSecHost(lastHttpErrorHost);
            if (unavailable instanceof UsDailyWorker.HttpStatus http) {
                DiagnosticLog.record(context, DiagnosticLog.Area.US_FINANCE,
                        "米国株財務取得先 " + lastHttpErrorHost + " · HTTP " + http.code
                                + (secAccessDenied ? " · SECアクセス拒否・再試行を停止" : " · 次回の再試行待ち"));
            } else {
                DiagnosticLog.recordError(context, DiagnosticLog.Area.US_FINANCE,
                        "SEC財務の取得・解析", unavailable);
            }
            String progress = preferences.getString(UsDailyWorker.PRIVATE_STATUS, "");
            synchronized (UsDailyWorker.QUOTE_LOCK) {
                var market = MarketFreshness.US_FINANCE;
                var latest = market.target(preferences);
                if (latest == null || attemptedDay == null || !latest.isAfter(attemptedDay)) {
                    var edit = market.waiting(preferences.edit(), MarketFreshness.Phase.ERROR, attemptedDay);
                    if (!progress.endsWith(" · 再試行待ち")) {
                        edit.putString(UsDailyWorker.PRIVATE_STATUS,
                                (progress.isEmpty() ? "米国株の財務データ待ち" : progress) + " · 再試行待ち");
                    }
                    edit.apply();
                }
            }
            // SEC 403 is not transient; repeatedly retrying it violates fair-access intent.
            // An explicit contact-settings save schedules a fresh attempt instead.
            return secAccessDenied ? Result.success() : Result.retry();
        }
    }

    static JSONArray repairTargets(JSONObject scan) throws JSONException {
        var results = scan.getJSONArray("results");
        var targets = scan.getJSONArray("targets");
        var ledger = scan.optJSONObject("ledger");
        var holds = ledger == null ? null : ledger.optJSONArray("split_holds");
        var splitHolds = new HashSet<String>();
        if (holds != null) {
            for (int index = 0; index < holds.length(); index++) splitHolds.add(holds.getString(index));
        }
        var ready = new HashSet<String>();
        var repair = new JSONArray();
        for (int index = 0; index < results.length(); index++) {
            var row = results.getJSONObject(index);
            var symbol = row.getString("symbol");
            ready.add(symbol);
            if (splitHolds.contains(symbol)) repair.put(row);
        }
        for (int index = 0; index < targets.length(); index++) {
            var target = targets.getJSONObject(index);
            if (!ready.contains(target.getString("symbol"))) repair.put(target);
        }
        return repair;
    }

    static boolean prepareRepair(JSONObject scan) throws JSONException {
        if (scan.optJSONObject("ledger") == null || scan.optInt("repair_round") >= REPAIR_ROUNDS) return false;
        var repair = repairTargets(scan);
        if (repair.length() == 0) return false;
        var wanted = new HashSet<String>();
        for (int index = 0; index < repair.length(); index++) wanted.add(repair.getJSONObject(index).getString("symbol"));
        var rows = scan.getJSONArray("results");
        var retained = new JSONArray();
        for (int index = 0; index < rows.length(); index++) {
            var row = rows.getJSONObject(index);
            if (!wanted.contains(row.getString("symbol"))) retained.put(row);
        }
        scan.put("targets", repair).put("results", retained).put("cursor", 0).put("reused", retained.length())
                .put("repair_round", scan.optInt("repair_round") + 1).remove("repair_after");
        scan.put("retained_ledger", scan.getJSONObject("ledger")).remove("ledger");
        return true;
    }

    private static UsListingHistory.DatedScope coverageScope(File directory, LocalDate day,
                                                            UsMarketCoverage.Directory nyse,
                                                            UsMarketCoverage.Directory nasdaq) {
        try {
            var saved = UsListingHistory.remember(directory, nyse, nasdaq);
            return UsListingHistory.coverageScope(saved, day, nyse, nasdaq);
        } catch (JSONException unavailable) {
            return null;
        }
    }

    private static void saveCoverageScope(JSONObject scan, UsListingHistory.DatedScope scope) throws JSONException {
        if (scope != null) scan.put("coverage_symbols", new JSONArray(scope.symbols()));
        scan.put("coverage_listing_date", scope == null ? "" : scope.day().toString());
    }

    private static void publishCoverage(android.content.SharedPreferences preferences, AtomicFile closeFile,
                                        JSONObject scan, Set<String> closes, Set<String> verified) {
        try {
            if (scan.optBoolean("supplement_recheck") && scan.optJSONObject("ledger") == null) return;
            var snapshot = coverage(scan, closes, verified);
            if (snapshot == null) return;
            synchronized (UsDailyWorker.QUOTE_LOCK) {
                if (!scan.getString("hash").equals(UsReferenceAlerts.sha256(closeFile.readFully()))) return;
                MarketCoverage.US.track(preferences, preferences.edit(), snapshot,
                        scan.optJSONObject("ledger") != null).apply();
            }
        } catch (IOException | JSONException | DateTimeParseException unavailable) {
            // The previous dated coverage remains available while this snapshot cannot be verified.
        }
    }

    static MarketCoverage.Snapshot coverage(JSONObject scan, Set<String> closes) throws JSONException {
        return coverage(scan, closes, null);
    }

    static MarketCoverage.Snapshot coverage(JSONObject scan, Set<String> closes, Set<String> verified) throws JSONException {
        var scope = scan.optJSONArray("coverage_symbols");
        if (scope == null) return null;
        var ordinary = new HashSet<String>();
        for (int index = 0; index < scope.length(); index++) ordinary.add(scope.getString(index));
        var reasons = new java.util.HashMap<String, MarketCoverage.Reason>();
        for (String symbol : ordinary) reasons.put(symbol, MarketCoverage.Reason.IDENTIFICATION);
        var targets = scan.getJSONArray("targets");
        for (int index = 0; index < targets.length(); index++) {
            reasons.put(targets.getJSONObject(index).getString("symbol"), MarketCoverage.Reason.FINANCIALS);
        }
        var results = scan.getJSONArray("results");
        for (int index = 0; index < results.length(); index++) {
            reasons.put(results.getJSONObject(index).getString("symbol"), MarketCoverage.Reason.VALUATION);
        }

        var ledger = scan.optJSONObject("ledger");
        if (ledger == null) ledger = scan.optJSONObject("retained_ledger");
        Set<String> screened = Set.of();
        var day = LocalDate.parse(scan.getString("day"));
        if (UsReferenceAlerts.hasTradeDateFx(ledger, day)
                && scan.getString("hash").equals(ledger.optString("close_sha256"))) {
            screened = UsReferenceAlerts.read(ledger).rows().keySet();
            for (int index = 0; index < results.length(); index++) {
                var row = results.getJSONObject(index);
                if (UsDeviceFinancials.nonPositiveFinancials(row)) {
                    reasons.put(row.getString("symbol"), MarketCoverage.Reason.NON_POSITIVE_FINANCIALS);
                }
            }
            var splits = ledger.optJSONArray("split_holds");
            if (splits != null) {
                for (int index = 0; index < splits.length(); index++) {
                    reasons.put(splits.getString(index), MarketCoverage.Reason.CORPORATE_ACTION);
                }
            }
        }

        var failed = scan.optString("coverage_failed");
        if (!failed.isEmpty()) reasons.put(failed, MarketCoverage.Reason.DOWNLOAD);
        if (verified != null) {
            for (String symbol : ordinary) {
                if (!closes.contains(symbol) && !verified.contains(symbol)) {
                    reasons.put(symbol, MarketCoverage.Reason.DATED_LISTING);
                }
            }
        }
        return MarketCoverage.build(day, LocalDate.parse(scan.getString("coverage_listing_date")),
                ordinary, closes, screened, reasons);
    }

    record BudgetCheck(UsPriceOnlyBudget.Result result, String cursor, boolean retry,
                       UsNasdaqRecovery.Result official, boolean exactListings) {
        BudgetCheck(UsPriceOnlyBudget.Result result, String cursor, boolean retry) {
            this(result, cursor, retry, UsNasdaqRecovery.Result.empty(), false);
        }
    }

    static UsScreen.Fx tradeDateFx(JSONArray rates, LocalDate day) throws JSONException {
        var fx = UsScreen.readFx(rates, day);
        if (!day.equals(fx.date())) throw new JSONException("US financial screen is waiting for trade-date FX");
        return fx;
    }

    private BudgetCheck prepareBudget(JSONObject quote, JSONObject ledger, File directory,
                                      LocalDate day, String hash, android.content.SharedPreferences state) {
        if (networkStopped()) return null;
        var expected = UsDailyCloses.onOrBeforeTradingDay(UsDailyCloses.mostRecentEligibleDay(Instant.now()));
        if (!day.equals(expected)) return null;
        try {
            var priorFile = new AtomicFile(new File(directory, UsDailyWorker.PREVIOUS_QUOTE_FILE));
            byte[] previousBytes = UsDailyWorker.readQuote(priorFile);
            var previous = new JSONObject(new String(previousBytes, StandardCharsets.UTF_8));
            var priorDay = UsPriceOnlyBudget.previousSession(day);
            if (!priorDay.toString().equals(previous.optString("trading_date_et"))
                    || !quote.getString("source").equals(previous.optString("source"))) return null;
            var nasdaq = listings("nasdaqlisted.txt", true);
            var nyse = listings("otherlisted.txt", false);
            var scope = UsListingHistory.scope(UsListingHistory.remember(directory, nyse, nasdaq), priorDay, day, nyse, nasdaq);
            var rates = new JSONArray(download.get(FX + "&from=" + priorDay + "&to=" + day));
            var financial = UsReferenceAlerts.read(ledger);
            if (!hash.equals(financial.hash())) return null;
            var budget = UsPriceOnlyBudget.compare(previous, quote, rates, scope.ordinary(), financial, expected);
            if (!UsPriceOnlyBudget.canCorroborateDolt(previous, quote)) {
                return new BudgetCheck(budget, "", false, UsNasdaqRecovery.Result.empty(), scope.exactDates());
            }
            Set<String> sent = sentBudgetSymbols(state, day);
            String cursor = day.toString().equals(state.getString(BUDGET_CURSOR_DAY, ""))
                    ? state.getString(BUDGET_CURSOR, "") : "";
            BudgetCheck primary = new BudgetCheck(budget, cursor, false);
            LocalDate asOf = LocalDate.now(UsDailyCloses.NEW_YORK);
            if (!budget.screen().entered().isEmpty()) {
                try {
                    primary = corroborateBudget(previous, quote, priorDay, day, asOf, budget, download,
                            this::networkStopped, sent, cursor);
                } catch (IOException | JSONException unavailable) {
                    primary = new BudgetCheck(budget, cursor, unavailable instanceof IOException);
                }
            }
            UsNasdaqRecovery.Result official = UsNasdaqRecovery.Result.empty();
            try {
                if (!primary.retry()) {
                    String key = hash + ":" + UsReferenceAlerts.sha256(previousBytes);
                    official = recoverOfficial(previous, quote, scope.nasdaq(), financial, priorDay, day, asOf, rates, state, key);
                }
            } catch (IOException unavailable) {
                official = new UsNasdaqRecovery.Result(PriceOnlyScreen.Result.empty(), true, false);
            } catch (JSONException invalid) {
                // Keep normal alerts when the supplementary dates or market evidence cannot be validated.
            }
            return new BudgetCheck(primary.result(), primary.cursor(), primary.retry() || official.retry(), official, scope.exactDates());
        } catch (IOException | JSONException | DateTimeParseException unavailable) {
            return null;
        }
    }

    private UsNasdaqRecovery.Result recoverOfficial(JSONObject previous, JSONObject latest,
            Set<String> nasdaq, UsReferenceAlerts.Screen financial, LocalDate priorDay,
            LocalDate day, LocalDate asOf, JSONArray rates, android.content.SharedPreferences state, String key)
            throws IOException, JSONException {
        var before = UsDeviceFinancials.prices(previous.getJSONArray("closes"));
        var after = UsDeviceFinancials.prices(latest.getJSONArray("closes"));
        var missing = UsNasdaqRecovery.missing(nasdaq, financial.rows().keySet(), before.keySet(), after.keySet());
        if (missing.isEmpty()) return UsNasdaqRecovery.Result.empty();
        var oldFx = tradeDateFx(rates, priorDay);
        var newFx = tradeDateFx(rates, day);
        var splits = UsDoltCloses.allSplits(priorDay, asOf, url -> new JSONObject(download.get(url)));
        var nasdaqSplits = UsNasdaqCloseCheck.splits(
                new JSONObject(download.get(UsNasdaqCloseCheck.splitCalendarUrl(priorDay))), priorDay, asOf);
        JSONObject receipts = new JSONObject();
        if (key.equals(state.getString(NOCP_PAIR_KEY, ""))) {
            try {
                receipts = new JSONObject(state.getString(NOCP_RECEIPTS, "{}"));
            } catch (JSONException invalid) {
                // A corrupt local cache can be revalidated from Nasdaq.
            }
        }
        var result = UsNasdaqRecovery.check(missing, priorDay, day, oldFx, newFx, splits.keySet(), nasdaqSplits,
                receipts, download, this::networkStopped);
        state.edit().putString(NOCP_PAIR_KEY, key).putString(NOCP_RECEIPTS, receipts.toString()).apply();
        return result;
    }

    static BudgetCheck corroborateBudget(JSONObject previous, JSONObject quote, LocalDate priorDay,
                                        LocalDate day, LocalDate asOf, UsPriceOnlyBudget.Result budget,
                                        Download download, BooleanSupplier stopped, Set<String> sent, String cursor)
            throws IOException, JSONException {
        var splits = UsDoltCloses.allSplits(priorDay, asOf, url -> new JSONObject(download.get(url)));
        var nasdaqSplits = UsNasdaqCloseCheck.splits(
                new JSONObject(download.get(UsNasdaqCloseCheck.splitCalendarUrl(priorDay))), priorDay, asOf);
        var before = UsDeviceFinancials.prices(previous.getJSONArray("closes"));
        var latest = UsDeviceFinancials.prices(quote.getJSONArray("closes"));
        var matched = new HashSet<>(sent);
        var queue = new ArrayList<>(budget.screen().entered().stream()
                .map(PriceOnlyScreen.BudgetEntry::code)
                .filter(symbol -> !sent.contains(symbol) && !UsNasdaqCloseCheck.hasSplit(splits.keySet(), symbol)
                        && !UsNasdaqCloseCheck.hasSplit(nasdaqSplits, symbol)
                        && UsNasdaqCloseCheck.url(symbol, priorDay, day) != null)
                .toList());
        queue.sort(Comparator.comparing((String symbol) -> symbol.compareTo(cursor) <= 0)
                .thenComparing(Comparator.naturalOrder()));
        boolean retry = queue.size() > MAX_NASDAQ_CHECKS;
        String last = cursor;
        for (String symbol : queue.subList(0, Math.min(MAX_NASDAQ_CHECKS, queue.size()))) {
            if (stopped.getAsBoolean()) break;
            last = symbol;
            try {
                String url = UsNasdaqCloseCheck.url(symbol, priorDay, day);
                if (UsNasdaqCloseCheck.matches(new JSONObject(download.get(url)), symbol, priorDay, before.get(symbol),
                        day, latest.get(symbol))) matched.add(symbol);
            } catch (UsDailyWorker.HttpStatus unavailable) {
                if (unavailable.code == 429) {
                    retry = true;
                    break;
                }
                if (unavailable.code >= 500) retry = true;
            } catch (IOException unavailable) {
                retry = true;
            } catch (JSONException invalid) {
                // A malformed second quote cannot confirm this symbol.
            }
        }
        return new BudgetCheck(budget.corroborated(matched), last, retry);
    }

    private static Set<String> sentBudgetSymbols(android.content.SharedPreferences state, LocalDate day) {
        return day.toString().equals(state.getString(BUDGET_SENT_DAY, ""))
                ? new HashSet<>(state.getStringSet(BUDGET_SENT_SYMBOLS, Set.of())) : new HashSet<>();
    }

    private static boolean applyBudget(Context context, android.content.SharedPreferences state, LocalDate day,
                                       BudgetCheck check) {
        var budget = check == null ? null : check.result();
        var date = day.toString();
        var status = state.edit().putString(UsDailyWorker.PRICE_ONLY_DAY, date);
        if (budget == null || (budget.screen().assessed() == 0 && check.official().screen().assessed() == 0)) {
            status.putString(UsDailyWorker.PRICE_ONLY_STATUS, "株価だけの予算判定は終値・上場一覧・当日為替の照合待ち").apply();
            return true;
        }
        var result = budget.screen();
        var official = check.official().screen();
        var entries = new ArrayList<>(budget.notificationEntries());
        entries.addAll(official.entered());
        String summary = "財務または株価で一次判定 " + (budget.combinedAssessed() + official.assessed()) + " / " + budget.listed()
                + "銘柄 · うち株価だけ " + (result.assessed() + official.assessed()) + "銘柄"
                + "\n株価だけで100株10万円以下に入った " + result.entered().size() + "銘柄";
        if (!check.exactListings()) summary += "\n上場一覧は比較2日分の履歴が揃うまで参考集計";
        if (!budget.verifiedPriceBasis()) {
            summary += " · 2つの取得元で終値一致 " + budget.notificationEntries().size()
                    + "銘柄 · 照合待ち " + (result.entered().size() - budget.notificationEntries().size()) + "銘柄";
        }
        if (official.assessed() > 0) summary += "\nNasdaq公式終値2日分で追加判定 " + official.assessed()
                + "銘柄 · 予算入り " + official.entered().size() + "銘柄";
        if (!entries.isEmpty()) {
            summary += "\n予算入り "
                    + String.join("、", entries.stream().map(PriceOnlyScreen.BudgetEntry::code).toList());
        }
        // Persist the complete verified candidate set separately from the
        // notification's "new since last sent" subset. It must survive process
        // death and remain inspectable without network access.
        var saved = new org.json.JSONArray();
        var officialCodes = new HashSet<String>();
        for (var item : official.entered()) officialCodes.add(item.code());
        var unique = new java.util.TreeMap<String, PriceOnlyScreen.BudgetEntry>();
        for (var item : entries) unique.put(item.code(), item);
        for (var item : unique.values()) {
            var row = new org.json.JSONObject();
            try {
                row.put("code", item.code());
                row.put("yen", item.yen().stripTrailingZeros().toPlainString());
                row.put("source", officialCodes.contains(item.code()) ? "Nasdaq公式終値" : "DoltHubとNasdaq照合");
                saved.put(row);
            } catch (org.json.JSONException invalid) {
                return false;
            }
        }
        status.putString(UsDailyWorker.PRICE_ONLY_STATUS, summary)
                .putString(BUDGET_RESULTS_DAY, date)
                .putString(BUDGET_RESULTS, saved.toString()).apply();
        String blocked = ScanWorker.alertBlockReason(context);
        DiagnosticLog.record(context, DiagnosticLog.Area.ALERT, "米国株の参考予算条件入り "
                + entries.size() + "件 · " + (blocked.isEmpty() ? "通知許可あり" : blocked));
        if (!blocked.isEmpty()) return true;
        var sent = sentBudgetSymbols(state, day);
        var progress = state.edit().putString(BUDGET_CURSOR_DAY, date).putString(BUDGET_CURSOR, check.cursor());
        var pending = pendingBudgetEntries(entries, sent);
        if (pending.isEmpty()) return progress.commit();
        var detail = new StringBuilder(day + "の終値と同日の為替で100株の購入額を計算（手数料別）");
        var officialEntries = new HashSet<>(official.entered());
        if (!budget.verifiedPriceBasis() && pending.stream().anyMatch(entry -> !officialEntries.contains(entry)))
            detail.append("\nDoltHubとNasdaq公開履歴を照合した参考通知");
        var issuerNames = UsCompanyNames.read(context);
        for (var entry : pending) {
            String name = issuerNames.get(entry.code());
            detail.append("\n").append(entry.code());
            if (name != null) detail.append(" (").append(name).append(")");
            detail.append(" · ").append(entry.yen().stripTrailingZeros().toPlainString()).append("円");
            if (officialEntries.contains(entry)) detail.append("（Nasdaq公式終値）");
        }
        if (!ScanWorker.postNotification(context, BUDGET_NOTIFICATION_ID,
                "米国株・参考 100株10万円以下に入った " + pending.size() + "銘柄", detail.toString())) return false;
        for (var entry : pending) sent.add(entry.code());
        return progress.putString(BUDGET_SENT_DAY, date).putStringSet(BUDGET_SENT_SYMBOLS, sent).commit();
    }

    static List<PriceOnlyScreen.BudgetEntry> pendingBudgetEntries(
            List<PriceOnlyScreen.BudgetEntry> entries, Set<String> sent) {
        var accounted = new HashSet<>(sent);
        var pending = new ArrayList<PriceOnlyScreen.BudgetEntry>();
        for (var entry : entries) {
            if (accounted.add(entry.code())) pending.add(entry);
        }
        return List.copyOf(pending);
    }

    private UsMarketCoverage.Directory listings(String filename, boolean nasdaq)
            throws IOException, JSONException {
        return UsMarketCoverage.directory(download.get(UsMarketCoverage.DIRECTORY + filename), nasdaq);
    }

    private static JSONObject resume(AtomicFile file) throws IOException {
        try {
            var scan = new JSONObject(new String(file.readFully(), StandardCharsets.UTF_8));
            if (scan.optInt("cursor", -1) >= 0
                    && scan.optJSONArray("targets") != null && scan.optJSONArray("results") != null) return scan;
        } catch (FileNotFoundException | JSONException absent) {
            // A missing or damaged local checkpoint starts a fresh scan.
        }
        return null;
    }

    private Set<Integer> changedIssuers(LocalDate since, LocalDate until) {
        if (since == null) return null;
        var changed = new HashSet<Integer>();
        try {
            // Check both endpoints: the previous day's filings become eligible, and
            // the current index may contain corrections with earlier filing dates.
            for (LocalDate date = since; !date.isAfter(until); date = date.plusDays(1)) {
                if (networkStopped()) return null;
                if (date.getDayOfWeek() == DayOfWeek.SATURDAY || date.getDayOfWeek() == DayOfWeek.SUNDAY) continue;
                changed.addAll(UsSecFilingIndex.issuers(download.get(UsSecFilingIndex.address(date)), date));
            }
            return changed;
        } catch (IOException | JSONException unavailable) {
            // Missing index coverage cannot certify that a cached issuer had no filings.
            return null;
        }
    }

    private JSONObject facts(JSONObject target, LocalDate day) throws IOException, JSONException {
        try {
            int cik = target.getInt("cik");
            var payload = new JSONObject(download.get(String.format(Locale.ROOT, SEC_FACTS, cik)));
            return UsDeviceFinancials.financialRow(target, payload, day);
        } catch (UsDailyWorker.HttpStatus error) {
            if (error.code == 404) return null;
            throw error;
        } catch (JSONException invalidIssuer) {
            // Invalid issuer facts cannot become a candidate.
            return null;
        }
    }

    private void updateProgress(LocalDate day, int position, int total, int verified, int reused) {
        var preferences = ScanWorker.prefs(getApplicationContext());
        synchronized (UsDailyWorker.QUOTE_LOCK) {
            var market = MarketFreshness.US_FINANCE;
            var latest = market.target(preferences);
            if (latest != null && latest.isAfter(day)) return;
            market.waiting(preferences.edit(), MarketFreshness.Phase.FINANCE, day)
                    .putString(UsDailyWorker.PRIVATE_STATUS,
                            "SEC財務を取得中 " + (position + reused) + " / " + (total + reused)
                                    + "銘柄 · 財務・株数照合 " + verified + "銘柄").apply();
        }
    }
}
