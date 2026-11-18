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
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

final class UsFinancialFacts {
    record Facts(LocalDate filed, LocalDate equityDate, LocalDate shareDate, BigDecimal shares,
                 BigDecimal profit, BigDecimal equity, String accession,
                 String sharesBasis, boolean reconciledParentAmounts, String profitBasis) {}

    record Filing(LocalDate periodEnd, LocalDate filed, String form, String accession) {}
    record Assessment(Facts facts, String hold, Filing filing) {}

    private record Fact(LocalDate start, LocalDate end, LocalDate filed,
                        String form, String accession, BigDecimal value, boolean reconciled) {}

    static boolean matchesIssuer(JSONObject payload, int cik) {
        String value = String.valueOf(payload.opt("cik"));
        return value.matches("[0-9]{1,10}") && Long.parseLong(value) == cik;
    }

    static Facts read(JSONObject payload, int cik, LocalDate session) throws JSONException {
        return assess(payload, cik, session).facts();
    }

    static Assessment assess(JSONObject payload, int cik, LocalDate session) throws JSONException {
        if (!matchesIssuer(payload, cik)) throw new JSONException("SEC issuer mismatch");
        var document = payload.getJSONObject("facts");
        // Preserve an already complete set of directly reported figures.
        var primary = assess(document, session, false);
        return primary.facts() == null ? assess(document, session, true) : primary;
    }

