package jp.valuehunter.privatewatch;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;

/** Quiet navy/copper decorative banner shared by home and diagnostic screens. */
final class CopperWaveDrawable extends Drawable {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int alpha = 255;
    @Override public void draw(Canvas c) {
        Rect b=getBounds();
        if(b.width()<=0||b.height()<=0)return;
        float w=b.width(),h=b.height();
        c.save();c.translate(b.left,b.top);
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(new LinearGradient(0,0,w,h,
                new int[]{0xff05111d,0xff0b2339,0xff061321},null,Shader.TileMode.CLAMP));
        c.drawRect(0,0,w,h,paint);paint.setShader(null);
        // Brushed copper ribbon from the original splash visual language.
        for(int i=0;i<9;i++) {
            Path wave=new Path();
            float y=h*(.79f+i*.017f);
            wave.moveTo(-w*.05f,y);
            wave.cubicTo(w*.35f,y-h*.09f,w*.70f,y+h*.13f,w*1.06f,y-h*.23f);
            paint.setColor(i%3==0?0xffbf7950:0x885c544f);
            paint.setStrokeWidth(Math.max(.7f,w*.0015f));
            paint.setStyle(Paint.Style.STROKE);c.drawPath(wave,paint);
        }
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0xffce8a5c);c.drawRect(0,h-3,w,h,paint);
        c.restore();
    }
    @Override public void setAlpha(int alpha) {this.alpha=alpha;invalidateSelf();}
    @Override public void setColorFilter(ColorFilter f) { paint.setColorFilter(f);invalidateSelf();}
    @Override public int getOpacity(){return PixelFormat.OPAQUE;}
}
