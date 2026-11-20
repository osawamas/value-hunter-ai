package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.Html;
import android.text.method.LinkMovementMethod;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

import java.io.IOException;

public final class MainActivity extends Activity {
    private static final String PAUSED = "public_jpx_watch_paused";
    private static final int PAGE = 0xfff3f5f0;
    private static final int SURFACE = 0xffffffff;
    private static final int FOREST = 0xff173b33;
    private static final int INK = 0xff182e28;
    private static final int MUTED = 0xff53665e;
    private static final int LIGHT_TEXT = 0xffd5e6d8;
    private static final int ACCENT = 0xffdbf183;
    private static final int OUTLINE = 0xffdbe3da;

    private SharedPreferences state;
    private Switch monitorSwitch;
    private TextView monitorStatus;
    private TextView notificationStatus;
    private TextView lastCheck;
    private TextView detail;
    private TextView usDailyStatus;
    private Button notificationButton;
    private Button checkNow;
    private Thread detailThread;

    private final SharedPreferences.OnSharedPreferenceChangeListener onChange = (prefs, name) -> render();

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(FOREST);
        getWindow().setNavigationBarColor(PAGE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        state = ScanWorker.prefs(this);
        ScanWorker.cancelLegacyApiWork(this);
        UsDailyWorker.schedule(this);

        var scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(PAGE);
        var content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(22), dp(20), dp(24));
        scroll.addView(content);
        setContentView(scroll);

        var hero = section(content, FOREST, false);
        var brand = label(hero, "VALUE HUNTER AI", 11, LIGHT_TEXT, true, 0);
        brand.setLetterSpacing(0.13f);
        label(hero, "株式モニター", 30, SURFACE, true, 7);
        monitorStatus = label(hero, "", 15, ACCENT, true, 10);
        label(hero, "新しく条件に入った銘柄を無音で通知", 13, LIGHT_TEXT, false, 5);

        var japan = section(content, SURFACE, true);
        label(japan, "日本株  ·  東証日報", 19, INK, true, 0);
        label(japan, "普通株の終値を一括取得 · 通期決算を順次自動取得", 13, MUTED, false, 5);
        label(japan, "PER・PBRから優先候補と参考候補を判定\n10万円以内で100株を優先", 13, MUTED, false, 7);

        monitorSwitch = new Switch(this);
        monitorSwitch.setText("自動監視");
        monitorSwitch.setTextSize(15);
        monitorSwitch.setTextColor(INK);
        monitorSwitch.setMinHeight(dp(48));
        monitorSwitch.setShowText(false);
        monitorSwitch.setThumbTintList(new ColorStateList(
                new int[][] {new int[] {android.R.attr.state_checked}, new int[] {}},
                new int[] {FOREST, MUTED}));
        monitorSwitch.setTrackTintList(new ColorStateList(
                new int[][] {new int[] {android.R.attr.state_checked}, new int[] {}},
                new int[] {ACCENT, OUTLINE}));
        monitorSwitch.setChecked(!state.getBoolean(PAUSED, false));
        place(japan, monitorSwitch, 5);
        monitorSwitch.setOnCheckedChangeListener((view, checked) -> {
            state.edit().putBoolean(PAUSED, !checked).apply();
            JpxWatchWorker.setEnabled(this, checked);
            if (checked) JpxWatchWorker.checkNow(this);
            render();
        });

        checkNow = button(japan, "今すぐ更新", ACCENT, 3);
        checkNow.setOnClickListener(view -> {
            if (JpxWatchWorker.checkNow(this)) {
                lastCheck.setText("通信可能になり次第、東証日報を確認");
            }
        });

        var unitedStates = section(content, SURFACE, true);
        label(unitedStates, "米国株  ·  NYSE / Nasdaq", 17, INK, true, 0);
        usDailyStatus = label(unitedStates, "", 13, MUTED, false, 4);

        var singapore = section(content, SURFACE, true);
        label(singapore, "シンガポール株  ·  SGX", 17, INK, true, 0);
        label(singapore, "終値の自動監視は準備中", 13, MUTED, false, 4);

