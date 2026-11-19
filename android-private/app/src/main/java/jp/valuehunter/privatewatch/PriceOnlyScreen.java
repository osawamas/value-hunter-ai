package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;
import java.util.function.Function;

/** Compares the actual yen purchase cost for ordinary shares without using financial statements. */
final class PriceOnlyScreen {
    private static final BigDecimal BUDGET = BigDecimal.valueOf(JapanScreen.BUDGET);

    record BudgetEntry(String code, BigDecimal yen) {}

    record Result(int assessed, List<BudgetEntry> entered) {
        static Result empty() { return new Result(0, List.of()); }
    }

    private PriceOnlyScreen() {}

    static Result budgetEntries(Set<String> codes, Set<String> financialCodes,
                                Function<String, BigDecimal> previousYenPerShare,
                                Function<String, BigDecimal> latestYenPerShare) {
        int assessed = 0;
        var entered = new ArrayList<BudgetEntry>();
        for (String code : codes) {
            if (financialCodes.contains(code)) continue;
            var previous = previousYenPerShare.apply(code);
            var latest = latestYenPerShare.apply(code);
            if (previous == null || latest == null || previous.signum() <= 0 || latest.signum() <= 0) continue;
            assessed++;
            var cost = latest.movePointRight(2);
            if (previous.movePointRight(2).compareTo(BUDGET) > 0 && cost.compareTo(BUDGET) <= 0) {
                entered.add(new BudgetEntry(code, cost));
            }
        }
        entered.sort(Comparator.comparing(BudgetEntry::code));
        return new Result(assessed, List.copyOf(entered));
    }
}
