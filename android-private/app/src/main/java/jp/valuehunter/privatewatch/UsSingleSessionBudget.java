package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

final class UsSingleSessionBudget {
    enum Verdict { WITHIN, OUTSIDE, HELD }
    private static final BigDecimal BUDGET = BigDecimal.valueOf(JapanScreen.BUDGET);

    static Verdict check(LocalDate day, UsScreen.Fx fx, BigDecimal close) {
        if (fx == null || !day.equals(fx.date()) || !Double.isFinite(fx.yenPerDollar())
                || fx.yenPerDollar() <= 0 || close == null || close.signum() <= 0) return Verdict.HELD;
        var yen = close.multiply(BigDecimal.valueOf(fx.yenPerDollar())).movePointRight(2);
        return yen.compareTo(BUDGET) <= 0 ? Verdict.WITHIN : Verdict.OUTSIDE;
    }

    static void addUnpairedCurrentOnly(Set<String> eligible, Set<String> pending,
                                       Map<String, String> sameDay, Set<String> paired,
                                       Set<String> todayPrices, Set<String> priorPrices) {
        for (var symbol : pending) {
            if (sameDay.containsKey(symbol) && todayPrices.contains(symbol)
                    && !priorPrices.contains(symbol) && !paired.contains(symbol)) {
                eligible.add(symbol);
            }
        }
    }

    static Set<String> targets(Set<String> pending, Map<String, String> sameDay, Set<String> paired) {
        var targets = new TreeSet<>(pending);
        targets.retainAll(sameDay.keySet());
        targets.removeAll(paired);
        return targets;
    }
}
