package jp.valuehunter.privatewatch;

import java.math.BigDecimal;

/** Classifies a close against as-of per-share financial data on the same price basis. */
final class ValueCandidateScreen {
    private static final BigDecimal PER = new BigDecimal("15");
    private static final BigDecimal PBR = BigDecimal.ONE;
    private static final BigDecimal REFERENCE_PER = new BigDecimal("20");
    private static final BigDecimal REFERENCE_PBR = new BigDecimal("1.5");

    enum Level {
        HELD("保留"), OUTSIDE("対象外"), REFERENCE("参考候補"), PRIORITY("優先候補");

        final String label;

        Level(String label) {
            this.label = label;
        }

        boolean qualifies() {
            return this == PRIORITY || this == REFERENCE;
        }

        boolean entersFrom(Level before) {
            return qualifies() && (before == OUTSIDE || (this == PRIORITY && before == REFERENCE));
        }
    }

    static Level assess(BigDecimal close, BigDecimal eps, BigDecimal bps) {
        if (close == null || close.signum() <= 0 || (eps == null && bps == null)
                || (eps != null && eps.signum() <= 0) || (bps != null && bps.signum() <= 0)) {
            return Level.HELD;
        }
        boolean perPasses = atMost(close, eps, PER);
        boolean pbrPasses = atMost(close, bps, PBR);
        if (perPasses && pbrPasses) return Level.PRIORITY;
        if ((perPasses && (bps == null || atMost(close, bps, REFERENCE_PBR)))
                || (pbrPasses && (eps == null || atMost(close, eps, REFERENCE_PER)))) {
            return Level.REFERENCE;
        }
        return Level.OUTSIDE;
    }

    private static boolean atMost(BigDecimal close, BigDecimal denominator, BigDecimal ceiling) {
        return denominator != null && close.compareTo(denominator.multiply(ceiling)) <= 0;
    }
}
