package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.BitmapFactory;
import android.widget.ImageView;
import java.io.IOException;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Complete offline brand header: never silently render an empty image placeholder. */
final class BrandHeader {
    private BrandHeader() {}

    static View create(Activity activity) {
        // The approved header is a 941x246 image recovered from build 23.
        // It must be USED, not merely placed in assets/ after the APK was signed.
        // With adjustViewBounds, every tablet keeps its original 941:246 ratio.
        try (var stream = activity.getAssets().open("brand_header.webp")) {
            var original = BitmapFactory.decodeStream(stream);
            if (original != null) {
                FrameLayout frame = new FrameLayout(activity);
                ImageView image = new ImageView(activity);
                image.setImageBitmap(original);
                image.setScaleType(ImageView.ScaleType.FIT_XY);
                image.setAdjustViewBounds(true);
                image.setContentDescription("他力本願寺 VALUE HUNTER AI");
                frame.addView(image, new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT,
                        FrameLayout.LayoutParams.WRAP_CONTENT));
                View menuHit = new View(activity);
                menuHit.setContentDescription("他力本願寺のメニュー");
                menuHit.setClickable(true);
                menuHit.setFocusable(true);
                FrameLayout.LayoutParams hitParams = new FrameLayout.LayoutParams(
                        dp(activity, 74), dp(activity, 92), Gravity.TOP | Gravity.END);
                frame.addView(menuHit, hitParams);
                menuHit.setOnClickListener(v -> showBrandMenu(activity));
                return frame;
            }
        } catch (IOException ignored) {
            // Native offline header below is only the emergency fallback.
        }
        FrameLayout root = new FrameLayout(activity);
        root.setBackground(new CopperWaveDrawable());
        root.setMinimumHeight(dp(activity, 152));

        LinearLayout row = new LinearLayout(activity);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(activity, 18), dp(activity, 14), dp(activity, 14), dp(activity, 18));
        FrameLayout.LayoutParams rp = new FrameLayout.LayoutParams(-1, dp(activity, 152));
        root.addView(row, rp);

        View emblem = BrandEmblem.create(activity);
        row.addView(emblem, new LinearLayout.LayoutParams(dp(activity, 86), dp(activity, 86)));
        LinearLayout titles = new LinearLayout(activity);
        titles.setOrientation(LinearLayout.VERTICAL);
        titles.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(0, -2, 1f);
        tp.leftMargin = dp(activity, 13);
        row.addView(titles, tp);

        TextView name = text(activity, "他力本願寺", 26, 0xffffe4cf, true);
        titles.addView(name);
        TextView brand = text(activity, "VALUE HUNTER AI", 15, 0xffdfac87, true);
        brand.setLetterSpacing(.065f);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, -2);
        bp.topMargin = dp(activity, 5);
        titles.addView(brand, bp);

        TextView menu = text(activity, "⋮", 27, 0xffffdfc4, true);
        menu.setGravity(Gravity.CENTER);
        menu.setContentDescription("他力本願寺のメニュー");
        menu.setClickable(true);
        menu.setFocusable(true);
        GradientDrawable background = new GradientDrawable();
        background.setColor(0x553e5366);
        background.setCornerRadius(dp(activity, 16));
        menu.setBackground(background);
        row.addView(menu, new LinearLayout.LayoutParams(dp(activity, 40), dp(activity, 48)));
        menu.setOnClickListener(v -> new AlertDialog.Builder(activity)
                .setTitle("他力本願寺")
                .setItems(new String[]{"ホーム", "デバッグ診断", "閉じる"}, (dialog, which) -> {
                    if (which == 0 && !(activity instanceof MainActivity)) {
                        Intent intent = new Intent(activity, MainActivity.class);
                        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        activity.startActivity(intent);
                        activity.finish();
                    } else if (which == 1 && !(activity instanceof DebugDiagnosticsActivity)) {
                        activity.startActivity(new Intent(activity, DebugDiagnosticsActivity.class));
                    }
                }).show());
        return root;
    }

    private static TextView text(Activity a, String value, int sp, int color, boolean bold) {
        TextView result = new TextView(a);
        result.setText(value);
        result.setTextSize(sp);
        result.setTextColor(color);
        result.setSingleLine(true);
        result.setIncludeFontPadding(false);
        if (bold) result.setTypeface(Typeface.create("serif", Typeface.BOLD));
        return result;
    }

    private static void showBrandMenu(Activity activity) {
        new AlertDialog.Builder(activity).setTitle("他力本願寺")
                .setItems(new String[]{"ホーム", "デバッグ診断", "閉じる"}, (dialog, which) -> {
                    if (which == 0 && !(activity instanceof MainActivity)) {
                        Intent intent = new Intent(activity, MainActivity.class);
                        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
                        activity.startActivity(intent);
                        activity.finish();
                    } else if (which == 1 && !(activity instanceof DebugDiagnosticsActivity)) {
                        activity.startActivity(new Intent(activity, DebugDiagnosticsActivity.class));
                    }
                }).show();
    }

    private static int dp(Activity a, int n) {
        return Math.round(n * a.getResources().getDisplayMetrics().density);
    }
}
