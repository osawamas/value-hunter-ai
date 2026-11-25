package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.IOException;
import java.time.LocalDate;
import java.util.List;
import java.util.Locale;

/** Persistent, offline-readable notifications from today and previous three JST days. */
public final class RecentAlertsActivity extends Activity {
    private static final int NAVY=0xff091b2e, COPPER=0xffb97650,
            INK=0xff162a3d, CREAM=0xfffffbf6, MUTED=0xff526070;
    private int dp(int d) {return Math.round(d*getResources().getDisplayMetrics().density);}
    private TextView text(String value,int size,int color,boolean bold) {
        var view=new TextView(this);
        view.setText(value);view.setTextSize(size);view.setTextColor(color);
        if(bold)view.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        view.setTextIsSelectable(true);
        return view;
    }
    private GradientDrawable cardShape() {
        var bg=new GradientDrawable();
        bg.setColor(Color.WHITE);bg.setCornerRadius(dp(16));bg.setStroke(dp(1),0xffdcc6b4);
        return bg;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(NAVY);
        getWindow().setNavigationBarColor(CREAM);
        var shell=new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setBackgroundColor(CREAM);
        var scroll=new ScrollView(this);
        scroll.setFillViewport(true);
        shell.addView(scroll,new LinearLayout.LayoutParams(-1,0,1f));
        shell.addView(BrandNav.create(this,"通知"),new LinearLayout.LayoutParams(-1,-2));
        setContentView(shell);
        var body=new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(body);
        body.addView(BrandHeader.create(this),new LinearLayout.LayoutParams(-1,-2));
        var header=text("当日＋過去3日の通知銘柄",22,Color.WHITE,true);
        header.setTypeface(Typeface.create("serif",Typeface.BOLD));
        header.setBackground(new CopperWaveDrawable());
        header.setPadding(dp(18),dp(15),dp(18),dp(15));
        body.addView(header);
        var explanation=text("端末に実際に届いた通知から表示。取引日ではなく通知日の日本時間で分類。"
                +"「予算入り」「株価急変」は割安度3段階の判定ではない。",13,MUTED,false);
        explanation.setPadding(dp(19),dp(16),dp(19),dp(14));
        body.addView(explanation);
        LocalDate today=LocalDate.now(RecentAlerts.JAPAN);
        List<RecentAlerts.Row> rows;
        try {
            rows=RecentAlerts.rows(NotificationHistory.recent(NotificationHistory.file(this),
                    System.currentTimeMillis()),today,UsCompanyNames.read(this));
        } catch(IOException failed) {
            var warning=text("通知履歴を読み込めなかった。デバッグ診断からログを確認して。",15,INK,false);
            warning.setPadding(dp(20),dp(20),dp(20),dp(20));
            body.addView(warning);
            return;
        }
        int count=0;
        for(int back=0;back<RecentAlerts.DAYS;back++){
            LocalDate day=today.minusDays(back);
            String heading=(back==0?"今日":back==1?"昨日":back+"日前")
                    +"  ·  "+day.getMonthValue()+"月"+day.getDayOfMonth()+"日";
            var date=text(heading,18,INK,true);
            date.setPadding(dp(20),dp(16),dp(20),dp(7));
            body.addView(date);
            int daily=0;
            for(var row:rows){
                if(!row.postedDay().equals(day))continue;
                daily++;count++;
                var item=new LinearLayout(this);
                item.setOrientation(LinearLayout.VERTICAL);
                item.setPadding(dp(15),dp(12),dp(15),dp(12));
                item.setBackground(cardShape());
                var lp=new LinearLayout.LayoutParams(-1,-2);
                lp.setMargins(dp(16),dp(5),dp(16),dp(6));
                body.addView(item,lp);
                var title=text(row.code()+(row.company().isEmpty()?"":"  "+row.company()),16,INK,true);
                item.addView(title);
                var sub=text(row.grade()+"  ·  "+row.time()+" JST",13,COPPER,true);
                sub.setPadding(0,dp(5),0,dp(3));item.addView(sub);
                item.setOnClickListener(v->new AlertDialog.Builder(this)
                        .setTitle(row.code()+(row.company().isEmpty()?"":" · "+row.company()))
                        .setMessage(row.postedDay()+" "+row.time()+" JST\n"
                                +row.grade()+"\n\n"+row.title()+"\n"+row.detail())
                        .setPositiveButton("閉じる",null).show());
            }
            if(daily==0) {
                var none=text("この日に記録された通知銘柄はない",13,MUTED,false);
                none.setPadding(dp(22),dp(6),dp(15),dp(13));
                body.addView(none);
            }
        }
        var footer=text("合計 "+count+"件の通知銘柄記録。インストール前の別アプリに保存された"
                +"履歴は引き継げない。名称が取得できない銘柄はコードのみ表示。",12,MUTED,false);
        footer.setPadding(dp(20),dp(15),dp(20),dp(28));
        body.addView(footer);
    }
}