    private static Assessment assess(JSONObject document, LocalDate session, boolean supplementary) {
        var gaap = document.optJSONObject("us-gaap");
        var equities = facts(gaap, "StockholdersEquity", "USD", session);
        if (supplementary) reconcileParentAmounts(equities,
                facts(gaap, "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "USD", session),
                facts(gaap, "MinorityInterest", "USD", session));
        var equity = latest(equities, false);
        if (equities.isEmpty()) return held("parent_equity_missing");
        if (equity == null || equity.start != null) return held("parent_equity_ambiguous");
        if (equity.end.isBefore(session.minusDays(150))) return held("parent_equity_stale");

        var shareRows = facts(document.optJSONObject("dei"), "EntityCommonStockSharesOutstanding", "shares", session);
        var cover = shareRows.stream().filter(f -> sameFiling(f, equity)
                && f.start == null && !f.end.isBefore(equity.end)).collect(Collectors.toList());
        var shares = one(cover);
        String sharesBasis = "cover";
        if (supplementary && cover.isEmpty()) {
            var balanceSheet = facts(gaap, "CommonStockSharesOutstanding", "shares", session).stream()
                    .filter(f -> samePeriod(f, equity)).collect(Collectors.toList());
            if (balanceSheet.isEmpty()) return held("shares_for_filing_missing", equity);
            shares = one(balanceSheet);
            sharesBasis = "balance_sheet";
        }
        if (!supplementary && cover.isEmpty()) return held("shares_for_filing_missing", equity);
        if (shares == null || shares.value.signum() <= 0 || shares.value.stripTrailingZeros().scale() > 0) {
            return held("shares_for_filing_ambiguous", equity);
        }

        var preferred = facts(gaap, "PreferredStockValue", "USD", session);
        if (preferred.stream().anyMatch(f -> sameFiling(f, equity) && f.end.equals(equity.end)
                && f.value.signum() != 0)) return held("preferred_equity_present");

        var profits = facts(gaap, "NetIncomeLoss", "USD", session);
        if (supplementary) reconcileParentAmounts(profits, facts(gaap, "ProfitLoss", "USD", session),
                facts(gaap, "NetIncomeLossAttributableToNoncontrollingInterest", "USD", session));
        var profit = calculateProfit(profits, equity);
        String profitBasis = "parent_net_income";
        if (supplementary && profit.value == null) {
            // Keep the same numerator definition in all periods of the trailing-year calculation.
            var common = calculateProfit(
                    facts(gaap, "NetIncomeLossAvailableToCommonStockholdersBasic", "USD", session), equity);
            if (common.value != null) {
                profit = common;
                profitBasis = "income_available_to_common";
            }
        }
        if (profit.value == null) return held(profit.hold);
        return new Assessment(new Facts(equity.filed, equity.end, shares.end, shares.value, profit.value, equity.value,
                equity.accession, sharesBasis, equity.reconciled || profit.reconciled, profitBasis), "", null);
    }

    private record Profit(BigDecimal value, boolean reconciled, String hold) {
        static Profit held(String reason) {
            return new Profit(null, false, reason);
        }
    }

    private static Profit calculateProfit(List<Fact> profits, Fact equity) {
        var atEnd = profits.stream().filter(f -> sameFiling(f, equity) && f.end.equals(equity.end))
                .collect(Collectors.toList());
        if ("10-K".equals(equity.form)) {
            var annual = one(atEnd.stream().filter(UsFinancialFacts::fullYear).collect(Collectors.toList()));
            return annual == null ? Profit.held("annual_profit_unconfirmed")
                    : new Profit(annual.value, annual.reconciled, "");
        }
        var annual = latest(profits.stream().filter(f -> "10-K".equals(f.form) && fullYear(f)
                && f.end.isBefore(equity.end) && f.filed.isBefore(equity.filed)).collect(Collectors.toList()), true);
        if (annual == null) return Profit.held("previous_annual_profit_unconfirmed");
        var ytd = one(atEnd.stream().filter(f -> annual.end.plusDays(1).equals(f.start)).collect(Collectors.toList()));
        if (ytd == null) return Profit.held("current_ytd_profit_unconfirmed");
        var prior = one(profits.stream().filter(f -> sameFiling(f, equity) && annual.start.equals(f.start)
                && f.end.isBefore(annual.end)
                && Math.abs(ChronoUnit.DAYS.between(f.end, ytd.end.minusYears(1))) <= 7
                && Math.abs(days(ytd) - days(f)) <= 7).collect(Collectors.toList()));
        if (prior == null) return Profit.held("prior_ytd_profit_unconfirmed");
        return new Profit(annual.value.add(ytd.value).subtract(prior.value),
                annual.reconciled || ytd.reconciled || prior.reconciled, "");
    }

    private static Assessment held(String reason) {
        return new Assessment(null, reason, null);
    }

    private static Assessment held(String reason, Fact equity) {
        return new Assessment(null, reason, new Filing(equity.end, equity.filed, equity.form, equity.accession));
    }

    private static void reconcileParentAmounts(List<Fact> parent, List<Fact> consolidated, List<Fact> minority) {
        var periods = new HashSet<Period>();
        for (var direct : parent) periods.add(Period.of(direct));
        var totals = groupPeriods(consolidated);
        var minorities = groupPeriods(minority);
        totals.forEach((period, items) -> {
            if (periods.contains(period) || !minorities.containsKey(period)) return;
            var total = one(items);
            var component = one(minorities.get(period));
            if (total == null || component == null) return;
            parent.add(new Fact(total.start, total.end, total.filed, total.form, total.accession,
                    total.value.subtract(component.value), true));
        });
    }

    private record Period(LocalDate start, LocalDate end, LocalDate filed, String form, String accession) {
        static Period of(Fact fact) {
            return new Period(fact.start, fact.end, fact.filed, fact.form, fact.accession);
        }
    }

    private static Map<Period, List<Fact>> groupPeriods(List<Fact> facts) {
        return facts.stream().collect(Collectors.groupingBy(Period::of));
    }

    private static boolean samePeriod(Fact first, Fact second) {
        return sameFiling(first, second) && first.end.equals(second.end)
                && Objects.equals(first.start, second.start);
    }

    private static List<Fact> facts(JSONObject namespace, String tag, String unit, LocalDate session) {
        var output = new ArrayList<Fact>();
        var concept = namespace == null ? null : namespace.optJSONObject(tag);
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
                output.add(new Fact(start, end, filed, form, accession, new BigDecimal(value.toString()), false));
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
