package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

final class JapanScreen {
    private static final Set<String> MARKETS = new HashSet<>(Arrays.asList("0111", "0112", "0113"));
    static final int BUDGET = 100_000;
    static final double MAX_PER = 15;
    static final double MAX_PBR = 1;

    record Candidate(String code, String name, double close, double per, double pbr) {
        int quantity() { return close <= BUDGET / 100.0 ? 100 : 1; }
        double cost() { return close * quantity(); }
        double score() { return (1 / per + 1 / pbr) / 2; }
    }

    static List<Candidate> find(LocalDate date, JSONArray bars, JSONArray metrics, JSONArray master)
            throws JSONException {
        var prices = index(date, bars);
        var ratios = index(date, metrics);
        var names = index(date, master);
        if (ratios.isEmpty() || names.isEmpty()) {
            throw new JSONException("同日の銘柄・指標データを取得できなかった");
        }
        List<Candidate> candidates = new ArrayList<>();
        for (var entry : prices.entrySet()) {
            String code = entry.getKey();
            var issue = names.get(code);
            var valuation = ratios.get(code);
            if (issue == null || valuation == null || !MARKETS.contains(issue.optString("Mkt"))
                    || !"011".equals(issue.optString("ProdCat"))) continue;
            double close = entry.getValue().optDouble("C");
            double per = valuation.optDouble("PER");
            double pbr = valuation.optDouble("PBR");
            String name = issue.optString("CoName");
            if (entry.getValue().optDouble("Vo") > 0 && close > 0 && close <= BUDGET && per > 0 && per <= MAX_PER
                    && pbr > 0 && pbr <= MAX_PBR && !name.trim().isEmpty()) {
                candidates.add(new Candidate(code.substring(0, 4), name, close, per, pbr));
            }
        }
        candidates.sort(Comparator.comparingInt(Candidate::quantity).reversed()
                .thenComparing(Comparator.comparingDouble(Candidate::score).reversed())
                .thenComparing(Candidate::code));
        return candidates;
    }

    static List<Candidate> newlyQualified(List<Candidate> current, Set<String> previous) {
        return current.stream().filter(row -> !previous.contains(row.code())).collect(Collectors.toList());
    }

    private static Map<String, JSONObject> index(LocalDate date, JSONArray rows) throws JSONException {
        var index = new HashMap<String, JSONObject>();
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.getJSONObject(i);
            if (!date.toString().equals(row.getString("Date"))) {
                throw new JSONException("取得データの取引日が一致しない");
            }
            String code = row.getString("Code");
            if (code.matches("[0-9][0-9A-Z]{3}0") && index.putIfAbsent(code, row) != null) {
                throw new JSONException("同日に同じ銘柄が重複している");
            }
        }
        return index;
    }
}
