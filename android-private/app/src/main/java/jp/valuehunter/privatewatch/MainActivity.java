package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
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
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

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
    private TextView communicationStatus;
    private Switch networkSwitch;
    private Switch wifiSwitch;
    private AlertDialog communicationNotice;
    private TextView lastCheck;
    private TextView detail;
    private TextView usDailyStatus;
    private Button notificationButton;
    private Button testNotificationButton;
    private boolean notificationTestPending;
    private Button checkNow;
    private Button showDetail;
    private Thread detailThread;
    private boolean communicationPreferenceSaved = true;

    private final SharedPreferences.OnSharedPreferenceChangeListener onChange = (prefs, name) -> render();
    private final Runnable onRouteChange = this::render;

    private final Runnable sendTestNotification = () -> {
        notificationTestPending = false;
        if (!ScanWorker.testNotification(this) && ScanWorker.notificationsRequested(this)) {
            Toast.makeText(this, "テスト通知を出せなかった。端末の通知設定を確認", Toast.LENGTH_LONG).show();
        }
        render();
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(FOREST);
        getWindow().setNavigationBarColor(PAGE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        state = ScanWorker.prefs(this);
        ScanWorker.cancelLegacyApiWork(this);

        var scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(PAGE);
        var content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(22), dp(20), dp(24));
        int availableWidth = getResources().getConfiguration().screenWidthDp;
        int contentWidth = availableWidth > 620 ? dp(620) : ScrollView.LayoutParams.MATCH_PARENT;
        scroll.addView(content, new ScrollView.LayoutParams(contentWidth,
                ScrollView.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.CENTER_HORIZONTAL));
        setContentView(scroll);

        var hero = section(content, FOREST, false);
        var brand = label(hero, "VALUE HUNTER AI", 11, LIGHT_TEXT, true, 0);
        brand.setLetterSpacing(0.13f);
        label(hero, "株式モニター", 30, SURFACE, true, 7);
        monitorStatus = label(hero, "", 15, ACCENT, true, 10);
        label(hero, "新しく条件に入った銘柄を無音で通知", 13, LIGHT_TEXT, false, 5);

        var communication = section(content, SURFACE, true);
        networkSwitch = optionSwitch(communication, "相場データの通信", MarketNetwork.requested());
        wifiSwitch = optionSwitch(communication, "Wi-Fi接続時のみ更新", MarketNetwork.wifiOnly());
        communicationStatus = label(communication, "", 13, MUTED, false, 5);
        networkSwitch.setOnClickListener(view -> applyMarketNetworkPreference(networkSwitch.isChecked()));
        wifiSwitch.setOnClickListener(view -> {
            communicationPreferenceSaved = MarketNetwork.setWifiOnly(this, wifiSwitch.isChecked());
            // Replace saved jobs so their network constraint matches the selected mode.
            androidx.work.WorkManager.getInstance(this).cancelAllWork();
            scheduleMarketChecks();
            render();
        });
        button(communication, "通信量について", PAGE, 5).setOnClickListener(view -> showCommunicationNotice(false));

        var notifications = section(content, SURFACE, true);
        label(notifications, "通知", 19, INK, true, 0);
        var notificationSwitch = optionSwitch(notifications, "無音通知", ScanWorker.notificationsRequested(this));
        notificationSwitch.setOnCheckedChangeListener((view, checked) ->
                state.edit().putBoolean(ScanWorker.NOTIFICATIONS_ENABLED, checked).apply());
        var wakeScreen = optionSwitch(notifications, "通知時に画面を点灯",
                state.getBoolean(NotificationScreenWake.ENABLED, true));
        wakeScreen.setOnCheckedChangeListener((view, checked) ->
                state.edit().putBoolean(NotificationScreenWake.ENABLED, checked).apply());
        notificationStatus = label(notifications, "", 13, MUTED, false, 5);
        notificationButton = button(notifications, "", PAGE, 7);
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
        testNotificationButton = button(notifications, "", PAGE, 5);
        testNotificationButton.setOnClickListener(view -> {
            notificationTestPending = true;
            render();
            Toast.makeText(this, "画面を消すと点灯も確認できる", Toast.LENGTH_SHORT).show();
            testNotificationButton.postDelayed(sendTestNotification, 5000);
        });
        button(notifications, "通知履歴（" + NotificationHistory.DAYS + "日間）", PAGE, 5)
                .setOnClickListener(view -> showNotificationHistory());

        var japan = section(content, SURFACE, true);
        label(japan, "日本株  ·  東証日報", 19, INK, true, 0);
        label(japan, "普通株の終値を一括取得 · 通期決算を順次自動取得", 13, MUTED, false, 5);
        label(japan, "PER・PBRから優先候補と参考候補を判定\n10万円以内で100株を優先", 13, MUTED, false, 7);

        monitorSwitch = optionSwitch(japan, "自動監視", !state.getBoolean(PAUSED, false));
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

        var result = section(content, SURFACE, true);
        label(result, "最新の確認", 19, INK, true, 0);
        lastCheck = label(result, "", 14, MUTED, false, 5);
        showDetail = button(result, "終値と判定の詳細", PAGE, 10);
        detail = label(result, "", 14, INK, false, 8);
        detail.setTextIsSelectable(true);
        detail.setMovementMethod(LinkMovementMethod.getInstance());
        detail.setVisibility(View.GONE);
        showDetail.setOnClickListener(view -> checkDetails());

        render();
    }

    @Override protected void onStart() {
        super.onStart();
        state.registerOnSharedPreferenceChangeListener(onChange);
        MarketNetwork.addListener(onRouteChange);
        MarketUpdate.addListener(onRouteChange);
        if (MarketNetwork.noticeRequired(this)) showCommunicationNotice(true);
        scheduleMarketChecks();
    }

    private void applyMarketNetworkPreference(boolean allowed) {
        communicationPreferenceSaved = MarketNetwork.setAllowed(this, allowed);
        if (MarketNetwork.requested()) {
            scheduleMarketChecks();
        } else {
            androidx.work.WorkManager.getInstance(this).cancelAllWork();
            if (detailThread != null) {
                detailThread.interrupt();
                detail.setText("通信を停止した");
            }
        }
        render();
    }

    private void showCommunicationNotice(boolean firstLaunch) {
        if (communicationNotice != null && communicationNotice.isShowing()) return;
        var notice = new AlertDialog.Builder(this).setTitle("通信量について").setMessage(
                "通信量に上限がある回線や従量制のモバイル回線では、インストールや相場監視はおすすめしません。"
                        + "\n\nWi-Fiやデータ無制限の回線での利用をおすすめします。"
                        + "\n\n相場監視は株価や財務データを繰り返し取得します。通信設定はあとから変更できます。");
        if (firstLaunch) {
            notice.setCancelable(false)
                    .setNegativeButton("通信オフで使う", (dialog, which) -> applyMarketNetworkPreference(false))
                    .setPositiveButton("相場通信をオン", (dialog, which) -> applyMarketNetworkPreference(true));
        } else {
            notice.setPositiveButton("閉じる", null);
        }
        communicationNotice = notice.show();
    }

    private void scheduleMarketChecks() {
        if (!MarketNetwork.requested()) return;
        UsDailyWorker.schedule(this);
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
        MarketNetwork.removeListener(onRouteChange);
        MarketUpdate.removeListener(onRouteChange);
        super.onStop();
    }

    @Override protected void onDestroy() {
        if (detailThread != null) detailThread.interrupt();
        if (communicationNotice != null) communicationNotice.dismiss();
        testNotificationButton.removeCallbacks(sendTestNotification);
        super.onDestroy();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 1 && ScanWorker.alertsEnabled(this)) JpxWatchWorker.checkNow(this);
        render();
    }

    private void render() {
        var usStatus = new StringBuilder();
        appendUpdateStatus(usStatus, "終値", MarketUpdate.US_CLOSE.display(state));
        appendUpdateStatus(usStatus, "財務", MarketUpdate.US_FINANCE.display(state));
        usDailyStatus.setText(usStatus.append(UsDailyWorker.displayStatus(state)));
        boolean connected = MarketNetwork.allowed();
        boolean awaitingNotice = MarketNetwork.noticeRequired(this);
        networkSwitch.setChecked(MarketNetwork.requested());
        networkSwitch.setEnabled(!awaitingNotice);
        wifiSwitch.setChecked(MarketNetwork.wifiOnly());
        wifiSwitch.setEnabled(!awaitingNotice);
        boolean active = monitorSwitch.isChecked();
        String status = !MarketNetwork.requested() ? "通信オフ · 自動更新・手動更新を停止中"
                : MarketNetwork.waitingForWifi() ? "Wi-Fi接続待ち · 更新を一時停止中"
                : MarketNetwork.wifiOnly() ? "Wi-Fi接続中 · 相場データの取得を許可" : "相場データの取得を許可";
        communicationStatus.setText(communicationPreferenceSaved ? status : status + "\n設定を保存できなかった");
        monitorStatus.setText(MarketNetwork.waitingForWifi() ? "○  Wi-Fi接続待ち · 保存済みの結果を表示中"
                : !connected ? "○  通信オフ · 保存済みの結果を表示中" : active ? "●  東証日報の自動監視中"
                + (Build.VERSION.SDK_INT < 35 ? "（互換モード）" : "") : "○  日本株の自動監視を停止中");
        checkNow.setEnabled(connected && active);
        showDetail.setEnabled(connected && detailThread == null);
        boolean requested = ScanWorker.notificationsRequested(this);
        boolean permitted = ScanWorker.systemAllowsAlerts(this);
        if (!requested && notificationTestPending) {
            testNotificationButton.removeCallbacks(sendTestNotification);
            notificationTestPending = false;
        }
        notificationStatus.setText(!requested ? "通知と点灯は停止中"
                : permitted ? "通知は有効" : "端末側で通知を許可すると受け取れる");
        notificationButton.setText(permitted ? "端末の通知設定" : "端末で通知を許可する");
        testNotificationButton.setEnabled(requested && permitted && !notificationTestPending);
        testNotificationButton.setText(notificationTestPending ? "テスト通知を予約中" : "5秒後にテスト通知");
        String report = JpxWatchWorker.displayStatus(state);
        String update = active ? MarketUpdate.JPX.display(state) : "";
        if (!update.isEmpty()) report = update + (report.isEmpty() ? "" : "\n" + report);
        lastCheck.setText(!report.isEmpty() ? report : !connected ? "保存済みの確認結果はまだない"
                : active ? "初回の東証日報を確認待ち" : "自動監視をオンにすると確認を開始");
    }

    private static void appendUpdateStatus(StringBuilder target, String label, String status) {
        if (!status.isEmpty()) target.append(label).append(" · ").append(status).append('\n');
    }

    private void checkDetails() {
        if (detailThread != null || !MarketNetwork.allowed()) return;
        showDetail.setEnabled(false);
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
            boolean cancelled = Thread.currentThread().isInterrupted();
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                detailThread = null;
                if (!cancelled && MarketNetwork.allowed()) detail.setText(result);
                render();
            });
        }, "jpx-daily-detail");
        detailThread.start();
    }

    private void showNotificationHistory() {
        var dialog = new AlertDialog.Builder(this).setTitle("通知履歴").setNegativeButton("閉じる", null);
        try {
            var entries = NotificationHistory.recent(NotificationHistory.file(this), System.currentTimeMillis());
            if (entries.isEmpty()) {
                dialog.setMessage("過去" + NotificationHistory.DAYS + "日間の通知はまだない").show();
                return;
            }
            var clock = DateTimeFormatter.ofPattern("M月d日 HH:mm", Locale.JAPAN)
                    .withZone(ZoneId.of("Asia/Tokyo"));
            var labels = new String[entries.size()];
            for (int i = 0; i < entries.size(); i++) {
                var entry = entries.get(i);
                labels[i] = clock.format(Instant.ofEpochMilli(entry.postedAt())) + "\n" + entry.title();
            }
            dialog.setItems(labels, (list, index) -> new AlertDialog.Builder(this)
                    .setTitle(entries.get(index).title())
                    .setMessage(clock.format(Instant.ofEpochMilli(entries.get(index).postedAt())) + " JST\n\n"
                            + entries.get(index).detail())
                    .setNeutralButton("履歴に戻る", (detailDialog, which) -> showNotificationHistory())
                    .setPositiveButton("閉じる", null).show()).show();
        } catch (IOException unavailable) {
            dialog.setMessage("通知履歴を読み込めなかった").show();
        }
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

    private Switch optionSwitch(LinearLayout parent, String title, boolean checked) {
        var view = new Switch(this);
        view.setText(title);
        view.setTextSize(15);
        view.setTextColor(INK);
        view.setMinHeight(dp(48));
        view.setShowText(false);
        view.setThumbTintList(new ColorStateList(
                new int[][] {new int[] {android.R.attr.state_checked}, new int[] {}},
                new int[] {FOREST, MUTED}));
        view.setTrackTintList(new ColorStateList(
                new int[][] {new int[] {android.R.attr.state_checked}, new int[] {}},
                new int[] {ACCENT, OUTLINE}));
        view.setChecked(checked);
        place(parent, view, 5);
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