        var notifications = section(content, SURFACE, true);
        label(notifications, "無音通知", 19, INK, true, 0);
        notificationStatus = label(notifications, "", 13, MUTED, false, 5);
        notificationButton = button(notifications, "", PAGE, 10);
        notificationButton.setOnClickListener(view -> {
            if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED
                    && !state.getBoolean("public_notification_permission_requested", false)) {
                state.edit().putBoolean("public_notification_permission_requested", true).apply();
                requestPermissions(new String[] {Manifest.permission.POST_NOTIFICATIONS}, 1);
            } else {
                openAlertSettings();
            }
        });

        var result = section(content, SURFACE, true);
        label(result, "最新の確認", 19, INK, true, 0);
        lastCheck = label(result, "", 14, MUTED, false, 5);
        var showDetail = button(result, "終値と判定の詳細", PAGE, 10);
        detail = label(result, "", 14, INK, false, 8);
        detail.setTextIsSelectable(true);
        detail.setMovementMethod(LinkMovementMethod.getInstance());
        detail.setVisibility(View.GONE);
        showDetail.setOnClickListener(view -> checkDetails(showDetail));

        render();
    }

    @Override protected void onStart() {
        super.onStart();
        state.registerOnSharedPreferenceChangeListener(onChange);
        if (monitorSwitch.isChecked() || JpxWatchWorker.enabled(this)) {
            JpxWatchWorker.setEnabled(this, monitorSwitch.isChecked());
        }
    }

    @Override protected void onResume() {
        super.onResume();
        render();
    }

    @Override protected void onStop() {
        state.unregisterOnSharedPreferenceChangeListener(onChange);
        super.onStop();
    }

    @Override protected void onDestroy() {
        if (detailThread != null) detailThread.interrupt();
        super.onDestroy();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 1 && ScanWorker.alertsEnabled(this)) JpxWatchWorker.checkNow(this);
        render();
    }

    private void render() {
        usDailyStatus.setText(UsDailyWorker.displayStatus(state));
        boolean active = monitorSwitch.isChecked();
        monitorStatus.setText(active ? "●  東証日報の自動監視中"
                + (Build.VERSION.SDK_INT < 35 ? "（互換モード）" : "") : "○  日本株の自動監視を停止中");
        checkNow.setEnabled(active);
        boolean alerts = ScanWorker.alertsEnabled(this);
        notificationStatus.setText(alerts ? "通知は有効" : "通知の許可が必要");
        notificationButton.setText(alerts ? "通知設定を開く" : "通知を有効にする");
        String report = JpxWatchWorker.displayStatus(state);
        lastCheck.setText(!report.isEmpty() ? report : active ? "初回の東証日報を確認待ち" : "自動監視をオンにすると確認を開始");
    }

    private void checkDetails(Button action) {
        if (detailThread != null) return;
        action.setEnabled(false);
        detail.setVisibility(View.VISIBLE);
        detail.setText("東証日報を確認中");
        detailThread = new Thread(() -> {
            CharSequence message;
            try {
                var daily = JpxDailyCheck.check(this);
                var rights = JpxShareRights.refresh(this);
                var history = JpxHistoryReference.load(this);
                var finance = JpxAutomaticFinance.cached(this, daily.latest());
                message = Html.fromHtml(daily.html(rights.rights(), history, finance) + "<br><br>" + rights.status(),
                        Html.FROM_HTML_MODE_LEGACY);
            } catch (IOException error) {
                message = "東証日報の確認に失敗\n" + error.getMessage();
            } catch (RuntimeException error) {
                message = "東証日報のPDFを読み取れなかった";
            }
            CharSequence result = message;
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                detailThread = null;
                detail.setText(result);
                action.setEnabled(true);
            });
        }, "jpx-daily-detail");
        detailThread.start();
    }

    private void openAlertSettings() {
        try {
            startActivity(ScanWorker.alertSettings(this));
        } catch (ActivityNotFoundException error) {
            startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.fromParts("package", getPackageName(), null)));
        }
    }

    private LinearLayout section(LinearLayout parent, int color, boolean border) {
        var group = new LinearLayout(this);
        group.setOrientation(LinearLayout.VERTICAL);
        group.setPadding(dp(17), dp(15), dp(17), dp(15));
        group.setBackground(shape(color, 17, border));
        place(parent, group, border ? 11 : 0);
        return group;
    }

    private TextView label(LinearLayout parent, String value, int size, int color, boolean bold, int margin) {
        var view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        place(parent, view, margin);
        return view;
    }

    private Button button(LinearLayout parent, String value, int color, int margin) {
        var view = new Button(this);
        view.setText(value);
        view.setTextSize(14);
        view.setAllCaps(false);
        view.setTextColor(INK);
        view.setMinHeight(dp(48));
        view.setMinimumHeight(dp(48));
        view.setPadding(dp(12), dp(5), dp(12), dp(5));
        view.setBackgroundTintList(null);
        view.setBackground(new RippleDrawable(ColorStateList.valueOf(0x22173b33),
                shape(color, 11, false), null));
        place(parent, view, margin);
        return view;
    }

    private GradientDrawable shape(int color, int radius, boolean border) {
        var shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        if (border) shape.setStroke(dp(1), OUTLINE);
        return shape;
    }

    private void place(LinearLayout parent, View element, int margin) {
        var params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.topMargin = dp(margin);
        parent.addView(element, params);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
