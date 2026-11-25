package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import java.io.IOException;

/** Uses the actual user-approved full-resolution artwork and overlays ONLY animated light. */
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
    @Override protected void onDestroy() {handler.removeCallbacks(enter);super.onDestroy();}
    private final class SplashArt extends View {
        private final Paint bitmapPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final long born = SystemClock.uptimeMillis();
        private final Bitmap art;
        SplashArt() {
            super(SplashActivity.this);
            Bitmap loaded = null;
            try (var stream = getAssets().open("brand_splash.webp")) {
                loaded = BitmapFactory.decodeStream(stream);
            } catch (IOException ignored) {}
            art = loaded;
        }
        private void flare(Canvas c, float x, float y, float radius, float strength) {
            int center = Color.argb(Math.min(255,Math.round(220*strength)),255,235,193);
            int halo = Color.argb(Math.min(255,Math.round(72*strength)),248,141,73);
            glow.setShader(new RadialGradient(x,y,radius,
                    new int[]{center,halo,Color.TRANSPARENT},new float[]{0f,.2f,1f},Shader.TileMode.CLAMP));
            c.drawCircle(x,y,radius,glow);
            glow.setShader(null);
            glow.setColor(Color.argb(Math.min(255,Math.round(110*strength)),255,215,166));
            glow.setStrokeWidth(Math.max(1f,radius*.008f));
            c.drawLine(x-radius*.77f,y,x+radius*.77f,y,glow);
            c.drawLine(x,y-radius*.35f,x,y+radius*.35f,glow);
        }
        @Override protected void onDraw(Canvas c) {
            super.onDraw(c);
            c.drawColor(0xff030a15);
            if (art == null || art.isRecycled()) return;
            // FIT_CENTER preserves original proportions and the complete composition.
            float scale = Math.min(getWidth()/(float)art.getWidth(),getHeight()/(float)art.getHeight());
            float left=(getWidth()-art.getWidth()*scale)/2f;
            float top=(getHeight()-art.getHeight()*scale)/2f;
            c.save();c.translate(left,top);c.scale(scale,scale);
            c.drawBitmap(art,0,0,bitmapPaint);
            float sec=(SystemClock.uptimeMillis()-born)/1000f;
            float pulse=(float)(.68+.2*Math.sin(sec*3.1));
            // Overlay small highlights at the emblem rim and existing copper divider.
            float angle=(float)(sec*.8);
            flare(c,462+215*(float)Math.cos(angle),500+215*(float)Math.sin(angle),82,pulse);
            flare(c,329,675,60,(float)(.35+.1*Math.sin(sec*2.5)));
            float t=(sec*.26f)%1f;
            flare(c,165+610*t,930,76,.50f);
            c.restore();
            if(sec<2.5f)postInvalidateDelayed(33);
        }
    }
}
