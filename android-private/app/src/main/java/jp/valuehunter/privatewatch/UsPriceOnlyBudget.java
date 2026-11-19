package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

final class UsPriceOnlyBudget {
    record Result(PriceOnlyScreen.Result screen, boolean verifiedPriceBasis,
                  List<PriceOnlyScreen.BudgetEntry> notificationEntries, int listed, int financialAssessed) {
        Result(PriceOnlyScreen.Result screen, boolean verifiedPriceBasis, int listed, int financialAssessed) {
            this(screen, verifiedPriceBasis, verifiedPriceBasis ? screen.entered() : List.of(), listed, financialAssessed);
        }

        int combinedAssessed() { return financialAssessed + screen.assessed(); }

        Result corroborated(Set<String> matched) {
            return new Result(screen, verifiedPriceBasis,
                    screen.entered().stream().filter(entry -> matched.contains(entry.code())).toList(),
                    listed, financialAssessed);
        }
    }

    private UsPriceOnlyBudget() {}

    static Result compare(JSONObject previous, JSONObject latest, JSONArray rates, Set<String> ordinary,
                          UsReferenceAlerts.Screen financial, LocalDate expectedDay) throws JSONException {
        var day = LocalDate.parse(latest.getString("trading_date_et"));
        var priorDay = LocalDate.parse(previous.getString("trading_date_et"));
        var provider = latest.getString("source");
        if (!day.equals(expectedDay) || !day.equals(financial.day()) || !provider.equals(financial.provider())
                || !provider.equals(previous.getString("source")) || !priorDay.equals(previousSession(day))) {
            return new Result(PriceOnlyScreen.Result.empty(), false, ordinary.size(), 0);
        }

        var oldFx = UsScreen.readFx(rates, priorDay);
        var newFx = UsScreen.readFx(rates, day);
        if (!oldFx.date().equals(priorDay) || !newFx.date().equals(day)) {
            return new Result(PriceOnlyScreen.Result.empty(), false, ordinary.size(), 0);
        }
        var oldPrices = UsDeviceFinancials.prices(previous.getJSONArray("closes"));
        var newPrices = UsDeviceFinancials.prices(latest.getJSONArray("closes"));
        var oldRate = BigDecimal.valueOf(oldFx.yenPerDollar());
        var newRate = BigDecimal.valueOf(newFx.yenPerDollar());
        var calculated = PriceOnlyScreen.budgetEntries(ordinary, financial.rows().keySet(),
                symbol -> yen(oldPrices.get(symbol), oldRate), symbol -> yen(newPrices.get(symbol), newRate));
        boolean unadjusted = UsDailyCloses.MASSIVE_SOURCE.equals(provider)
                && Boolean.FALSE.equals(previous.opt("adjusted")) && Boolean.FALSE.equals(latest.opt("adjusted"));
        int financialAssessed = (int) financial.rows().keySet().stream()
                .filter(ordinary::contains).filter(newPrices::containsKey).count();
        return new Result(calculated, unadjusted, ordinary.size(), financialAssessed);
    }

    static boolean canCorroborateDolt(JSONObject previous, JSONObject latest) {
        return UsDoltCloses.SOURCE.equals(previous.optString("source"))
                && UsDoltCloses.SOURCE.equals(latest.optString("source"))
                && previous.has("adjusted") && previous.isNull("adjusted")
                && latest.has("adjusted") && latest.isNull("adjusted");
    }

    static Set<String> ordinary(UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq,
                                LocalDate day) throws JSONException {
        if (!nyse.date().equals(nasdaq.date()) || nyse.date().isBefore(day)
                || nyse.date().isAfter(day.plusDays(4))
                || !java.util.Collections.disjoint(nyse.symbols(), nasdaq.symbols())) {
            throw new JSONException("US listing dates or exchanges do not match");
        }
        var symbols = new HashSet<>(nyse.symbols());
        symbols.addAll(nasdaq.symbols());
        return symbols;
    }

    static LocalDate previousSession(LocalDate day) {
        return UsDailyCloses.onOrBeforeTradingDay(day.minusDays(1));
    }

    private static BigDecimal yen(BigDecimal usd, BigDecimal rate) {
        return usd == null ? null : usd.multiply(rate);
    }
}
