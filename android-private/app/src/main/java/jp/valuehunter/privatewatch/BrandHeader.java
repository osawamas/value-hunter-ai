package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.BitmapFactory;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import java.io.IOException;

/** The approved art-directed brand header, rather than a low-resolution redraw. */
final class BrandHeader {
    private BrandHeader() {}
    static View create(Activity activity) {
        FrameLayout root=new FrameLayout(activity);
        ImageView art=new ImageView(activity);
        art.setAdjustViewBounds(true);
        art.setScaleType(ImageView.ScaleType.FIT_XY);
        try (var input=activity.getAssets().open("brand_header.webp")) {
            art.setImageBitmap(BitmapFactory.decodeStream(input));
        } catch (IOException ignored) {
            // In development builds the external original image may be absent.
            art.setBackground(new CopperWaveDrawable());
            art.setMinimumHeight(dp(activity,110));
        }
        root.addView(art,new FrameLayout.LayoutParams(-1,-2));
        View menu=new View(activity);
        menu.setContentDescription("他力本願寺のメニュー");
        menu.setOnClickListener(v -> new AlertDialog.Builder(activity)
                .setTitle("他力本願寺")
                .setItems(new String[]{"ホーム","デバッグ診断","閉じる"},(dialog,which)->{
                    if(which==0 && !(activity instanceof MainActivity)){
                        Intent intent=new Intent(activity,MainActivity.class);
                        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        activity.startActivity(intent);
                        activity.finish();
                    } else if(which==1 && !(activity instanceof DebugDiagnosticsActivity)){
                        activity.startActivity(new Intent(activity,DebugDiagnosticsActivity.class));
                    }
                }).show());
        FrameLayout.LayoutParams hit=new FrameLayout.LayoutParams(dp(activity,72),dp(activity,100),Gravity.TOP|Gravity.END);
        root.addView(menu,hit);
        return root;
    }
    private static int dp(Activity a,int n) {
        return Math.round(n*a.getResources().getDisplayMetrics().density);
    }
}
