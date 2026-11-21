package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;

enum MarketFreshness {
    JPX("jpx_freshness"),
    US_CLOSE("us_close_freshness"),
    US_FINANCE("us_finance_freshness");

    enum Phase {
        PUBLICATION("終値の公開待ち"),
        COMPARISON("比較日の終値待ち"),
        FINANCE("財務・株数などの照合待ち"),
        ERROR("取得に失敗 · 再試行待ち"),
        NEXT_CHECK("取得に失敗 · 次回の更新で確認");

        final String label;

        Phase(String label) {
            this.label = label;
        }
    }

    private final String key;

    MarketFreshness(String key) {
        this.key = key;
    }

    SharedPreferences.Editor waiting(SharedPreferences.Editor edit, Phase phase, LocalDate target) {
        return edit.putString(key + "_phase", phase == null ? "" : phase.name())
                .putString(key + "_target", target == null ? "" : target.toString());
    }

    SharedPreferences.Editor verified(SharedPreferences.Editor edit, LocalDate day, int assessed, int candidates,
                                      String candidateDetails) {
        return edit.putString(key + "_day", day.toString()).putInt(key + "_assessed", assessed)
                .putInt(key + "_candidates", candidates).putString(key + "_details", candidateDetails);
    }

    LocalDate day(SharedPreferences state) {
        return date(state.getString(key + "_day", ""));
    }

    LocalDate target(SharedPreferences state) {
        return date(state.getString(key + "_target", ""));
    }

    Phase phase(SharedPreferences state) {
        String saved = state.getString(key + "_phase", "");
        for (var phase : Phase.values()) {
            if (phase.name().equals(saved)) return phase;
        }
        return null;
    }

    String result(SharedPreferences state) {
        var day = day(state);
        if (day == null) return "判定済みの取引日を確認待ち";
        return result(day, state.getInt(key + "_assessed", 0), state.getInt(key + "_candidates", 0));
    }

    static String result(LocalDate day, int assessed, int candidates) {
        return day + " の取引分 · 判定済み " + assessed + "銘柄 · 条件該当 " + candidates + "銘柄";
    }

    String details(SharedPreferences state) {
        return state.getString(key + "_details", "");
    }

    String waiting(SharedPreferences state) {
        return waiting(phase(state), target(state));
    }

    static String waiting(Phase phase, LocalDate target) {
        return phase == null ? "" : (target == null ? "" : target + " の取引分 · ") + phase.label;
    }

    void clear(SharedPreferences.Editor edit) {
        edit.remove(key + "_day").remove(key + "_assessed").remove(key + "_candidates")
                .remove(key + "_details").remove(key + "_phase").remove(key + "_target");
    }

    private static LocalDate date(String stored) {
        try {
            return stored.isEmpty() ? null : LocalDate.parse(stored);
        } catch (DateTimeParseException invalid) {
            return null;
        }
    }
}
