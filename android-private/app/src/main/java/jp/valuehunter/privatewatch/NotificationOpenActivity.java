package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;

/** A notification tap acknowledges the alert before opening the normal app screen. */
public final class NotificationOpenActivity extends Activity {
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            NotificationDismissal.record(this, getIntent().getData());
            startActivity(new Intent(this, MainActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP));
        } finally {
            finish();
        }
    }
}
