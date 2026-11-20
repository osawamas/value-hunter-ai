package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

final class UsNasdaqRecovery {
    private static final int BATCH = 24;

    record Result(PriceOnlyScreen.Result screen, boolean retry, boolean more) {
        static Result empty() { return new Result(PriceOnlyScreen.Result.empty(), false, false); }
    }

    static Set<String> missing(Set<String> nasdaq, Set<String> financial, Set<String> previous, Set<String> latest) {
        var result = new HashSet<>(nasdaq);
        result.removeAll(financial);
        result.removeIf(code -> (previous.contains(code) && latest.contains(code))
                || UsNasdaqOfficialClose.url(code) == null);
        return result;
    }

    static Result check(Set<String> missing, LocalDate previous, LocalDate latest, UsScreen.Fx oldFx,
                        UsScreen.Fx newFx, Set<String> splits, Set<String> nasdaqSplits, JSONObject receipts,
                        UsSecFinanceWorker.Download download, BooleanSupplier stopped) throws JSONException {
        if (!previous.equals(oldFx.date()) || !latest.equals(newFx.date())) return Result.empty();
        var eligible = missing.stream().filter(code -> !UsNasdaqCloseCheck.hasSplit(splits, code)
                && !UsNasdaqCloseCheck.hasSplit(nasdaqSplits, code)).sorted().toList();
        var queue = eligible.stream().filter(code -> !receipts.has(code)).toList();
        boolean retry = false;
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(75);
        for (String code : queue.subList(0, Math.min(BATCH, queue.size()))) {
            if (stopped.getAsBoolean() || System.nanoTime() >= deadline) break;
            try {
                var pair = UsNasdaqOfficialClose.read(new JSONObject(download.get(UsNasdaqOfficialClose.url(code))),
                        code, previous, latest);
                receipts.put(code, pair == null ? Boolean.FALSE : new JSONArray()
                        .put(pair.before().toPlainString()).put(pair.after().toPlainString()));
            } catch (UsDailyWorker.HttpStatus unavailable) {
                if (unavailable.code == 429) {
                    retry = true;
                    break;
                }
                if (unavailable.code >= 500) retry = true;
                else receipts.put(code, false);
            } catch (IOException unavailable) {
                retry = true;
            } catch (JSONException invalid) {
                receipts.put(code, false);
            }
        }
        var before = new HashMap<String, BigDecimal>();
        var after = new HashMap<String, BigDecimal>();
        var oldRate = BigDecimal.valueOf(oldFx.yenPerDollar());
        var newRate = BigDecimal.valueOf(newFx.yenPerDollar());
        for (String code : eligible) {
            var pair = receipts.optJSONArray(code);
            if (pair == null || pair.length() != 2) continue;
            try {
                var oldPrice = new BigDecimal(pair.getString(0));
                var newPrice = new BigDecimal(pair.getString(1));
                if (oldPrice.signum() <= 0 || newPrice.signum() <= 0) continue;
                before.put(code, oldPrice.multiply(oldRate));
                after.put(code, newPrice.multiply(newRate));
            } catch (JSONException | NumberFormatException malformed) {
                receipts.remove(code);
            }
        }
        var result = PriceOnlyScreen.budgetEntries(before.keySet(), Set.of(), before::get, after::get);
        boolean remaining = eligible.stream().anyMatch(code -> !receipts.has(code));
        return new Result(result, retry, !retry && remaining);
    }

    private UsNasdaqRecovery() {}
}
