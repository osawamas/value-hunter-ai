package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Activity;
import android.app.NotificationManager;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.text.method.LinkMovementMethod;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.work.WorkManager;

import org.json.JSONArray;
import org.json.JSONException;

import java.io.IOException;

public final class MainActivity extends Activity {
    private SharedPreferences state;
    private TextView status;
    private TextView results;
    private TextView usResults;
    private TextView sgResults;
    private EditText key;
    private EditText usKey;
    private EditText sgKey;
    private CheckBox sgWatch;
    private Thread jpxCheckThread;
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
        filter.setText("東証の普通株 · 実績PER 15倍以下 · PBR 1倍以下\n10万円以内で100株買える候補を優先。次に1株（取扱いは証券会社による）");
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
        addJpxDailyCheck(content);

        var erase = new Button(this);
        erase.setText("この端末のAPIキー・監視履歴を消去");
        erase.setOnClickListener(view -> {
            // Stop every private scan before erasing its locally stored credentials.
            var work = WorkManager.getInstance(this);
            work.cancelUniqueWork("japan-watch");
            work.cancelUniqueWork("japan-check-now");
            work.cancelUniqueWork("us-watch");
            work.cancelUniqueWork("us-check-now");
            work.cancelUniqueWork("sg-check-now");
            ScanWorker.stopSingaporeWatch(this);
            state.edit().clear().commit();
            getSystemService(NotificationManager.class).cancelAll();
            key.setText("");
            if (usKey != null) usKey.setText("");
            if (sgKey != null) sgKey.setText("");
            if (sgWatch != null) sgWatch.setChecked(false);
            render();
        });
        content.addView(erase);

        var usTitle = new TextView(this);
        usTitle.setText("米国株 · IBM接続試験");
        usTitle.setTextSize(18);
        content.addView(usTitle);

        usKey = new EditText(this);
        usKey.setHint("自分のAlpha Vantage APIキー");
        usKey.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        usKey.setSaveEnabled(false);
        usKey.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        content.addView(usKey);

        var usRefresh = new Button(this);
        usRefresh.setText("米国株の設定を保存して確認");
        usRefresh.setOnClickListener(view -> {
            String entered = usKey.getText().toString().trim();
            String previous = state.getString("us_key", "");
            if (entered.isEmpty() && previous.isEmpty()) {
                usKey.setError("各自のAPIキーを入力して");
                return;
            }
            var editor = state.edit().putString("us_status", "米国株の確認を予約した");
            if (!entered.isEmpty() && !entered.equals(previous)) {
                editor.putString("us_key", entered).remove("us_date").remove("us_result")
                        .remove("us_qualified");
            }
            editor.apply();
            usKey.setText("");
            requestNotifications();
            ScanWorker.scheduleUs(this);
        });
        content.addView(usRefresh);

        usResults = new TextView(this);
        usResults.setTextIsSelectable(true);
        content.addView(usResults);

        var source = new TextView(this);
        source.setText(android.text.Html.fromHtml("<a href='" + UsScreen.FILING + "'>IBMのSEC開示</a>",
                android.text.Html.FROM_HTML_MODE_LEGACY));
        source.setMovementMethod(LinkMovementMethod.getInstance());
        content.addView(source);

        var sgTitle = new TextView(this);
        sgTitle.setText("シンガポール株 · S63接続試験");
        sgTitle.setTextSize(18);
        content.addView(sgTitle);

        sgKey = new EditText(this);
        sgKey.setHint("自分のDataCedar APIキー");
        sgKey.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        sgKey.setSaveEnabled(false);
        sgKey.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        content.addView(sgKey);

        sgWatch = new CheckBox(this);
        sgWatch.setText("S63を定期確認して、新しく条件に入ったら無音通知");
        sgWatch.setChecked(state.getBoolean("sg_watch", false));
        content.addView(sgWatch);

        var sgCheck = new Button(this);
        sgCheck.setText("S63の設定を保存して確認");
        sgCheck.setOnClickListener(view -> {
            String entered = sgKey.getText().toString().trim();
            String savedKey = state.getString("sg_key", "");
            String selected = entered.isEmpty() ? savedKey : entered;
            if (selected.isEmpty() || !selected.matches("[!-~]+")) {
                sgKey.setError("各自のAPIキーを確認して");
                return;
            }
            boolean watch = sgWatch.isChecked();
            var editor = state.edit().putString("sg_key", selected).putBoolean("sg_watch", watch)
                    .putString("sg_result", "接続確認を予約した");
            if (!selected.equals(savedKey)) editor.remove("sg_last_result");
            if (!selected.equals(savedKey) || watch != state.getBoolean("sg_watch", false)) {
                editor.remove("sg_qualified_date").remove("sg_qualified");
            }
            editor.apply();
            sgKey.setText("");
            if (watch) {
                ScanWorker.scheduleSingaporeWatch(this);
                requestNotifications();
            } else {
                ScanWorker.stopSingaporeWatch(this);
            }
            ScanWorker.checkSingapore(this);
        });
        content.addView(sgCheck);

        sgResults = new TextView(this);
        sgResults.setTextIsSelectable(true);
        content.addView(sgResults);

        var jpTitle = new TextView(this);
        jpTitle.setText("日本株の候補");
        jpTitle.setTextSize(18);
        content.addView(jpTitle);
        status = new TextView(this);
        content.addView(status);
        results = new TextView(this);
        results.setTextIsSelectable(true);
        content.addView(results);
    }

    private void addJpxDailyCheck(LinearLayout content) {
        var check = new Button(this);
        check.setText("東証日報で終値を確認");
        content.addView(check);
        var report = new TextView(this);
        report.setTextIsSelectable(true);
        report.setMovementMethod(LinkMovementMethod.getInstance());
        content.addView(report);

        if (Build.VERSION.SDK_INT < 35) {
            check.setEnabled(false);
            report.setText("東証日報のPDF読み取りはAndroid 15以降に対応");
            return;
        }

        report.setText("接続試験 · 1301 極洋 / 7203 トヨタ自動車");
        check.setOnClickListener(view -> {
            check.setEnabled(false);
            report.setText("JPXの株式相場表を取得中");
            jpxCheckThread = new Thread(() -> {
                CharSequence message;
                try {
                    var daily = JpxDailyCheck.check(getCacheDir());
                    message = android.text.Html.fromHtml(daily.html(), android.text.Html.FROM_HTML_MODE_LEGACY);
                } catch (IOException error) {
                    message = "東証日報の確認に失敗\n" + error.getMessage();
                } catch (RuntimeException error) {
                    message = "東証日報のPDFを読み取れなかった";
                }
                CharSequence result = message;
                runOnUiThread(() -> {
                    if (isDestroyed() || isFinishing()) return;
                    jpxCheckThread = null;
                    report.setText(result);
                    check.setEnabled(true);
                });
            }, "jpx-daily-check");
            jpxCheckThread.start();
        });
    }

    @Override protected void onDestroy() {
        if (jpxCheckThread != null) jpxCheckThread.interrupt();
        super.onDestroy();
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
        sgResults.setText(state.getString("sg_result", "DataCedarのキーでS63の終値を確認"));
        String usResult = state.getString("us_result", "");
        usResults.setText(state.getString("us_status", "Alpha VantageのキーでIBMの取得を開始")
                + (usResult.isEmpty() ? "" : "\n" + usResult));
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
