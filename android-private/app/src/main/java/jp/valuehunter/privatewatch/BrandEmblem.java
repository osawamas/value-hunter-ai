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
    private static final String IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAFAAAABQAgMAAADzfxo+AAAADFBMVEXv6ea6c1lAJxkZEguNzevGAAAEuUlEQVR42l3Vb2jdVx3H8fc5Ob/bpK3mzN6WJTJbUEYHhUYYONroPRnpEFrMHUscTTuasQ7c6Gx9sgcy6a1UkDm2CNuYEPUKrdPeuP0qugf+2T1XE3XoMIMwnVaJMtua3KznQrNk93fy+/rgxtr6fXR48X34PZ+PYmN2PM/iCW6dfhGRc7daQUREZPIWrEt+4UJdcneTbZH2WJEdJ+XdmxfzScbVFw/U8//ZJvnXz0bHj8jcR2XuBu7N75X2eF2uq/oagAbU3OU3vAF6ilOb3AYWOPFxpyDqoTt9dQN3t/vujzgC9Ka3b+Dkn5QTIIpJXip0ULtTIQBch7ueVRXQ0JM3IkIEseqxygRoKK6OO4wHH3HrC0XQMPHPcyMRj/cMYXb3gIbKt0LRq0AwTUO6WYNG51utEQLCRcSWKhU0SWaCDmcigvcZNi2j6Y5EBkOUIMYuu2RgF5pdl9xm3B6IvTL4U8JaNxqb0n26N/uMj2tbu2akctCgqcw6/be5OhDCp3Zl6pqmi+++ke2+6+7X37kwlr0zcNuWN7etfU+p+MTQ6OWvX338vTfPHpYfvFS8fE1pnS2Jn18u3JlmDz2rrsyoL6ROm+jT5oFs2yloz286VS6+H6w2mCz/kvtGASZfW1Ut96GnbNfmY3rw14sP5zv/uPW22a/ML39Wf2yLtq0zh5ulr110oPbbPYdIo9G8j3puvmvWA8fmfzW8SDTa/hmZb+4sOsD8pPvCE+VrGGuXtt93aVcBIGltmu5HjMHve3B0IvQDqPVQmAS0CztGag+rzv0MctyTKg0cdrQ66O5zLvMYmqhHGx0T2ffg6NK2hi79ApJvegCURWpeYYCs9uNh7yCrDbLdIWik9moKVUBq0IQMzW7U2DARSMogniaGQWroYQDlUONl3npP+6UaEB0gQDnFYlTYPhHiJz2gWtTPnqf4d0N81HEllAAakJ14npJGOdone3sBZsysW0wTtDcwhZ2rQG5m1h8/HxEdhmj74tmZBbjnw715PRlVaJCp8Weur6xC9VAv34Zm1GE09perreUSNPbck2TQijqQlKWxvv849F28O5ZSTqGj9aw+kI08WU6enn3lufmXX5mJOm5xrDRl/ko5mSq+3tcqvVwMmrwidV9+rXT0cuNpd6ZaVASdmep0LAxcOR5D39TCQqKcDUrFnnPTj73o+vc3Pne0b/ncUv3thhaF9OzV1GYfmKK1nyLOK07//uDil59cJKJIvvMbd+8vtcaXG5U4grWUKnE2lUaOZuFgwj/2brUGt7P06T0ka2iavSmz1j1lsTPWTHB7RLPWE+Xd9RYOm9S9EbuAJlfECsqb+836cAqTKUD9q5m0j60sf3/99OIRaeed/z5ynWCVogWZPNTBhU9Y6gSLDbb04u/WQMPVbi9YBQqYnrgEBtr67aXoDDBgrKoMgQapHDzauc9DFP+S+06CVe8gOIOAVEdXAQNc1c+AFbxb+eH6WxtZ94F/5OcnCSDNO2RgA5noCT/ylml1vtq+kbRaVgrywvlk/Egn1LsAhAPb/vrIR/7w79/m+25O6vyFse2fr9+U08BJkfarIh/c0giqLiKSl/+vPOoi+X+rQ93YHZMlv/H+DywbKl4bleqZAAAAAElFTkSuQmCC";
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
                // The supplied source has pale square pixels beyond its round black rim.
                // Clip within the actual emblem so the widget/header never shows a white halo.
                float r = Math.min(getWidth(), getHeight()) * .445f;
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
