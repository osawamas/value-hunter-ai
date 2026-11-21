package jp.valuehunter.privatewatch;

import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

enum MarketCoverage {
    JPX("jpx_coverage"),
    US("us_coverage");

    enum Reason {
        CLOSE("終値待ち"),
        FINANCIALS("財務・株数待ち"),
        CORPORATE_ACTION("分割・併合などの確認待ち"),
        DOWNLOAD("取得エラー"),
        IDENTIFICATION("上場銘柄とSECの照合待ち"),
        VALUATION("為替など判定資料の確認待ち"),
        OUTSIDE_BUDGET("終値で予算外と確認");

        final String label;
        Reason(String label) { this.label = label; }
    }

    record Snapshot(LocalDate day, LocalDate listingDay, int target, int closed, int assessed,
                    Map<Reason, List<String>> unassessed) {
        String summary() {
            return day + " 分 · 監視対象 " + target + "銘柄"
                    + "\n終値確認 " + closed + " / " + target + "銘柄"
                    + "\n割安判定 " + assessed + " / " + target + "銘柄"
                    + (day.equals(listingDay) ? "" : "\n対象は " + listingDay + " 時点の上場一覧（参考）");
        }
    }

    private final String key;
    MarketCoverage(String key) { this.key = key; }

    boolean available(SharedPreferences state) { return state.contains(key + "_details"); }
    String summary(SharedPreferences state) { return state.getString(key + "_summary", "監視範囲を集計待ち"); }
    void clear(SharedPreferences.Editor edit) { edit.remove(key + "_summary").remove(key + "_details"); }

    SharedPreferences.Editor save(SharedPreferences.Editor edit, Snapshot snapshot) {
        var groups = new HashMap<String, JSONArray>();
        snapshot.unassessed().forEach((reason, codes) -> groups.put(reason.name(), new JSONArray(codes)));
        return edit.putString(key + "_summary", snapshot.summary())
                .putString(key + "_details", new JSONObject(groups).toString());
    }

    Map<Reason, List<String>> groups(SharedPreferences state) throws JSONException {
        var saved = new JSONObject(state.getString(key + "_details", "{}"));
        var groups = new EnumMap<Reason, List<String>>(Reason.class);
        for (var reason : Reason.values()) {
            var entries = saved.optJSONArray(reason.name());
            if (entries == null || entries.length() == 0) continue;
            var codes = new ArrayList<String>();
            for (int index = 0; index < entries.length(); index++) codes.add(entries.getString(index));
            groups.put(reason, List.copyOf(codes));
        }
        return groups;
    }

    static Snapshot build(LocalDate day, LocalDate listingDay, Set<String> scope, Set<String> closes,
                          Set<String> assessed, Map<String, Reason> reasons) {
        var groups = new EnumMap<Reason, List<String>>(Reason.class);
        int closed = 0;
        int screened = 0;
        for (String code : new TreeSet<>(scope)) {
            boolean hasClose = closes.contains(code);
            if (hasClose) closed++;
            if (hasClose && assessed.contains(code)) {
                screened++;
                continue;
            }
            Reason reason = hasClose ? reasons.getOrDefault(code, Reason.FINANCIALS) : Reason.CLOSE;
            groups.computeIfAbsent(reason, ignored -> new ArrayList<>()).add(code);
        }
        groups.replaceAll((reason, codes) -> List.copyOf(codes));
        return new Snapshot(day, listingDay, scope.size(), closed, screened, Map.copyOf(groups));
    }
}
