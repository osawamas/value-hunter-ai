package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Activity;
import android.app.NotificationManager;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONException;

public final class MainActivity extends Activity {
    private SharedPreferences state;
    private TextView status;
    private TextView results;
    private EditText key;
    private final SharedPreferences.OnSharedPreferenceChangeListener onChange =
            (prefs, name) -> render();

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        state = ScanWorker.prefs(this);
        var content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        int gutter = (int) (20 * getResources().getDisplayMetrics().density);
        content.setPadding(gutter, gutter, gutter, gutter);
        var scroll = new ScrollView(this);
        scroll.addView(content);
        setContentView(scroll);

        TextView title = new TextView(this);
        title.setTextSize(26);
        title.setText("VALUE HUNTER AI");
        content.addView(title);
        var filter = new TextView(this);
        filter.setText("東証の普通株 · 100株10万円以内 · 実績PER 15倍以下 · PBR 1倍以下");
        content.addView(filter);

        key = new EditText(this);
        key.setHint("自分のJ-Quants APIキー");
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        key.setSaveEnabled(false);
        if (Build.VERSION.SDK_INT >= 26) key.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        content.addView(key);

        var delayed = new CheckBox(this);
        delayed.setText("無料プラン（株価は約12週間遅れ）");
        delayed.setChecked(state.getBoolean("delayed", true));
        content.addView(delayed);

        var save = new Button(this);
        save.setText("接続を保存して監視を開始");
        save.setOnClickListener(view -> {
            String entered = key.getText().toString().trim();
            String savedKey = state.getString("key", "");
            if (entered.isEmpty() && savedKey.isEmpty()) {
                key.setError("各自のAPIキーを入力して");
                return;
            }
            boolean different = !entered.isEmpty() && !entered.equals(savedKey);
            var editor = state.edit().putString("key", entered.isEmpty() ? savedKey : entered)
                    .putBoolean("delayed", delayed.isChecked());
            if (different || delayed.isChecked() != state.getBoolean("delayed", true)) {
                editor.remove("latest_date").remove("rows").remove("qualified");
            }
            editor.putString("status", "株価の確認を予約した").apply();
            key.setText("");
            ScanWorker.schedule(this);
            requestNotifications();
            ScanWorker.checkNow(this);
        });
        content.addView(save);

        var refresh = new Button(this);
        refresh.setText("今すぐ確認");
        refresh.setOnClickListener(view -> {
            if (state.getString("key", "").isEmpty()) {
                key.setError("先にAPIキーを保存して");
                return;
            }
            requestNotifications();
            ScanWorker.checkNow(this);
        });
        content.addView(refresh);

        var test = new Button(this);
        test.setText("無音通知を試す");
        test.setOnClickListener(view -> {
            if (!getSystemService(NotificationManager.class).areNotificationsEnabled()) {
                requestNotifications();
                return;
            }
            ScanWorker.testNotification(this);
        });
        content.addView(test);

        status = new TextView(this);
        content.addView(status);
        results = new TextView(this);
        results.setTextIsSelectable(true);
        content.addView(results);
    }

    @Override protected void onStart() {
        super.onStart();
        state.registerOnSharedPreferenceChangeListener(onChange);
        render();
    }

    @Override protected void onStop() {
        state.unregisterOnSharedPreferenceChangeListener(onChange);
        super.onStop();
    }

    private void requestNotifications() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        render();
    }

    private void render() {
        String date = state.getString("latest_date", "");
        boolean enabled = getSystemService(NotificationManager.class).areNotificationsEnabled();
        String dataLabel = state.getBoolean("delayed", true) ? "（遅延データ）" : "";
        status.setText(state.getString("status", "APIキーを設定して監視を始める")
                + (date.isEmpty() ? "" : "\n一覧の株価基準日 " + date + dataLabel)
                + (enabled ? "" : "\n無音通知を受け取るには通知を許可して"));
        try {
            var lines = new JSONArray(state.getString("rows", "[]"));
            StringBuilder text = new StringBuilder();
            for (int i = 0; i < lines.length(); i++) {
                if (i > 0) text.append("\n\n");
                text.append(lines.getString(i));
            }
            results.setText(text);
        } catch (JSONException error) {
            results.setText("候補一覧を読み込めなかった");
        }
    }
}
