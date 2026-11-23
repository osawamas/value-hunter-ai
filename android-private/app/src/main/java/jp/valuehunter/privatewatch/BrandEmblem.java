package jp.valuehunter.privatewatch;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.Base64;
import android.view.View;

/** Original provided bronze/black emblem, downsampled for the compact app header. */
final class BrandEmblem {
    private static final String IMAGE = "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";
    private static Bitmap bitmap;
    static View create(Context context) {
        if (bitmap == null) {
            byte[] bytes = Base64.decode(IMAGE, Base64.DEFAULT);
            bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
        }
        return new View(context) {
            final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
            @Override protected void onDraw(Canvas canvas) {
                if (bitmap == null) return;
                float r = Math.min(getWidth(), getHeight()) / 2f;
                Path circle = new Path();
                circle.addCircle(getWidth()/2f, getHeight()/2f, r, Path.Direction.CW);
                canvas.save();
                canvas.clipPath(circle);
                canvas.drawBitmap(bitmap, null, new RectF(0, 0, getWidth(), getHeight()), paint);
                canvas.restore();
            }
        };
    }
}
