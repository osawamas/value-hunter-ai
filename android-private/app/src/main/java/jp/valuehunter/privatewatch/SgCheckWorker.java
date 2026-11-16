package jp.valuehunter.privatewatch;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.time.LocalTime;
import java.time.ZonedDateTime;
import java.util.Locale;

public final class SgCheckWorker extends Worker {
    private static final Object LOCK = new Object();
    public SgCheckWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    @NonNull @Override public Result doWork() {
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
        String result;
        SgCloseCheck.Pair pair = null;
        Evaluation evaluation = null;
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
            evaluation = evaluate(context, pair.latest(), getRunAttemptCount());
            result += evaluation.details() + evaluation.disclosureDetails();
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
                || watch != state.getBoolean("sg_watch", false)) return Result.success();
        var editor = state.edit();
        if (pair != null) {
            editor.putString("sg_last_result", result);
            retryableFailure = evaluation.retryableFailure();
        } else {
            String previousResult = state.getString("sg_last_result", "");
            if (!previousResult.isEmpty()) result += "\n\n前回取得したデータ\n" + previousResult;
        }
        if (retryableFailure) result += "\n一時エラー。再試行を予約した";
        editor.putString("sg_result", result);
        boolean alert = false;
        if (watch && pair != null && evaluation.qualified() != null) {
            String last = state.getString("sg_qualified_date", "");
            String next = pair.latest().session().toString();
            if (next.compareTo(last) > 0) {
                alert = SgValuation.shouldAlert(pair, last, state.getBoolean("sg_qualified", false),
                        evaluation.qualified());
                editor.putString("sg_qualified_date", next).putBoolean("sg_qualified", evaluation.qualified());
            }
        }
        if (!editor.commit()) return Result.retry();
        if (alert && key.equals(state.getString("sg_key", "")) && state.getBoolean("sg_watch", false)) {
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
                              boolean retryableFailure) {}

    private static SgShareLedger.Disclosure readBundledDisclosure(Context context, SgCloseCheck.Close close) {
        try {
            var ledger = SgShareLedger.readAsset(context.getAssets().open("android-s63-shares.json"));
            return SgShareLedger.read(ledger, close.session());
        } catch (IOException | JSONException error) {
            return null;
        }
    }

    private static Evaluation evaluate(Context context, SgCloseCheck.Close close, int attempts) {
        StringBuilder details = new StringBuilder();
        SgShareLedger.Disclosure disclosure = null;
        boolean retryableFailure = false;
        if (SgValuation.financialsAvailable(close.session())) {
            disclosure = readBundledDisclosure(context, close);
            if (disclosure == null) {
                try {
                    var ledger = new JSONObject(UsScanWorker.get(SgShareLedger.URL, null));
                    disclosure = SgShareLedger.read(ledger, close.session());
                } catch (IOException | JSONException error) {
                    details.append("\n開示株数の更新データを確認できなかった");
                    if (error instanceof IOException) {
                        retryableFailure = shouldRetry(error instanceof UsScanWorker.HttpFailure failure
                                ? failure.status : 0, attempts);
                    }
                }
            }
        }
        var trial = disclosure == null ? null : SgValuation.forClose(close, disclosure.shares());
        Boolean qualified = null;
        if (!SgValuation.financialsAvailable(close.session())) {
            details.append("\n取引日時点の財務が未登録。時価総額・PER・PBRは保留");
        } else if (trial == null) {
            details.append("\n同日の開示株数を確認できず、時価総額・PER・PBRは保留");
        } else {
            details.append(String.format(Locale.JAPAN,
                    "\n同日の開示株数 %,d株（事後照合）"
                            + "\n財務基準日 " + SgValuation.FINANCIAL_PERIOD
                            + "\n参考時価総額 %,.0f SGD · 参考PER %.2f倍 · 参考PBR %.2f倍",
                    trial.shares(), trial.cap(), trial.per(), trial.pbr()));
        }
        try {
            var fx = UsScreen.readFx(new JSONArray(UsScanWorker.get(
                    "https://api.frankfurter.dev/v2/rates?base=SGD&quotes=JPY"
                            + "&from=" + close.session().minusDays(4)
                            + "&to=" + close.session(), null)), close.session(), "SGD");
            double oneShare = close.sgd() * fx.yenPerDollar();
            details.append(String.format(Locale.JAPAN,
                    "\n為替基準日 %s · 1株 約%,.0f円 · 100株 約%,.0f円（手数料別）",
                    fx.date(), oneShare, oneShare * 100));
            if (trial != null) {
                qualified = trial.qualifies(oneShare);
                details.append(qualified ? "\n割安条件に該当（参考）" : "\n割安条件外（参考）");
            }
        } catch (IOException | JSONException error) {
            details.append("\n為替を取得できなかったため、円換算は保留");
            if (error instanceof IOException) {
                retryableFailure |= shouldRetry(error instanceof UsScanWorker.HttpFailure failure
                        ? failure.status : 0, attempts);
            }
        }
        String disclosureDetails = disclosure == null ? "" :
                "\n株数の開示日時 " + disclosure.disclosedAt().format(
                        java.time.format.DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss 'SGT'", Locale.JAPAN))
                        + "\nSGX原本 " + disclosure.source();
        return new Evaluation(details.toString(), disclosureDetails, qualified, retryableFailure);
    }
}
