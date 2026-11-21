package jp.valuehunter.privatewatch;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalTime;
import java.time.ZonedDateTime;
import java.util.Locale;

public final class SgCheckWorker extends Worker {
    private static final Object LOCK = new Object();
    private static final String CACHED_LEDGER = "sg_verified_ledger";
    public SgCheckWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    @NonNull @Override public Result doWork() {
        if (!MarketNetwork.allowed()) return MarketNetwork.waitingForWifi() ? Result.retry() : Result.success();
        if (!getInputData().getBoolean(ScanWorker.LEGACY_API_REQUEST, false)) return Result.success();
        synchronized (LOCK) {
            return check();
        }
    }

    private Result check() {
        var context = getApplicationContext();
        var state = ScanWorker.prefs(context);
        String key = state.getString("sg_key", "");
        if (key.isEmpty()) return Result.success();
        boolean watch = state.getBoolean("sg_watch", false);
        String lastEvaluated = state.getString("sg_qualified_date", "");
        String result;
        SgCloseCheck.Pair pair = null;
        Evaluation evaluation = null;
        Evaluation previous = null;
        SgDisclosureLookup disclosures = null;
        var decision = SgValuation.WatchDecision.UNCHANGED;
        boolean retryableFailure = false;
        try {
            var now = ZonedDateTime.now(SgCloseCheck.SINGAPORE);
            var cutoff = now.toLocalTime().isBefore(LocalTime.of(18, 0))
                    ? now.toLocalDate().minusDays(1) : now.toLocalDate();
            var payload = new JSONObject(UsScanWorker.get(
                    "https://api.datacedar.com/v3/stocks/sgx%3AS63/bars"
                            + "?timeframe=1Day&adjustment=raw&order=desc&limit=8", key));
            pair = SgCloseCheck.read(payload, cutoff);
            result = String.format(Locale.JAPAN, "S63 · 未調整終値を2取引日分取得\n%s  %.3f SGD\n%s  %.3f SGD",
                    pair.previous().session(), pair.previous().sgd(), pair.latest().session(), pair.latest().sgd());
            disclosures = new SgDisclosureLookup(readBundledLedger(context),
                    state.getString(CACHED_LEDGER, ""), now.toInstant(),
                    () -> UsScanWorker.get(SgShareLedger.URL, null));
            boolean mayNeedPrevious = watch && SgValuation.needsPreviousEvaluation(pair, lastEvaluated);
            var rates = new SgExchangeRates(pair, mayNeedPrevious,
                    url -> new JSONArray(UsScanWorker.get(url, null)));
            evaluation = evaluate(disclosures, rates, pair.latest(), true, getRunAttemptCount());
            result += evaluation.details() + evaluation.disclosureDetails();
            if (mayNeedPrevious && Boolean.TRUE.equals(evaluation.qualified())) {
                previous = evaluate(disclosures, rates, pair.previous(), false, getRunAttemptCount());
            }
            if (watch) {
                decision = SgValuation.watchDecision(pair, lastEvaluated, evaluation.qualified(),
                        previous == null ? null : previous.qualified());
                if (decision == SgValuation.WatchDecision.WAIT_FOR_PREVIOUS) {
                    result += "\n通知は保留 · 直前取引日 " + pair.previous().session() + " · "
                            + previous.blockingReason();
                }
            }
        } catch (UsScanWorker.HttpFailure error) {
            retryableFailure = shouldRetry(error.status, getRunAttemptCount());
            result = switch (error.status) {
                case 401 -> "DataCedarのAPIキーを確認して";
                case 403 -> "DataCedarが取得を拒否した。プランと銘柄へのアクセス権を確認して";
                case 429 -> "DataCedarの取得上限に達した。時間をおいて再試行して";
                default -> "DataCedarから取得できなかった（HTTP " + error.status + "）";
            };
        } catch (JSONException error) {
            result = "S63の応答を照合できなかった。2取引日分の未調整日足が必要";
        } catch (IOException error) {
            result = "DataCedarに接続できなかった";
            retryableFailure = shouldRetry(0, getRunAttemptCount());
        }
        if (isStopped() || !key.equals(state.getString("sg_key", ""))
                || watch != state.getBoolean("sg_watch", false)
                || !lastEvaluated.equals(state.getString("sg_qualified_date", ""))) return Result.success();
        var editor = state.edit();
        if (pair != null) {
            editor.putString("sg_last_result", result);
            String verifiedLedger = disclosures.verifiedUpdate();
            if (verifiedLedger != null) editor.putString(CACHED_LEDGER, verifiedLedger);
            retryableFailure = evaluation.retryableFailure() || (previous != null && previous.retryableFailure());
        } else {
            String previousResult = state.getString("sg_last_result", "");
            if (!previousResult.isEmpty()) result += "\n\n前回取得したデータ\n" + previousResult;
        }
        if (retryableFailure) result += "\n一時エラー。再試行を予約した";
        editor.putString("sg_result", result);
        if (decision == SgValuation.WatchDecision.SAVE || decision == SgValuation.WatchDecision.ALERT) {
            editor.putString("sg_qualified_date", pair.latest().session().toString())
                    .remove("sg_qualified");
        }
        if (!editor.commit()) return Result.retry();
        if (decision == SgValuation.WatchDecision.ALERT && key.equals(state.getString("sg_key", ""))
                && state.getBoolean("sg_watch", false)) {
            var close = pair.latest();
            ScanWorker.postNotification(context, 4, "S63が割安条件に該当（参考）",
                    close.session() + "終値 " + String.format(Locale.JAPAN, "%.3f SGD", close.sgd())
                            + evaluation.details());
        }
        if (retryableFailure) return Result.retry();
        return pair == null ? Result.failure() : Result.success();
    }

