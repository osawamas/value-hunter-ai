package jp.valuehunter.privatewatch;

import java.time.LocalDate;

final class SgValuation {
    static final LocalDate FINANCIAL_PERIOD = LocalDate.of(2026, 6, 30);
    private static final LocalDate FIRST_USABLE_SESSION = LocalDate.of(2026, 8, 14);

    static boolean financialsAvailable(LocalDate session) {
        return !session.isBefore(FIRST_USABLE_SESSION);
    }

    // S63 FY2025 annual report and 1H2026 results, amounts in SGD.
    private static final long TTM_PROFIT = (462_770L + 512_126L - 402_829L) * 1000;
    private static final long PARENT_EQUITY = 2_524_548_000L;

    record Trial(long shares, double cap, double per, double pbr) {
        boolean qualifies(double oneShareYen) {
            return Double.isFinite(oneShareYen) && oneShareYen > 0 && oneShareYen <= JapanScreen.BUDGET
                    && per > 0 && per <= JapanScreen.MAX_PER && pbr > 0 && pbr <= JapanScreen.MAX_PBR;
        }
    }

    static boolean needsPreviousEvaluation(SgCloseCheck.Pair pair, String lastEvaluated, boolean qualified) {
        return qualified && !lastEvaluated.isEmpty()
                && lastEvaluated.compareTo(pair.previous().session().toString()) < 0;
    }

    static boolean shouldAlert(SgCloseCheck.Pair pair, String lastEvaluated, boolean wasQualified,
                               boolean qualified, Boolean previousQualified) {
        String previous = pair.previous().session().toString();
        if (!qualified || !pair.latest().session().isAfter(pair.previous().session())) return false;
        if (previous.equals(lastEvaluated)) return !wasQualified;
        return needsPreviousEvaluation(pair, lastEvaluated, qualified) && Boolean.FALSE.equals(previousQualified);
    }

    static Trial forClose(SgCloseCheck.Close close, long shares) {
        if (shares <= 0 || !financialsAvailable(close.session())) return null;
        double cap = close.sgd() * shares;
        return new Trial(shares, cap, cap / TTM_PROFIT, cap / PARENT_EQUITY);
    }
}
