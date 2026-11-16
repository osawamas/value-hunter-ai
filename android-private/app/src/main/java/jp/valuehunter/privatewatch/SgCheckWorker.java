package jp.valuehunter.privatewatch;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.time.LocalTime;
import java.time.ZonedDateTime;
import java.util.Locale;

public final class SgCheckWorker extends Worker {
    public SgCheckWorker(@NonNull Context context, @NonNull WorkerParameters parameters) {
        super(context, parameters);
    }

    @NonNull @Override public Result doWork() {
        var state = ScanWorker.prefs(getApplicationContext());
        String key = state.getString("sg_key", "");
        if (key.isEmpty()) return Result.success();
        String result;
        boolean passed = false;
        try {
            var now = ZonedDateTime.now(SgCloseCheck.SINGAPORE);
            var cutoff = now.toLocalTime().isBefore(LocalTime.of(18, 0))
                    ? now.toLocalDate().minusDays(1) : now.toLocalDate();
            var payload = new JSONObject(UsScanWorker.get(
                    "https://api.datacedar.com/v3/stocks/sgx%3AS63/bars"
                            + "?timeframe=1Day&adjustment=raw&order=desc&limit=8", key));
            var pair = SgCloseCheck.read(payload, cutoff);
            result = String.format(Locale.JAPAN, "S63 · 未調整終値を2取引日分取得\n%s  %.3f SGD\n%s  %.3f SGD",
                    pair.previous().session(), pair.previous().sgd(), pair.latest().session(), pair.latest().sgd());
            passed = true;
        } catch (UsScanWorker.HttpFailure error) {
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
        }
        if (isStopped() || !key.equals(state.getString("sg_key", ""))) return Result.success();
        state.edit().putString("sg_result", result).apply();
        return passed ? Result.success() : Result.failure();
    }
}
