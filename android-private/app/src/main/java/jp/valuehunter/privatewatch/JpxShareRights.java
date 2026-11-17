package jp.valuehunter.privatewatch;

import android.content.Context;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.YearMonth;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

record JpxShareRights(Set<String> coveredCodes, Set<YearMonth> months, List<Notice> notices) {
    private static final String JPX_MONTHLY =
            "https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html";

    record Notice(String code, LocalDate exDay, String source) {
        String description() {
            return "権利落日 " + exDay + " · <a href='" + source + "'>JPX原本</a>";
        }
    }

    static JpxShareRights load(Context context) {
        try (var asset = context.getAssets().open("jpx-share-rights.json")) {
            return read(asset);
        } catch (IOException | JSONException | DateTimeException error) {
            return new JpxShareRights(Set.of(), Set.of(), List.of());
        }
    }

    private static JpxShareRights read(InputStream input) throws IOException, JSONException {
        var bytes = new ByteArrayOutputStream();
        byte[] buffer = new byte[8_192];
        for (int length; (length = input.read(buffer)) != -1;) bytes.write(buffer, 0, length);
        var payload = new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
        var codes = new HashSet<String>();
        var covered = payload.getJSONArray("coveredCodes");
        for (int index = 0; index < covered.length(); index++) {
            String code = covered.getString(index);
            if (!code.matches("[0-9][0-9A-Z]{3}")) throw new JSONException("Invalid JPX security code");
            codes.add(code);
        }
        var months = new HashSet<YearMonth>();
        var coverage = payload.getJSONObject("monthlySources");
        var keys = coverage.keys();
        while (keys.hasNext()) {
            String key = keys.next();
            officialSource(coverage.getString(key));
            months.add(YearMonth.parse(key));
        }
        var entries = payload.getJSONArray("notices");
        var notices = new ArrayList<Notice>();
        for (int index = 0; index < entries.length(); index++) {
            var entry = entries.getJSONObject(index);
            String code = entry.getString("code");
            if (!codes.contains(code)) throw new JSONException("JPX notice outside snapshot scope");
            notices.add(new Notice(code, LocalDate.parse(entry.getString("exDay")),
                    officialSource(entry.getString("source"))));
        }
        return new JpxShareRights(Set.copyOf(codes), Set.copyOf(months), List.copyOf(notices));
    }

    private static String officialSource(String url) throws JSONException {
        if (!url.matches("https://www\\.jpx\\.co\\.jp/[A-Za-z0-9./_-]+")) {
            throw new JSONException("Invalid JPX rights source");
        }
        return url;
    }

    Notice firstChange(String code, LocalDate fromExclusive, LocalDate through) {
        for (var notice : notices) {
            if (notice.code().equals(code) && notice.exDay().isAfter(fromExclusive)
                    && !notice.exDay().isAfter(through)) return notice;
        }
        return null;
    }

    String holdReason(String code, LocalDate fromExclusive, LocalDate through) {
        var notice = firstChange(code, fromExclusive, through);
        return notice == null ? coverageHold(code, fromExclusive, through) : notice.description();
    }

    private String coverageHold(String code, LocalDate fromExclusive, LocalDate through) {
        if (!through.isAfter(fromExclusive)) return "";
        if (!coveredCodes.contains(code)) return "対象銘柄の分割・併合資料なし";
        var missing = new ArrayList<YearMonth>();
        for (var month = YearMonth.from(fromExclusive.plusDays(1));
             !month.isAfter(YearMonth.from(through)); month = month.plusMonths(1)) {
            if (!months.contains(month)) missing.add(month);
        }
        if (missing.isEmpty()) return "";
        return "権利落月報の未確認月 " + missing.stream().map(YearMonth::toString)
                .collect(java.util.stream.Collectors.joining("、"))
                + " · <a href='" + JPX_MONTHLY + "'>JPX統計月報</a>";
    }
}
