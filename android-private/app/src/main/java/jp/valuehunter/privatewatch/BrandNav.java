package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;

/** Shared bottom navigation, matching the approved ivory/navy/copper layout. */
final class BrandNav {
    private BrandNav(){}
    static View create(Activity activity, String selected) {
        LinearLayout bar=new LinearLayout(activity);
        bar.setGravity(Gravity.CENTER);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setPadding(dp(activity,7),dp(activity,8),dp(activity,7),dp(activity,8));
        bar.setBackgroundColor(0xfffffbf6);
        String[] names={"ホーム","相場","通知","診断"};
        String[] marks={"⌂","▥","♧","◇"};
        for(int i=0;i<names.length;i++){
            final int index=i;
            Button button=new Button(activity);
            button.setText(marks[i]+"  "+names[i]);
            button.setAllCaps(false);
            button.setTextSize(13);
            button.setSingleLine(true);
            boolean active=names[i].equals(selected);
            button.setTextColor(active?0xff9a4c22:0xff435365);
            GradientDrawable bg=new GradientDrawable();
            bg.setColor(active?0xfff3d9c5:0xfffffbf6);
            bg.setCornerRadius(dp(activity,17));
            button.setBackgroundTintList(null);
            button.setBackground(bg);
            button.setOnClickListener(v->{
                if(index<3) {
                    Intent open=new Intent(activity,MainActivity.class);
                    open.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
                    open.putExtra("focus", index==1?"us":index==2?"notifications":"top");
                    activity.startActivity(open);
                    if(!(activity instanceof MainActivity))activity.finish();
                } else if(!(activity instanceof DebugDiagnosticsActivity)){
                    activity.startActivity(new Intent(activity,DebugDiagnosticsActivity.class));
                }
            });
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(activity,54),1f);
            lp.setMargins(dp(activity,2),0,dp(activity,2),0);
            bar.addView(button,lp);
        }
        return bar;
    }
    private static int dp(Activity activity,int value) {
        return Math.round(value*activity.getResources().getDisplayMetrics().density);
    }
}
