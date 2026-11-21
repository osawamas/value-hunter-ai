package jp.valuehunter.privatewatch;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.Set;

final class JpxTradingDays {
    // JPX cash-market closures, https://www.jpx.co.jp/corporate/about-jpx/calendar/index.html
    private static final Set<Integer> CLOSURES_2026 = Set.of(
            101, 102, 103, 112, 211, 223, 320, 429, 503, 504, 505, 506, 720, 811, 921, 922, 923, 1012, 1103, 1123, 1231);
    private static final Set<Integer> CLOSURES_2027 = Set.of(
            101, 102, 103, 111, 211, 223, 321, 322, 429, 503, 504, 505, 719, 811, 920, 923, 1011, 1103, 1123, 1231);
    private static final ZoneId TOKYO = ZoneId.of("Asia/Tokyo");
    private static final LocalTime CLOSE = LocalTime.of(15, 30);

    private JpxTradingDays() {}

    static LocalDate expected(Instant instant) {
        var local = instant.atZone(TOKYO);
        var day = local.toLocalDate();
        return onOrBefore(local.toLocalTime().isBefore(CLOSE) ? day.minusDays(1) : day);
    }

    static LocalDate onOrBefore(LocalDate day) {
        while (true) {
            var closures = switch (day.getYear()) {
                case 2026 -> CLOSURES_2026;
                case 2027 -> CLOSURES_2027;
                default -> null;
            };
            if (closures == null) return null;
            var weekday = day.getDayOfWeek();
            if (weekday != DayOfWeek.SATURDAY && weekday != DayOfWeek.SUNDAY
                    && !closures.contains(day.getMonthValue() * 100 + day.getDayOfMonth())) return day;
            day = day.minusDays(1);
        }
    }
}
