package jp.valuehunter.privatewatch;

final class SgValuation {
    // S63 FY2025 annual report and 1H2026 results, amounts in SGD.
    private static final long TTM_PROFIT = (462_770L + 512_126L - 402_829L) * 1000;
    private static final long PARENT_EQUITY = 2_524_548_000L;

    record Trial(long shares, double cap, double per, double pbr) {
        boolean qualifies(double oneShareYen) {
            return Double.isFinite(oneShareYen) && oneShareYen > 0 && oneShareYen <= JapanScreen.BUDGET
                    && per > 0 && per <= JapanScreen.MAX_PER && pbr > 0 && pbr <= JapanScreen.MAX_PBR;
        }
    }

    static boolean shouldAlert(SgCloseCheck.Pair pair, String lastEvaluated, boolean wasQualified, boolean qualified) {
        // Consecutive provider sessions only. A gap establishes a new baseline.
        return qualified && !wasQualified && pair.previous().session().toString().equals(lastEvaluated)
                && pair.latest().session().isAfter(pair.previous().session());
    }

    static Trial forClose(SgCloseCheck.Close close) {
        // SGXNet buyback notices supply dated shares excluding treasury.
        long shares = switch (close.session().toString()) {
            case "2026-10-26" -> 3_116_347_115L;
            case "2026-11-13" -> 3_115_847_115L;
            case "2026-11-16" -> 3_115_347_115L;
            default -> 0;
        };
        return forClose(close, shares);
    }

    static Trial forClose(SgCloseCheck.Close close, long shares) {
        if (shares <= 0) return null;
        double cap = close.sgd() * shares;
        return new Trial(shares, cap, cap / TTM_PROFIT, cap / PARENT_EQUITY);
    }
}
