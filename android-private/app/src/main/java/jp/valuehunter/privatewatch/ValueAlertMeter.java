package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.math.MathContext;
import java.util.List;

/** Versioned scoring for the alert preview. Scores measure evidence, not forecasts. */
final class ValueAlertMeter {
    static final Thresholds DEFAULT = new Thresholds(60, 75, 85);
    static final List<String> LABELS = List.of("対象外", "割安", "かなり割安", "超割安");

    record Thresholds(int first, int second, int third) {
        Thresholds {
            if (first < 1 || first >= second || second >= third || third > 100) {
                throw new IllegalArgumentException("Invalid alert thresholds");
            }
        }

        static Thresholds read(String saved) {
            try {
                String[] parts = saved.split(",", -1);
                if (parts.length == 3) return new Thresholds(Integer.parseInt(parts[0]),
                        Integer.parseInt(parts[1]), Integer.parseInt(parts[2]));
            } catch (IllegalArgumentException invalid) {
                // Older and malformed settings use the defaults.
            }
            return DEFAULT;
        }

        String encode() { return first + "," + second + "," + third; }

        int level(int points) {
            if (points >= third) return 3;
            if (points >= second) return 2;
            return points >= first ? 1 : 0;
        }
    }

    record Score(int points, int ceiling, int confirmed) {
        int level(Thresholds thresholds) { return Math.min(ceiling, thresholds.level(points)); }
    }

    static Score assess(BigDecimal price, BigDecimal profit, BigDecimal equity, List<BigDecimal> annualEps,
                        Integer cash, Integer peers, Integer balance) {
        if (price == null || profit == null || equity == null
                || price.signum() <= 0 || profit.signum() <= 0 || equity.signum() <= 0) return new Score(0, 0, 0);
        double per = price.divide(profit, MathContext.DECIMAL64).doubleValue();
        double pbr = price.divide(equity, MathContext.DECIMAL64).doubleValue();
        int perPoints = multiple(per, 7, 10, 15, 25);
        int pbrPoints = multiple(pbr, .6, .8, 1, 1.8);
        boolean growthKnown = annualEps.size() >= 2 && annualEps.get(1).signum() > 0;
        boolean falling = growthKnown && annualEps.get(0).compareTo(
                annualEps.get(1).multiply(new BigDecimal("0.8"))) <= 0;
        boolean threeProfitable = annualEps.size() >= 3
                && annualEps.subList(0, 3).stream().allMatch(eps -> eps.signum() > 0);
        boolean loss = annualEps.stream().anyMatch(eps -> eps.signum() <= 0);
        int earnings = falling || loss ? 25 : threeProfitable ? 95 : growthKnown ? 80 : 70;
        int score = (35 * perPoints + 25 * pbrPoints + 20 * earnings
                + 10 * neutral(cash) + 5 * neutral(peers) + 5 * neutral(balance)) / 100;
        int confirmed = 3 + (cash == null ? 0 : 1) + (peers == null ? 0 : 1) + (balance == null ? 0 : 1);
        boolean warning = falling || loss || (cash != null && cash == 0) || (balance != null && balance == 0);
        if (warning || !atMost(price, profit, "15") || !atMost(price, equity, "1")) {
            return new Score(score, 0, confirmed);
        }
        if (threeProfitable && positive(cash) && positive(peers) && positive(balance)
                && atMost(price, profit, "9") && atMost(price, equity, "0.8")) return new Score(score, 3, confirmed);
        // SEC companyfacts supplies comparable EPS and operating cash flow, but not a
        // reliable peer score or balance-strength score for the broad US universe.
        // Never treat missing evidence as confirmed: require substantially cheaper
        // valuation, three profitable annual EPS observations and positive cash flow
        // in both comparable years before allowing the top tier without those scores.
        // Explicit adverse peer/balance evidence must not be bypassed by this fallback.
        if (threeProfitable && positive(cash) && peers == null && balance == null
                && atMost(price, profit, "7") && atMost(price, equity, "0.6")) {
            return new Score(score, 3, confirmed);
        }
        if (growthKnown && (positive(cash) || positive(peers))
                && atMost(price, profit, "12") && atMost(price, equity, "0.9")) return new Score(score, 2, confirmed);
        return new Score(score, 1, confirmed);
    }

    /** US SEC path: verified balance health can replace the unknown balance slot,
     * but cannot replace a missing sector-relative comparison without strict valuation. */
    static Score assessUs(BigDecimal price, BigDecimal profit, BigDecimal equity, List<BigDecimal> annualEps,
                          Integer cash, Integer peers, Integer balance) {
        var measured = assess(price, profit, equity, annualEps, cash, peers, balance);
        if (measured.ceiling() == 3 || peers != null || !positive(balance)) return measured;
        var conservative = assess(price, profit, equity, annualEps, cash, null, null);
        if (conservative.ceiling() == 3)
            return new Score(measured.points(), 3, measured.confirmed());
        return measured;
    }

    static int promotion(Score previous, Score current, Thresholds thresholds) {
        if (previous == null) return 0;
        int before = previous.level(thresholds);
        int after = current.level(thresholds);
        return after > before ? after : 0;
    }

    private static boolean atMost(BigDecimal price, BigDecimal denominator, String multiple) {
        return price.compareTo(denominator.multiply(new BigDecimal(multiple))) <= 0;
    }

    private static int neutral(Integer evidence) { return evidence == null ? 50 : evidence; }

    private static boolean positive(Integer evidence) { return evidence != null && evidence >= 70; }

    private static int multiple(double value, double strong, double good, double basic, double weak) {
        if (value <= strong) return 100;
        if (value <= good) return interpolate(value, strong, good, 100, 80);
        if (value <= basic) return interpolate(value, good, basic, 80, 60);
        if (value <= weak) return interpolate(value, basic, weak, 60, 0);
        return 0;
    }

    private static int interpolate(double value, double from, double to, int high, int low) {
        return (int) Math.round(high + (low - high) * (value - from) / (to - from));
    }
}
