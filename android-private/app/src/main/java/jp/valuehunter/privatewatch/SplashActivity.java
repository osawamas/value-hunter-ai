package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;

/** Android 9-compatible two-second startup animation. */
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
        setContentView(new Art());
        handler.postDelayed(enter, 2300);
    }
    @Override protected void onDestroy() { handler.removeCallbacks(enter); super.onDestroy(); }
    private final class Art extends View {
        private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final long born = SystemClock.uptimeMillis();
        Art() { super(SplashActivity.this); setLayerType(View.LAYER_TYPE_SOFTWARE, null); }
        void flare(Canvas c,float x,float y,float r,float alpha) {
            p.reset();p.setAntiAlias(true);
            p.setShader(new RadialGradient(x,y,r,new int[]{
                Color.argb((int)(230*alpha),255,238,198),
                Color.argb((int)(140*alpha),234,135,62),0x00de7839},
                new float[]{0f,.16f,1f},Shader.TileMode.CLAMP));
            c.drawCircle(x,y,r,p);p.setShader(null);
            p.setColor(Color.argb((int)(135*alpha),255,199,137));p.setStrokeWidth(1.2f);
            c.drawLine(x-r*.7f,y,x+r*.7f,y,p);
            c.drawLine(x,y-r*.4f,x,y+r*.4f,p);
        }
        @Override protected void onDraw(Canvas c) {
            float w=getWidth(),h=getHeight();
            if(w==0||h==0)return;
            float s=w/400f, cx=w*.5f, cy=h*.37f, rad=Math.min(w*.27f,h*.18f);
            float sec=(SystemClock.uptimeMillis()-born)/1000f;
            p.reset();p.setAntiAlias(true);
            p.setShader(new LinearGradient(0,0,w,h,0xff071528,0xff030a16,Shader.TileMode.CLAMP));
            c.drawRect(0,0,w,h,p);p.setShader(null);
            for(int j=0;j<14;j++){
                Path wave=new Path();float y=h*(.83f+j*.009f);
                wave.moveTo(0,y);
                wave.cubicTo(w*.25f,y-h*.04f,w*.53f,y+h*.05f,w,y-h*.12f);
                p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(Math.max(.7f,s*.6f));
                p.setColor(j%3==0?0x998c5437:0x665a4337);c.drawPath(wave,p);
            }
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2.8f*s);p.setColor(0xffad714d);
            c.drawRoundRect(10*s,10*s,w-10*s,h-10*s,23*s,23*s,p);
            p.setStrokeWidth(.8f*s);p.setColor(0xffffc99d);
            c.drawRoundRect(13*s,13*s,w-13*s,h-13*s,20*s,20*s,p);
            p.setStyle(Paint.Style.FILL);
            p.setShader(new RadialGradient(cx,cy,rad*1.5f,
                    new int[]{0x6cbe693a,0x00000000},null,Shader.TileMode.CLAMP));
            c.drawCircle(cx,cy,rad*1.5f,p);p.setShader(null);
            p.setColor(0xff20100a);c.drawCircle(cx,cy,rad*1.04f,p);
            p.setColor(0xffc88957);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3*s);
            c.drawCircle(cx,cy,rad,p);p.setStyle(Paint.Style.FILL);
            View emblem=BrandEmblem.create(SplashActivity.this);
            int side=(int)(rad*1.86f);
            emblem.measure(MeasureSpec.makeMeasureSpec(side,MeasureSpec.EXACTLY),
                    MeasureSpec.makeMeasureSpec(side,MeasureSpec.EXACTLY));
            emblem.layout(0,0,side,side);
            c.save();c.translate(cx-side/2f,cy-side/2f);emblem.draw(c);c.restore();
            float twinkle=(float)(.7+.3*Math.sin(sec*3));
            flare(c,cx+rad*(float)Math.cos(sec*.65f),cy+rad*(float)Math.sin(sec*.65f),
                    rad*.4f,twinkle);
            flare(c,cx-rad*.82f,cy+rad*.78f,rad*.26f,.67f);
            p.setTextAlign(Paint.Align.CENTER);p.setTypeface(Typeface.create("serif",Typeface.BOLD));
            p.setColor(0xffffddba);p.setTextSize(45*s);c.drawText("他力本願寺",cx,h*.60f,p);
            p.setTypeface(Typeface.create("serif",Typeface.NORMAL));p.setTextSize(19*s);
            p.setColor(0xffe3a779);c.drawText("V A L U E  H U N T E R  A I",cx,h*.68f,p);
            p.setColor(0xffb47a50);p.setStrokeWidth(s);
            c.drawLine(w*.16f,h*.63f,w*.84f,h*.63f,p);
            flare(c,w*(.16f+.68f*((sec*.28f)%1f)),h*.63f,w*.15f,.6f);
            if(sec<3.2f)postInvalidateDelayed(33);
        }
    }
}
