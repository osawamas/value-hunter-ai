package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.text.TextWatcher;
import android.text.Editable;
import org.json.JSONObject;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;

/** On-device, no-login diagnostic screens for the private APK. */
public final class DebugDiagnosticsActivity extends Activity {
    private static final int NAVY = 0xff091b2e, COPPER = 0xffb76e42;
    private static final int INK = 0xff142336, CREAM = 0xfffffbf6, OUTLINE = 0xffdac8ba;
    private static final int RED = 0xffad3434, AMBER = 0xffb16b24, GREEN = 0xff277052;
    private static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("MM/dd HH:mm:ss", Locale.JAPAN)
            .withZone(ZoneId.of("Asia/Tokyo"));
    private LinearLayout body;
    private int page;
    private String filter = "ERROR";
    private String query = "";

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(NAVY);
        getWindow().setNavigationBarColor(CREAM);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        showPage(0);
    }

    private void showPage(int next) {
        page = next;
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(CREAM);
        LinearLayout root = column();
        scroll.addView(root);
        setContentView(scroll);
        header(root);
        body = column();
        body.setPadding(dp(16), dp(18), dp(16), dp(32));
        root.addView(body);
        if (page == 0) overview();
        else if (page == 1) listing();
        else if (page == 2) detailLog();
        else sharedReport();
    }

    private void header(LinearLayout root) {
        LinearLayout band = column();
        band.setPadding(dp(16), dp(18), dp(16), dp(16));
        band.setBackground(new CopperWaveDrawable());
        root.addView(band);
        LinearLayout brand = row();
        band.addView(brand);
        View emblem = BrandEmblem.create(this);
        brand.addView(emblem, new LinearLayout.LayoutParams(dp(62), dp(62)));
        LinearLayout names = column();
        LinearLayout.LayoutParams ns = new LinearLayout.LayoutParams(0, -2, 1f);
        ns.leftMargin = dp(13);
        brand.addView(names, ns);
        TextView title = text("他力本願寺", 28, 0xffffe7cc, true);
        title.setTypeface(Typeface.create("serif", Typeface.BOLD));
        names.addView(title);
        TextView subtitle = text("VALUE HUNTER AI", 12, 0xffd79c73, false);
        subtitle.setLetterSpacing(0.16f);
        names.addView(subtitle);
        Button close = new Button(this);
        close.setText("×");
        close.setTextColor(0xffffe7cc);
        close.setTextSize(22);
        close.setAllCaps(false);
        close.setBackgroundColor(Color.TRANSPARENT);
        close.setOnClickListener(v -> finish());
        brand.addView(close, new LinearLayout.LayoutParams(dp(48), dp(50)));
        View rule = new View(this);
        rule.setBackgroundColor(COPPER);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(-1, dp(2));
        rp.topMargin = dp(12);
        band.addView(rule, rp);
        TextView section = text(page == 1 ? "エラー一覧" : page == 2 ? "詳細ログ" : page == 3 ? "共有レポート" : "デバッグ診断", 21, 0xffffe7cc, true);
        section.setTypeface(Typeface.create("serif", Typeface.BOLD));
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(-1, -2);
        tp.topMargin = dp(12);
        band.addView(section, tp);
        LinearLayout tabs = row();
        tabs.setPadding(dp(5), dp(8), dp(5), dp(8));
        root.addView(tabs);
        String[] labels = {"概要", "エラー一覧", "詳細ログ", "共有"};
        for (int i = 0; i < labels.length; i++) {
            int index = i;
            Button b = new Button(this);
            b.setText(labels[i]);
            b.setAllCaps(false);
            b.setTextSize(12);
            b.setMinimumHeight(dp(48));
            b.setTextColor(i == page ? Color.WHITE : INK);
            b.setBackground(shape(i == page ? NAVY : CREAM, 10, true));
            b.setOnClickListener(v -> showPage(index));
            LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(0, dp(48), 1);
            bp.setMargins(dp(2), 0, dp(2), 0);
            tabs.addView(b, bp);
        }
    }

    private void overview() {
        List<JSONObject> all = DiagnosticLog.entries(this);
        int errors = 0, retry = 0, success = 0;
        for (JSONObject event : all) {
            switch (event.optString("level")) {
                case "ERROR" -> errors++;
                case "RETRY" -> retry++;
                default -> success++;
            }
        }
        LinearLayout stats = row();
        body.addView(stats);
        stat(stats, "エラー", errors, RED);
        stat(stats, "再試行", retry, AMBER);
        stat(stats, "通常記録", success, GREEN);
        heading(body, "最新の異常");
        int shown = 0;
        for (JSONObject event : all) {
            if ("INFO".equals(event.optString("level"))) continue;
            eventCard(body, event);
            if (++shown == 5) break;
        }
        if (shown == 0) body.addView(text("直近7日間のエラーは記録されていない", 15, INK, false));
        action(body, "エラー一覧を見る", () -> { filter = "ERROR"; showPage(1); }, true);
        action(body, "診断ログをすべてコピー", this::copyReport, true);
        action(body, "共有レポート", () -> showPage(3), false);
    }

    private void listing() {
        heading(body, "エラー・再試行の一覧");
        LinearLayout choices = row();body.addView(choices);
        for (String kind : new String[]{"ERROR", "RETRY", "ALL"}) {
            Button b = new Button(this);
            b.setText(kind.equals("ERROR") ? "エラー" : kind.equals("RETRY") ? "再試行" : "すべて");
            b.setAllCaps(false);b.setTextSize(13);
            b.setTextColor(filter.equals(kind) ? Color.WHITE : INK);
            b.setBackground(shape(filter.equals(kind) ? NAVY : CREAM, 14, true));
            b.setOnClickListener(v -> {filter=kind;showPage(1);});
            choices.addView(b, new LinearLayout.LayoutParams(0, dp(48), 1));
        }
        EditText search = new EditText(this);
        search.setSingleLine(true);search.setTextSize(14);
        search.setHint("処理名・エラー名で検索");
        search.setText(query);
        body.addView(search);
        LinearLayout results = column();body.addView(results);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                query=s.toString();fillResults(results);
            }
            @Override public void afterTextChanged(Editable e){}
        });
        fillResults(results);
        action(body, "診断ログをコピー", this::copyReport, true);
    }

    private void fillResults(LinearLayout container) {
        container.removeAllViews();
        int count=0;
        for (JSONObject event: DiagnosticLog.entries(this)) {
            String level=event.optString("level");
            if (!"ALL".equals(filter) && !filter.equals(level)) continue;
            if (!query.isEmpty() && !(event.optString("area")+" "+event.optString("operation")
                    +" "+event.optString("exception")).toLowerCase(Locale.ROOT)
                    .contains(query.toLowerCase(Locale.ROOT))) continue;
            eventCard(container,event);
            count++;
        }
        if(count==0)container.addView(text("該当する記録はない",15,INK,false));
    }

    private void detailLog() {
        heading(body,"詳細ログ");
        TextView log=text(DiagnosticLog.detailedReport(this),12,INK,false);
        log.setTextIsSelectable(true);
        log.setTypeface(Typeface.MONOSPACE);
        log.setPadding(dp(14),dp(12),dp(14),dp(12));
        log.setBackground(shape(Color.WHITE,12,true));
        body.addView(log);
        action(body,"ログ全文をコピー",this::copyReport,true);
    }

    private void sharedReport() {
        heading(body,"共有レポート");
        body.addView(text("端末・OS・アプリ版・通信状態・エラーの種類と発生位置をまとめる。",14,INK,false));
        TextView report=text(DiagnosticLog.detailedReport(this),12,INK,false);
        report.setTypeface(Typeface.MONOSPACE); report.setTextIsSelectable(true);
        report.setPadding(dp(12),dp(12),dp(12),dp(12));
        report.setBackground(shape(Color.WHITE,12,true));
        body.addView(report);
        action(body,"診断レポートをコピー",this::copyReport,true);
        action(body,"共有シートを開く",() -> {
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_TEXT,DiagnosticLog.detailedReport(this));
            startActivity(Intent.createChooser(send,"診断レポートを共有"));
        },false);
        body.addView(text("共有前にログ内容を確認して。認証情報を含む診断データは送信しないで。",12,INK,false));
    }

    private void eventCard(LinearLayout root,JSONObject event) {
        String level=event.optString("level");
        int status = "ERROR".equals(level) ? RED : "RETRY".equals(level) ? AMBER : GREEN;
        LinearLayout card=column();
        card.setPadding(dp(13),dp(13),dp(13),dp(13));
        card.setBackground(shape(Color.WHITE,12,true));
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,-2);
        cp.topMargin=dp(10);root.addView(card,cp);
        TextView title=text(event.optString("area")+"  ·  "+("ERROR".equals(level)?"エラー":"RETRY".equals(level)?"再試行":"記録"),16,INK,true);
        card.addView(title);
        card.addView(text(event.optString("operation"),14,INK,false));
        String when=CLOCK.format(Instant.ofEpochMilli(event.optLong("time")));
        card.addView(text(when+"  "+event.optString("exception")+"  "+event.optString("location"),11,0xff576576,false));
        card.setOnClickListener(v -> new AlertDialog.Builder(this)
                .setTitle(event.optString("area")+"  ·  詳細")
                .setMessage(event.optString("operation")+"\n"+event.optString("exception")
                        +"\n"+event.optString("location")+"\n\n"+event.optString("trace"))
                .setPositiveButton("このエラーをコピー",(d,w)-> copy(event.toString()))
                .setNegativeButton("閉じる",null).show());
        card.setContentDescription("診断記録 "+event.optString("area")+" "+event.optString("operation"));
    }

    private void stat(LinearLayout root,String name,int count,int color) {
        LinearLayout box=column();
        box.setGravity(Gravity.CENTER);
        box.setPadding(dp(4),dp(10),dp(4),dp(10));
        box.setBackground(shape(0xffffffff,11,true));
        LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(0,dp(96),1);
        bp.setMargins(dp(3),0,dp(3),0);
        root.addView(box,bp);
        box.addView(text(name,13,INK,true));
        TextView value=text(Integer.toString(count)+" 件",24,color,true);
        value.setGravity(Gravity.CENTER);
        box.addView(value);
    }
    private void copyReport(){copy(DiagnosticLog.detailedReport(this));}
    private void copy(String value){
        ClipboardManager cm=getSystemService(ClipboardManager.class);
        if(cm!=null)cm.setPrimaryClip(ClipData.newPlainText("他力本願寺 診断ログ",value));
        android.widget.Toast.makeText(this,"診断ログをコピーした",android.widget.Toast.LENGTH_SHORT).show();
    }
    private void heading(LinearLayout root,String title){
        TextView label=text(title,19,INK,true);
        label.setTypeface(Typeface.create("serif",Typeface.BOLD));
        label.setPadding(0,dp(22),0,dp(9));
        root.addView(label);
    }
    private void action(LinearLayout root,String title,Runnable run,boolean primary){
        Button button=new Button(this);button.setText(title);button.setAllCaps(false);
        button.setTextSize(15);button.setMinimumHeight(dp(54));
        button.setTextColor(primary?Color.WHITE:INK);
        button.setBackground(shape(primary?NAVY:Color.WHITE,12,true));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(54));
        p.topMargin=dp(12);root.addView(button,p);
        button.setOnClickListener(v->run.run());
    }
    private TextView text(String value,int size,int color,boolean bold){
        TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);
        if(bold)v.setTypeface(size>=18?Typeface.create("serif",Typeface.BOLD):Typeface.DEFAULT,Typeface.BOLD);
        return v;
    }
    private LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
    private LinearLayout row(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.HORIZONTAL);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    private GradientDrawable shape(int color,int radius,boolean stroke){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));
        if(stroke)d.setStroke(dp(1),OUTLINE);
        return d;
    }
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
}
