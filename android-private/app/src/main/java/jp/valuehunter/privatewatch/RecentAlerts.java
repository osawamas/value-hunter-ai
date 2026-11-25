package jp.valuehunter.privatewatch;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/** Read-only four-calendar-day projection of the durable posted-notification ledger. */
final class RecentAlerts {
    static final ZoneId JAPAN = ZoneId.of("Asia/Tokyo");
    static final int DAYS = 4;
    private static final Pattern CODE = Pattern.compile("(?:[A-Z][A-Z0-9.$+^=/_-]{0,23}|[0-9]{4}[A-Z]?)");
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm");

    record Row(LocalDate postedDay, String time, String code, String company, String grade,
               String title, String detail) {}

    private RecentAlerts() {}

    static List<Row> rows(List<NotificationHistory.Entry> entries, LocalDate today,
                          Map<String,String> companyNames) {
        var found = new ArrayList<Row>();
        for (var event : entries) {
            var local = Instant.ofEpochMilli(event.postedAt()).atZone(JAPAN);
            LocalDate day=local.toLocalDate();
            if(day.isBefore(today.minusDays(DAYS-1)) || day.isAfter(today)) continue;
            String time=local.format(CLOCK);
            for(String raw : event.detail().split("\\r?\\n")) {
                int delimiter=raw.indexOf(" · ");
                if(delimiter<=0)continue;
                String prefix=raw.substring(0,delimiter).trim();
                String code=prefix, embedded="";
                int nameBegin=prefix.indexOf(" (");
                if(nameBegin>0 && prefix.endsWith(")")) {
                    code=prefix.substring(0,nameBegin);
                    embedded=prefix.substring(nameBegin+2,prefix.length()-1);
                }
                if(!CODE.matcher(code).matches()) continue;
                String name=companyNames.getOrDefault(code,embedded);
                // "株価だけ予算入り" is not a valuation grade. Never infer undervaluation.
                String grade=grade(raw,event.title());
                found.add(new Row(day,time,code,name,grade,event.title(),raw));
            }
        }
        return List.copyOf(found);
    }

    private static String grade(String line,String title) {
        if(line.contains("超割安"))return "超割安";
        if(line.contains("かなり割安"))return "かなり割安";
        if(line.contains(" · 割安 ·") || line.endsWith(" · 割安"))return "割安";
        if(line.contains(" · 優先候補"))return "財務・優先候補（3段階外）";
        if(line.contains(" · 参考候補"))return "財務・参考候補（3段階外）";
        if(title.contains("株価急変"))return "株価急変（割安判定外）";
        if(title.contains("100株10万円以下") || title.contains("参考予算"))return "予算条件入り（割安判定外）";
        return "参考条件（3段階外）";
    }
}