    static boolean shouldRetry(int httpStatus, int attempts) {
        return attempts < 2 && (httpStatus == 0 || httpStatus == 408 || httpStatus == 429
                || (httpStatus >= 500 && httpStatus <= 599));
    }

    private record Evaluation(String details, String disclosureDetails, Boolean qualified,
                              String blockingReason, boolean retryableFailure) {}

    private static JSONObject readBundledLedger(Context context) {
        try {
            return SgShareLedger.readAsset(context.getAssets().open("android-s63-shares.json"));
        } catch (IOException | JSONException error) {
            return null;
        }
    }

    private static Evaluation evaluate(SgDisclosureLookup disclosures, SgExchangeRates rates,
                                       SgCloseCheck.Close close, boolean showPurchaseCost, int attempts) {
        StringBuilder details = new StringBuilder();
        SgShareLedger.Disclosure disclosure = null;
        String ledgerNote = "";
        boolean retryableFailure = false;
        boolean financialsAvailable = SgValuation.financialsAvailable(close.session());
        String blockingReason = "";
        if (financialsAvailable) {
            try {
                var lookup = disclosures.forSession(close.session());
                disclosure = lookup.disclosure();
                ledgerNote = lookup.source().note;
            } catch (IOException | JSONException error) {
                blockingReason = "開示台帳の更新データを取得・照合できなかった";
                if (error instanceof IOException) {
                    retryableFailure = shouldRetry(error instanceof UsScanWorker.HttpFailure failure
                            ? failure.status : 0, attempts);
                }
            }
        }
        var trial = disclosure == null ? null : SgValuation.forClose(close, disclosure.shares());
        Boolean qualified = null;
        if (!financialsAvailable) {
            blockingReason = "取引日時点の財務が未登録";
        } else if (trial == null && blockingReason.isEmpty()) {
            blockingReason = "取引日付の開示株数を確認できなかった";
        }
        if (trial == null) {
            details.append("\n").append(blockingReason).append("。時価総額・PER・PBRは保留");
        } else {
            details.append(String.format(Locale.JAPAN,
                    "\n取引日付の開示株数 %,d株（事後照合）"
                            + "\n財務基準日 " + SgValuation.FINANCIAL_PERIOD
                            + "\n参考時価総額 %,.0f SGD · 参考PER %.2f倍 · 参考PBR %.2f倍",
                    trial.shares(), trial.cap(), trial.per(), trial.pbr()));
        }
        if (trial == null && !showPurchaseCost) {
            return new Evaluation(details.toString(), "", null, blockingReason, retryableFailure);
        }
        try {
            var fx = rates.forSession(close.session());
            double oneShare = close.sgd() * fx.yenPerDollar();
            details.append(String.format(Locale.JAPAN,
                    "\n為替基準日 %s · 1株 約%,.0f円 · 100株 約%,.0f円（手数料別）",
                    fx.date(), oneShare, oneShare * 100));
            if (trial != null) {
                qualified = trial.qualifies(oneShare);
                details.append(qualified ? "\n割安条件に該当（参考）" : "\n割安条件外（参考）");
            }
        } catch (IOException | JSONException error) {
            String fxReason = error instanceof JSONException
                    ? "取引日までのSGD/JPYレートを照合できなかった"
                    : "SGD/JPYレートを取得できなかった";
            details.append("\n").append(fxReason).append("。円換算は保留");
            if (blockingReason.isEmpty()) blockingReason = fxReason;
            if (error instanceof IOException) {
                retryableFailure |= shouldRetry(error instanceof UsScanWorker.HttpFailure failure
                        ? failure.status : 0, attempts);
            }
        }
        String disclosureDetails = disclosure == null ? "" :
                "\n株数の開示日時 " + disclosure.disclosedAt().format(
                        java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss 'SGT'", Locale.JAPAN))
                        + "\nSGX原本 " + disclosure.source()
                        + (ledgerNote.isEmpty() ? "" : "\n" + ledgerNote);
        return new Evaluation(details.toString(), disclosureDetails, qualified, blockingReason, retryableFailure);
    }
}
