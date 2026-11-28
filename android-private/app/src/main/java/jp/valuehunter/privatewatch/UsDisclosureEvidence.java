package jp.valuehunter.privatewatch;
import org.json.*;
import java.time.LocalDate;
import java.util.*;
/** SEC 8-K item codes are event metadata, not an assertion that a contract is profitable. */
final class UsDisclosureEvidence {
    static String url(int cik) { return String.format(Locale.ROOT,"https://data.sec.gov/submissions/CIK%010d.json",cik); }
    static JSONArray read(JSONObject payload, int cik, LocalDate day) throws JSONException {
        var result = new JSONArray();
        if (payload.optInt("cik",-1) != cik) return result;
        var recent = payload.getJSONObject("filings").getJSONObject("recent");
        var forms = recent.getJSONArray("form");
        var dates = recent.getJSONArray("filingDate");
        var items = recent.getJSONArray("items");
        var ids = recent.getJSONArray("accessionNumber");
        if (forms.length()!=dates.length() || forms.length()!=items.length() || forms.length()!=ids.length()) return result;
        var seen = new HashSet<String>();
        for(int i=0;i<forms.length();i++) {
            if(!"8-K".equals(forms.optString(i))) continue;
            LocalDate filed;
            try { filed=LocalDate.parse(dates.optString(i)); } catch(java.time.DateTimeException e) { continue; }
            String id=ids.optString(i);
            if(!filed.isBefore(day) || filed.isBefore(day.minusDays(60)) || !id.matches("[0-9]{10}-[0-9]{2}-[0-9]{6}") || !seen.add(id)) continue;
            var codes=Arrays.asList(items.optString(i).replace(" ","").split(","));
            var risks=new ArrayList<String>();
            for(String code:List.of("1.03","2.04","2.06","4.02")) if(codes.contains(code)) risks.add(code);
            if(!risks.isEmpty()) result.put(new JSONObject().put("day",filed.toString()).put("cik",cik)
                .put("accession",id).put("items",new JSONArray(risks))
                .put("source","https://www.sec.gov/Archives/edgar/data/"+cik+"/"+id.replace("-","")+"/"+id+"-index.htm"));
        }
        return result;
    }
    static ValueAlertMeter.Score adjust(ValueAlertMeter.Score score, JSONObject row, LocalDate day) {
        var events=row.optJSONArray("disclosure_events");
        if(events==null) return score;
        boolean risk = false;
        for(int i=0;i<events.length();i++) {
            var event=events.optJSONObject(i);
            if(event==null || event.optInt("cik",-1)!=row.optInt("cik",-2)) continue;
            try {
                var filed=LocalDate.parse(event.getString("day"));
                if(!filed.isBefore(day)||filed.isBefore(day.minusDays(30))) continue;
                var items=event.getJSONArray("items");
                for (int j = 0; j < items.length(); j++) {
                    String item = items.optString(j);
                    if ("1.03".equals(item)) {
                        return new ValueAlertMeter.Score(Math.max(0, score.points() - 10), 0, score.confirmed());
                    }
                    if (List.of("2.04", "2.06", "4.02").contains(item)) risk = true;
                }
            } catch(JSONException | java.time.DateTimeException invalid) { }
        }
        return risk ? new ValueAlertMeter.Score(Math.max(0, score.points() - 10),
                Math.min(2, score.ceiling()), score.confirmed()) : score;
    }
}
