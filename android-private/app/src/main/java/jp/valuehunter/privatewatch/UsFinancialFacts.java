package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

final class UsFinancialFacts {
    record Facts(LocalDate filed, LocalDate shareDate, BigDecimal shares,
                 BigDecimal profit, BigDecimal equity, String accession) {}

    private record Fact(LocalDate start, LocalDate end, LocalDate filed,
                        String form, String accession, BigDecimal value) {}

    static boolean matchesIssuer(JSONObject payload, int cik) {
        String value = String.valueOf(payload.opt("cik"));
        return value.matches("[0-9]{1,10}") && Long.parseLong(value) == cik;
    }

    static Facts read(JSONObject payload, int cik, LocalDate session) throws JSONException {
        if (!matchesIssuer(payload, cik)) throw new JSONException("SEC issuer mismatch");
        var document = payload.getJSONObject("facts");
        var gaap = document.getJSONObject("us-gaap");
        var equity = latest(facts(gaap, "StockholdersEquity", "USD", session), false);
        if (equity == null || equity.start != null
                || equity.end.isBefore(session.minusDays(150))) return null;

        var shareRows = facts(document.getJSONObject("dei"), "EntityCommonStockSharesOutstanding", "shares", session);
        var shares = one(shareRows.stream().filter(f -> sameFiling(f, equity)
                && f.start == null && !f.end.isBefore(equity.end)).collect(Collectors.toList()));
        if (shares == null || shares.value.signum() <= 0 || shares.value.stripTrailingZeros().scale() > 0) return null;

        var preferred = facts(gaap, "PreferredStockValue", "USD", session);
        if (preferred.stream().anyMatch(f -> sameFiling(f, equity) && f.end.equals(equity.end)
                && f.value.signum() != 0)) return null;

        var profits = facts(gaap, "NetIncomeLoss", "USD", session);
        var atEnd = profits.stream().filter(f -> sameFiling(f, equity) && f.end.equals(equity.end)).collect(Collectors.toList());
        BigDecimal profit;
        if ("10-K".equals(equity.form)) {
            var annual = one(atEnd.stream().filter(UsFinancialFacts::fullYear).collect(Collectors.toList()));
            if (annual == null) return null;
            profit = annual.value;
        } else {
            var annual = latest(profits.stream().filter(f -> "10-K".equals(f.form) && fullYear(f)
                    && f.end.isBefore(equity.end) && f.filed.isBefore(equity.filed)).collect(Collectors.toList()), true);
            if (annual == null) return null;
            var ytd = one(atEnd.stream().filter(f -> annual.end.plusDays(1).equals(f.start)).collect(Collectors.toList()));
            if (ytd == null) return null;
            var prior = one(profits.stream().filter(f -> sameFiling(f, equity) && annual.start.equals(f.start)
                    && f.end.isBefore(annual.end)
                    && Math.abs(ChronoUnit.DAYS.between(f.end, ytd.end.minusYears(1))) <= 7
                    && Math.abs(days(ytd) - days(f)) <= 7).collect(Collectors.toList()));
            if (prior == null) return null;
            profit = annual.value.add(ytd.value).subtract(prior.value);
        }
        return new Facts(equity.filed, shares.end, shares.value, profit, equity.value, equity.accession);
    }

    private static List<Fact> facts(JSONObject namespace, String tag, String unit, LocalDate session) {
        var output = new ArrayList<Fact>();
        var concept = namespace.optJSONObject(tag);
        var units = concept == null ? null : concept.optJSONObject("units");
        JSONArray rows = units == null ? null : units.optJSONArray(unit);
        if (rows == null) return output;
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.optJSONObject(i);
            if (row == null) continue;
            String form = row.optString("form");
            String accession = row.optString("accn");
            if (!(form.equals("10-K") || form.equals("10-Q")) || !accession.matches("[0-9]{10}-[0-9]{2}-[0-9]{6}")) continue;
            try {
                LocalDate filed = LocalDate.parse(row.getString("filed"));
                LocalDate end = LocalDate.parse(row.getString("end"));
                LocalDate start = row.has("start") ? LocalDate.parse(row.getString("start")) : null;
                Object value = row.get("val");
                if (!filed.isBefore(session) || end.isAfter(filed) || (start != null && start.isAfter(end))
                        || !(value instanceof Number)) continue;
                output.add(new Fact(start, end, filed, form, accession, new BigDecimal(value.toString())));
            } catch (DateTimeParseException | JSONException | NumberFormatException invalid) {
                // Other valid filing records may still contain the requested fiscal period.
            }
        }
        return output;
    }

    private static Fact latest(List<Fact> facts, boolean allowRepeatedAnnual) {
        var order = Comparator.comparing(Fact::end).thenComparing(Fact::filed);
        var latest = facts.stream().max(order).orElse(null);
        if (latest == null) return null;
        var tied = facts.stream().filter(f -> order.compare(f, latest) == 0).collect(Collectors.toList());
        if (allowRepeatedAnnual) {
            if (tied.stream().anyMatch(f -> !f.start.equals(latest.start) || f.value.compareTo(latest.value) != 0)) return null;
            return latest;
        }
        return one(tied);
    }

    private static Fact one(List<Fact> facts) {
        if (facts.isEmpty()) return null;
        var first = facts.get(0);
        return facts.stream().allMatch(first::equals) ? first : null;
    }

    private static boolean sameFiling(Fact left, Fact right) {
        return left.accession.equals(right.accession) && left.filed.equals(right.filed) && left.form.equals(right.form);
    }

    private static long days(Fact fact) {
        return ChronoUnit.DAYS.between(fact.start, fact.end) + 1;
    }

    private static boolean fullYear(Fact fact) {
        return fact.start != null && days(fact) >= 350 && days(fact) <= 380;
    }
}
