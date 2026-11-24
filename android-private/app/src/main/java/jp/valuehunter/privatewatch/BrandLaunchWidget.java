package jp.valuehunter.privatewatch;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Rect;
import java.io.IOException;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.os.Build;
import android.view.View;
import android.widget.RemoteViews;

/** Launcher 2x1 home-screen widget. Tap to start app; no periodic processing. */
public final class BrandLaunchWidget extends AppWidgetProvider {
    @Override public void onUpdate(Context context,AppWidgetManager manager,int[] ids) {
        for(int id:ids) update(context,manager,id);
    }
    @Override public void onAppWidgetOptionsChanged(Context context,AppWidgetManager manager,int id,
                                                       android.os.Bundle options) {
        update(context,manager,id);
    }
    private static void update(Context context,AppWidgetManager manager,int id) {
        RemoteViews remote=new RemoteViews(context.getPackageName(),R.layout.brand_widget);
        remote.setImageViewBitmap(R.id.brand_widget_image,draw(context));
        Intent open=new Intent(context,SplashActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags=PendingIntent.FLAG_UPDATE_CURRENT;
        if(Build.VERSION.SDK_INT>=23)flags|=PendingIntent.FLAG_IMMUTABLE;
        remote.setOnClickPendingIntent(R.id.brand_widget_image,
                PendingIntent.getActivity(context,id,open,flags));
        manager.updateAppWidget(id,remote);
    }
    private static Bitmap draw(Context context) {
        // The exact user-approved 2x1 artwork, not a text-and-logo imitation.
        try (var stream = context.getAssets().open("brand_widget.webp")) {
            Bitmap bitmap = BitmapFactory.decodeStream(stream);
            if (bitmap != null) {
                int w = 720, h = 300;
                Bitmap result = Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(result);
                Paint filter = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
                float targetRatio = w / (float) h;
                int cropWidth = Math.min(bitmap.getWidth(),Math.round(bitmap.getHeight()*targetRatio));
                int cropHeight = Math.min(bitmap.getHeight(),Math.round(bitmap.getWidth()/targetRatio));
                int x = (bitmap.getWidth()-cropWidth)/2;
                int y = (bitmap.getHeight()-cropHeight)/2;
                canvas.drawBitmap(bitmap,new Rect(x,y,x+cropWidth,y+cropHeight),
                        new Rect(0,0,w,h),filter);
                bitmap.recycle();
                return result;
            }
        } catch (IOException ignored) {}
        int w=720,h=300;
        Bitmap out=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
        Canvas c=new Canvas(out);
        Paint p=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
        RectF bounds=new RectF(8,8,w-8,h-8);
        c.save();
        Path clip=new Path();clip.addRoundRect(bounds,46,46,Path.Direction.CW);c.clipPath(clip);
        p.setShader(new LinearGradient(0,0,w,h,0xff091b30,0xff020916,Shader.TileMode.CLAMP));
        c.drawRect(bounds,p);p.setShader(null);
        for(int i=0;i<8;i++){
            Path ribbon=new Path();
            float y=h*.85f+i*6;
            ribbon.moveTo(0,y);ribbon.cubicTo(w*.35f,y-16,w*.55f,y+50,w,y-110);
            p.setColor(i%2==0?0xaa805036:0x66795649);
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.6f);
            c.drawPath(ribbon,p);
        }
        p.setStyle(Paint.Style.STROKE);p.setColor(0xffdc9868);p.setStrokeWidth(5f);
        c.drawRoundRect(new RectF(11,11,w-11,h-11),43,43,p);
        p.setColor(0xffffd2ac);p.setStrokeWidth(1.6f);
        c.drawRoundRect(new RectF(15,15,w-15,h-15),39,39,p);
        p.setStyle(Paint.Style.FILL);
        View image=BrandEmblem.create(context);
        int side=230;
        image.measure(View.MeasureSpec.makeMeasureSpec(side,View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(side,View.MeasureSpec.EXACTLY));
        image.layout(0,0,side,side);
        c.save();c.translate(38,35);image.draw(c);c.restore();
        p.setColor(0xffd99b6c);p.setStrokeWidth(2);c.drawRect(292,52,294,247,p);
        p.setTypeface(Typeface.create("serif",Typeface.BOLD));
        p.setColor(0xffffdfc1);p.setTextSize(63);
        c.drawText("他力本願寺",318,135,p);
        p.setTypeface(Typeface.create("serif",Typeface.NORMAL));p.setTextSize(33);
        p.setColor(0xffe6af89);c.drawText("VALUE HUNTER AI",319,196,p);
        p.setShader(new LinearGradient(310,218,705,218,
                new int[]{0x007f3e24,0xffffc58c,0x00ffb874},null,Shader.TileMode.CLAMP));
        c.drawRect(310,218,695,223,p);p.setShader(null);
        c.restore();
        return out;
    }
}
