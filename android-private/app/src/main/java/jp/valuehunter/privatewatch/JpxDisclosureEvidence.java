package jp.valuehunter.privatewatch;

import java.time.LocalDate;
import java.util.*;
import org.json.JSONArray;
import org.json.JSONException;

/** Dated, issuer-matched exchange disclosure titles. Headlines are not executed transactions. */
final class JpxDisclosureEvidence {
    record Event(LocalDate day, String title, String source, String kind) {}
    private static String kind(String title) {
        if (title.contains("訂正")) return "";
        if (title.contains("債務超過に関するお知らせ") || title.contains("民事再生手続開始の申立")
                || title.contains("会社更生手続開始の申立")
                || title.contains("監理銘柄（確認中）への指定")) return "distress";
        if (title.contains("取消") || title.contains("中止")
                || title.contains("終了") || title.contains("取得状況")) return "";
        if (title.contains("下方修正") || title.contains("業績予想の下方") || title.contains("行政処分")
                || title.contains("不正会計") || title.contains("継続企業の前提")) return "risk";
        if ((title.contains("自己株式") || title.contains("自己株")) && title.contains("取得")
                && (title.contains("決定") || title.contains("取得に係る事項"))) return "buyback";
        if (title.contains("大型受注") || title.contains("受注契約の締結")) return "order";
        if (title.contains("特許取得") || title.contains("特許登録")) return "patent";
        return "";
    }
    static boolean relevant(String title) { return !kind(title).isEmpty(); }
    private static boolean source(String code, String url) {
        return code.matches("[0-9][0-9A-Z]{3}") && url.matches("https://www2\\.jpx\\.co\\.jp/disc/" + code + "0/[0-9]+\\.pdf");
    }
    static List<Event> extract(String code, LocalDate through, JpxIssuerArchive.Page page) {
        var events = new ArrayList<Event>();
        for (var item : page.disclosures()) {
            if (item.pdfLink() == null || item.day().isAfter(through) || item.day().isBefore(through.minusDays(90))) continue;
            String url = item.pdfLink().toString(), kind = kind(item.title());
            if (!kind.isEmpty() && source(code, url)) events.add(new Event(item.day(), item.title(), url, kind));
        }
        return events.stream().distinct().sorted(Comparator.comparing(Event::day).reversed()).limit(100)
                .collect(java.util.stream.Collectors.toUnmodifiableList());
    }
    static JSONArray encode(List<Event> events) {
        var rows = new JSONArray();
        for (var e : events) rows.put(new JSONArray().put(e.day().toString()).put(e.title()).put(e.source()));
        return rows;
    }
    static List<Event> decode(String code, JSONArray rows, LocalDate through) {
        var result = new ArrayList<Event>();
        if (rows != null) for (int i=0; i<Math.min(100,rows.length()); i++) {
            try {
                var row = rows.getJSONArray(i);
                var day = LocalDate.parse(row.getString(0));
                String title = row.getString(1), url = row.getString(2), kind = kind(title);
                if (!kind.isEmpty() && source(code,url) && !day.isAfter(through) && !day.isBefore(through.minusDays(90)))
                    result.add(new Event(day,title,url,kind));
            } catch (JSONException | java.time.DateTimeException invalid) { /* Skip damaged evidence. */ }
        }
        return List.copyOf(result);
    }
    static ValueAlertMeter.Score adjust(ValueAlertMeter.Score score, List<Event> events, LocalDate session) {
        if (score == null || score.ceiling() == 0) return score;
        var kinds = new HashSet<String>();
        for (var e : events) if (e.day().isBefore(session) && !e.day().isBefore(session.minusDays(30))) kinds.add(e.kind());
        if (kinds.contains("distress")) {
            return new ValueAlertMeter.Score(Math.max(0, score.points() - 10), 0, score.confirmed());
        }
        // One contribution per category; title-only positives cannot lift the existing evidence ceiling.
        int delta = kinds.contains("risk") ? -10 : Math.min(6, (kinds.contains("buyback") ? 3 : 0)
                + (kinds.contains("order") ? 2 : 0) + (kinds.contains("patent") ? 1 : 0));
        return new ValueAlertMeter.Score(Math.max(0,Math.min(100,score.points()+delta)),score.ceiling(),score.confirmed());
    }
}
