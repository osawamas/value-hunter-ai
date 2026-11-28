package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.time.LocalDate;

/** Valuation using cash generation, sales and balance-sheet resilience. */
final class JpxOperatingValuation {
    private JpxOperatingValuation() {}

    static ValueAlertMeter.Score assess(JpxAnnualSummary.Annual annual, LocalDate day, BigDecimal close) {
        var facts = annual.operating();
        if (facts == null || close == null || close.signum() <= 0) return null;
        // Use issued ordinary shares including treasury for a conservative price multiple.
        var marketCap = annual.onShareBasis(day, close, true).multiply(facts.issuedShares());
        var cashFlow = annual.onShareBasis(day, facts.cashFlow(), false);
        var revenue = annual.onShareBasis(day, facts.revenue(), false);
        boolean soundBalance = atLeast(facts.netAssets(), facts.assets(), "0.25");
        boolean weakParentEquity = annual.bps() != null && annual.bps().signum() <= 0;
        if (cashFlow == null) {
            var profit = facts.operatingProfit();
            var prior = facts.priorProfit();
            // Both periods must show operating profitability. This first-tier route does not
            // infer cash generation and never substitutes for disclosed weak cash flow.
            if (profit == null || prior == null || prior.signum() <= 0 || profit.compareTo(prior) <= 0
                    || annual.bps() == null || weakParentEquity
                    || !atLeast(facts.netAssets(), facts.assets(), "0.50")
                    || !atLeast(facts.revenue(), marketCap, "2")
                    || !atLeast(annual.onShareBasis(day, profit, false), marketCap, "0.15")) return null;
            return new ValueAlertMeter.Score(65, 1, 4);
        }
        if (!soundBalance || weakParentEquity || !atLeast(cashFlow, marketCap, "0.08")
                || !atLeast(revenue, marketCap, "1")) {
            return new ValueAlertMeter.Score(0, 0, 3);
        }

        var profit = facts.operatingProfit();
        var previous = facts.priorProfit();
        boolean profitable = profit != null && profit.signum() > 0;
        boolean improving = profitable && previous != null && profit.compareTo(previous) > 0;
        if (improving && atLeast(profit, facts.revenue(), "0.05")
                && atLeast(facts.netAssets(), facts.assets(), "0.50")
                && atLeast(cashFlow, marketCap, "0.20") && atLeast(revenue, marketCap, "2.5")) {
            return new ValueAlertMeter.Score(93, 3, 4);
        }
        if (profitable && (previous == null || profit.compareTo(previous) >= 0)
                && atLeast(facts.netAssets(), facts.assets(), "0.40")
                && atLeast(cashFlow, marketCap, "0.14") && atLeast(revenue, marketCap, "1.5")) {
            return new ValueAlertMeter.Score(82, 2, improving ? 4 : 3);
        }
        // A firm with an operating loss can only enter the first tier with
        // both materially stronger cash generation and improving operating results.
        if (!profitable && (profit == null || previous == null || profit.compareTo(previous) <= 0
                || !atLeast(cashFlow, marketCap, "0.14"))) {
            return new ValueAlertMeter.Score(0, 0, 3);
        }
        return new ValueAlertMeter.Score(69, 1, improving ? 4 : 3);
    }

    private static boolean atLeast(BigDecimal numerator, BigDecimal denominator, String minimum) {
        return numerator.compareTo(denominator.multiply(new BigDecimal(minimum))) >= 0;
    }
}
