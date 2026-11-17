package jp.valuehunter.privatewatch;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Issuer disclosures used by the JPX manual preview. */
final class JpxReferenceFinancials {
    static final LocalDate ANNUAL_END = LocalDate.of(2026, 3, 31);
    private static final Map<String, Disclosures> BY_CODE = Map.of(
            "1301", new Disclosures(
                    new Annual(LocalDate.of(2026, 5, 15), new BigDecimal("576.02"),
                            new BigDecimal("6511.31"), "https://www.kyokuyo.co.jp/files/20260501.pdf"),
                    List.of(new Shares(LocalDate.of(2026, 9, 30), LocalDate.of(2026, 11, 6),
                            12_078_283L, 189_788L, "中間決算",
                            "https://www.kyokuyo.co.jp/files/20261106.pdf"))),
            "3861", new Disclosures(
                    new Annual(LocalDate.of(2026, 5, 15), new BigDecimal("61.10"),
                            new BigDecimal("1257.44"), "https://www.ojiholdings.co.jp/uploads/docs/ja0515irnews01.pdf"),
                    List.of(new Shares(LocalDate.of(2026, 9, 30), LocalDate.of(2026, 11, 6),
                            914_381_817L, 64_360_900L, "中間決算",
                            "https://www.ojiholdings.co.jp/uploads/news/docs/ja1106irnews02.pdf"))),
            "7203", new Disclosures(
                    new Annual(LocalDate.of(2026, 5, 8), new BigDecimal("295.25"),
                            new BigDecimal("3062.82"),
                            "https://global.toyota/pages/global_toyota/ir/financial-results/2026_4q_summary_jp.pdf"),
                    List.of(
                            new Shares(LocalDate.of(2026, 10, 31), LocalDate.of(2026, 11, 13),
                                    14_594_987_460L, 2_857_384_091L, "EDINET買付報告（ESOP信託分は控除外）",
                                    "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100ZH9B.pdf"),
                            new Shares(LocalDate.of(2026, 9, 30), LocalDate.of(2026, 10, 13),
                                    14_594_987_460L, 2_815_366_947L, "EDINET買付報告（ESOP信託分は控除外）",
                                    "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100Z7HA.pdf"))));

    private record Annual(LocalDate released, BigDecimal eps, BigDecimal bps, String source) {}

    private record Shares(LocalDate asOf, LocalDate released, long issued, long treasury,
                          String sourceLabel, String source) {
        long outstanding() {
            return issued - treasury;
        }
    }

    private record Disclosures(Annual annual, List<Shares> shares) {}

    enum Condition {
        UNAVAILABLE("参考財務条件は保留（立会日より前の通期決算なし）"),
        UNUSABLE("参考財務条件は対象外（EPS・BPSがともに正でない）"),
        MATCH("参考財務条件に一致（PER 15倍以下・PBR 1倍以下）"),
        PER_OVER("参考財務条件は対象外 · PER 15倍超"),
        PBR_OVER("参考財務条件は対象外 · PBR 1倍超"),
        BOTH_OVER("参考財務条件は対象外 · PER 15倍超 · PBR 1倍超");

        final String label;

        Condition(String label) {
            this.label = label;
        }
    }

    static Condition condition(String code, LocalDate session, BigDecimal close) {
        var disclosures = BY_CODE.get(code);
        if (disclosures == null || !session.isAfter(disclosures.annual().released())) {
            return Condition.UNAVAILABLE;
        }
        var annual = disclosures.annual();
        if (annual.eps().signum() <= 0 || annual.bps().signum() <= 0) return Condition.UNUSABLE;

        boolean perOver = close.compareTo(annual.eps().multiply(BigDecimal.valueOf(JapanScreen.MAX_PER))) > 0;
        boolean pbrOver = close.compareTo(annual.bps().multiply(BigDecimal.valueOf(JapanScreen.MAX_PBR))) > 0;
        if (perOver) return pbrOver ? Condition.BOTH_OVER : Condition.PER_OVER;
        return pbrOver ? Condition.PBR_OVER : Condition.MATCH;
    }

    static void appendHtml(StringBuilder html, String code, LocalDate session, BigDecimal close) {
        var disclosures = BY_CODE.get(code);
        if (disclosures == null) return;
        var annual = disclosures.annual();
        if (session.isAfter(annual.released())) {
            html.append("<br>参考PER ").append(ratio(close, annual.eps()))
                    .append(" / 参考PBR ").append(ratio(close, annual.bps()))
                    .append("<br>").append(ANNUAL_END).append("期 EPS ")
                    .append(annual.eps().toPlainString()).append("円 / BPS ")
                    .append(annual.bps().toPlainString()).append("円")
                    .append(" · <a href='").append(annual.source()).append("'>通期決算</a>")
                    .append("<br>決算公表時の1株値で試算（以降の株式分割等は未反映）");
        }
        html.append("<br>").append(condition(code, session, close).label);
        appendShareData(html, code, session);
    }

    static void appendShareData(StringBuilder html, String code, LocalDate session) {
        var disclosures = BY_CODE.get(code);
        if (disclosures == null) return;
        for (var shares : disclosures.shares()) {
            if (!session.isAfter(shares.released())) continue;
            html.append("<br>自己株式控除後 ").append(shares.outstanding()).append("株")
                    .append("（").append(shares.asOf()).append("時点）")
                    .append(" · <a href='").append(shares.source()).append("'>")
                    .append(shares.sourceLabel()).append("</a>");
            break;
        }
        html.append("<br>時価総額は保留（立会日の株式数未照合）");
    }

    private static String ratio(BigDecimal close, BigDecimal denominator) {
        return denominator.signum() <= 0 ? "算出不可"
                : close.divide(denominator, 2, RoundingMode.HALF_UP).toPlainString() + "倍";
    }
}
