package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;
import org.json.JSONObject;
import org.json.JSONArray;
import org.json.JSONException;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.Map;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Comparator;

/** Offline view over the SAME completed, matched SEC valuation ledger that drives alerts.
 * Never generates a candidate from incomplete/mismatched filings or stale price hashes. */
final class CurrentCandidates {
    record Row(String code,String name,String market,String status,String grade,int score,
               int quantity,String closeUsd,String purchaseYen,String per,String pbr) {}
    record Snapshot(LocalDate date,String source,List<Row> rows,int priority,int reference) {}

    private CurrentCandidates() {}

    static Snapshot load(Context context) throws IOException, JSONException {
        File dir=context.getNoBackupFilesDir();
        var closeFile=new AtomicFile(new File(dir,"us-daily-closes.json"));
        byte[] raw=UsDailyWorker.readQuote(closeFile);
        var quote=new JSONObject(new String(raw,StandardCharsets.UTF_8));
        var state=new JSONObject(new String(new AtomicFile(new File(dir,
                "us-sec-financials.json")).readFully(),StandardCharsets.UTF_8));
        var ledger=state.optJSONObject("ledger");
        if(ledger==null)throw new IOException("SEC財務の最終判定待ち（取得済み情報は保持中）");
        String closeHash=UsReferenceAlerts.sha256(raw);
        String day=quote.getString("trading_date_et");
        if(!closeHash.equals(state.optString("hash"))
                || !day.equals(ledger.optString("trading_date_et"))
                || !quote.getString("source").equals(ledger.optString("close_provider"))
                || !closeHash.equals(ledger.optString("close_sha256"))) {
            throw new IOException("終値と財務の基準日・保存内容が一致しないため候補を保留");
        }
        var evidence=state.optJSONObject("valuation_evidence");
        if(evidence==null || !Double.isFinite(evidence.optDouble("fx_rate",Double.NaN))
                || evidence.optDouble("fx_rate")<=0) throw new IOException("取引日換算レートを確認中");
        return parse(quote,state,UsCompanyNames.read(context),
                ValueAlertMeter.Thresholds.read(ScanWorker.prefs(context)
                        .getString(ValueAlertPreview.SETTINGS,"")));
    }

    static Snapshot parse(JSONObject quote,JSONObject state,Map<String,String> names,
                          ValueAlertMeter.Thresholds thresholds) throws JSONException {
        JSONObject ledger=state.getJSONObject("ledger");
        JSONObject screen=ledger.getJSONObject("reference_screen");
        String day=quote.getString("trading_date_et");
        if(!day.equals(ledger.getString("trading_date_et"))
                || !day.equals(screen.getString("fx_date"))
                || !quote.getString("source").equals(screen.getString("provider"))) {
            throw new JSONException("Mismatched price/finance session");
        }
        var prices=UsDeviceFinancials.prices(quote.getJSONArray("closes"));
        double fx=state.getJSONObject("valuation_evidence").getDouble("fx_rate");
        if(!Double.isFinite(fx)||fx<=0)throw new JSONException("Invalid FX rate");
        var finance=new HashMap<String,JSONObject>();
        JSONArray results=state.getJSONArray("results");
        for(int i=0;i<results.length();i++){
            JSONObject item=results.getJSONObject(i);
            finance.put(item.getString("symbol"),item);
        }
        JSONArray observations=screen.getJSONArray("observations");
        JSONObject scores=screen.optJSONObject("meter_rows");
        var candidates=new ArrayList<Row>();
        int priority=0,reference=0;
        for(int i=0;i<observations.length();i++){
            JSONObject row=observations.getJSONObject(i);
            String status=row.getString("status");
            if(!status.equals("priority")&&!status.equals("reference"))continue;
            String code=row.getString("symbol");
            JSONObject facts=finance.get(code);
            BigDecimal close=prices.get(code);
            if(facts==null || close==null || facts.getInt("cik")!=row.getInt("cik")
                    || !facts.getString("exchange").equals(row.getString("exchange")))continue;
            BigDecimal shares=new BigDecimal(facts.getString("shares"));
            BigDecimal profit=new BigDecimal(facts.getString("profit"));
            BigDecimal equity=new BigDecimal(facts.getString("equity"));
            if(shares.signum()<=0||profit.signum()<=0||equity.signum()<=0)continue;
            BigDecimal cap=close.multiply(shares);
            int quantity=row.getInt("quantity");
            String grade="3段階未判定";
            int points=-1;
            if(scores!=null){
                JSONArray meter=scores.optJSONArray(UsReferenceAlerts.meterKey(
                        row.getString("exchange"),row.getInt("cik"),code));
                if(meter!=null && meter.length()>=4 && meter.optInt(3,0)==quantity){
                    points=meter.getInt(0);
                    int ceiling=meter.getInt(1),confirmed=meter.getInt(2);
                    int level=new ValueAlertMeter.Score(points,ceiling,confirmed).level(thresholds);
                    if(level>0)grade=ValueAlertMeter.LABELS.get(level);
                }
            }
            String yen=close.multiply(BigDecimal.valueOf(fx)).multiply(BigDecimal.valueOf(quantity))
                    .setScale(0,RoundingMode.HALF_UP).toPlainString();
            String per=cap.divide(profit,2,RoundingMode.HALF_UP).toPlainString();
            String pbr=cap.divide(equity,2,RoundingMode.HALF_UP).toPlainString();
            candidates.add(new Row(code,names.getOrDefault(code,""),row.getString("exchange"),status,grade,
                    points,quantity,close.stripTrailingZeros().toPlainString(),yen,per,pbr));
            if(status.equals("priority"))priority++;else reference++;
        }
        candidates.sort(Comparator.comparing((Row row)->!row.status().equals("priority"))
                .thenComparing(row->row.quantity()!=100)
                .thenComparing(Row::code));
        return new Snapshot(LocalDate.parse(day),screen.getString("provider"),List.copyOf(candidates),
                priority,reference);
    }
}
