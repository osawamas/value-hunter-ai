package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import java.io.IOException;

/** Offline opening sequence. Its brand art cannot disappear if a source asset is absent. */
public final class SplashActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean entered;
    private final Runnable enter = () -> {
        if (entered || isFinishing()) return;
        entered = true;
        startActivity(new Intent(this, MainActivity.class));
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
        finish();
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xff050e1b);
        getWindow().setNavigationBarColor(0xff050e1b);
        setContentView(new SplashArt());
        handler.postDelayed(enter, 2350);
    }

    @Override protected void onDestroy() {
        handler.removeCallbacks(enter);
        super.onDestroy();
    }

    private final class SplashArt extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final long born = SystemClock.uptimeMillis();
        private final Bitmap art;

        SplashArt() {
            super(SplashActivity.this);
            Bitmap loaded = null;
            try (var stream = getAssets().open("brand_splash.webp")) {
                loaded = BitmapFactory.decodeStream(stream);
            } catch (IOException ignored) {
                // The canonical image was not shipped in older CI builds.
                // Always show the complete native branded composition instead.
            }
            art = loaded;
        }

        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            int w = getWidth(), h = getHeight();
            if (w <= 0 || h <= 0) return;
            paint.setShader(new LinearGradient(0, 0, w, h,
                    0xff030b17, 0xff10283d, Shader.TileMode.CLAMP));
            canvas.drawRect(0, 0, w, h, paint);
            paint.setShader(null);
            if (art != null && !art.isRecycled()) {
                float scale = Math.min(w / (float) art.getWidth(), h / (float) art.getHeight());
                float left = (w - art.getWidth() * scale) / 2f;
                float top = (h - art.getHeight() * scale) / 2f;
                canvas.save();
                canvas.translate(left, top);
                canvas.scale(scale, scale);
                canvas.drawBitmap(art, 0, 0, paint);
                canvas.restore();
            } else {
                drawNativeBrand(canvas, w, h);
            }
            float seconds = (SystemClock.uptimeMillis() - born) / 1000f;
            float x = w * (.1f + .8f * (seconds / 2.35f));
            paint.setShader(new RadialGradient(x, h * .76f, Math.max(20f, w * .16f),
                    new int[]{0x22ffcea4, 0x0acf8658, Color.TRANSPARENT},
                    new float[]{0f, .32f, 1f}, Shader.TileMode.CLAMP));
            canvas.drawCircle(x, h * .76f, Math.max(20f, w * .16f), paint);
            paint.setShader(null);
            if (seconds < 2.35f) postInvalidateDelayed(33);
        }

        private void drawNativeBrand(Canvas canvas, int w, int h) {
            float centerX = w / 2f;
            float centerY = h * .44f;
            float emblemSize = Math.min(w * .38f, h * .23f);
            View logo = BrandEmblem.create(SplashActivity.this);
            int px = Math.round(emblemSize);
            logo.measure(MeasureSpec.makeMeasureSpec(px, MeasureSpec.EXACTLY),
                    MeasureSpec.makeMeasureSpec(px, MeasureSpec.EXACTLY));
            logo.layout(0, 0, px, px);
            canvas.save();
            canvas.translate(centerX - emblemSize / 2f, centerY - emblemSize * .75f);
            logo.draw(canvas);
            canvas.restore();

            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(Typeface.create("serif", Typeface.BOLD));
            paint.setTextSize(Math.min(w * .09f, 39f));
            paint.setColor(0xffffe3c5);
            canvas.drawText("他力本願寺", centerX, centerY + emblemSize * .56f, paint);
            paint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
            paint.setTextSize(Math.min(w * .051f, 22f));
            paint.setColor(0xffdca67f);
            canvas.drawText("VALUE HUNTER AI", centerX, centerY + emblemSize * .88f, paint);

            paint.setColor(0xffcb8c62);
            paint.setStrokeWidth(Math.max(1.5f, w * .003f));
            float dividerY = h * .74f;
            canvas.drawLine(w * .11f, dividerY, w * .89f, dividerY, paint);
            paint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
            paint.setTextSize(Math.min(w * .033f, 14f));
            paint.setColor(0xfff2d7c4);
            canvas.drawText("JPX  /  US STOCK MONITOR", centerX, h * .81f, paint);
        }
    }
}
