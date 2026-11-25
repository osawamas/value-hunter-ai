package jp.valuehunter.privatewatch;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
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
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final String METER_DRAFT = "valueMeterDraft";
    private static final String PAUSED = "public_jpx_watch_paused";
    private static final int PAGE = 0xfffffbf6;
    private static final int SURFACE = 0xffffffff;
    private static final int FOREST = 0xff091b2e;
    private static final int INK = 0xff142336;
    private static final int MUTED = 0xff536071;
    private static final int LIGHT_TEXT = 0xffffe3ca;
    private static final int ACCENT = 0xffd79b72;
    private static final int OUTLINE = 0xffdac8ba;

    private ScrollView rootScroll;
    private View notificationSection;
    private View usSection;
    private SharedPreferences state;
    private Switch monitorSwitch;
    private TextView monitorStatus;
    private TextView notificationStatus;
    private TextView communicationStatus;
    private Switch networkSwitch;
    private Switch wifiSwitch;
    private AlertDialog communicationNotice;
    private AlertDialog valueMeterDialog;
    private ValueAlertMeter.Thresholds valueMeterDraft;
    private TextView lastCheck;
    private TextView detail;
    private TextView usDailyStatus;
    private Button notificationButton;
    private Button testNotificationButton;
    private boolean notificationTestPending;
    private boolean notificationWasBlocked;
    private Button checkNow;
    private Button showDetail;
    private Button jpxCoverageButton;
    private Button usCoverageButton;
    private TextView jpxCoverage;
    private TextView usCoverage;
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
        content.setPadding(0, 0, 0, dp(24));
        int availableWidth = getResources().getConfiguration().screenWidthDp;
        int contentWidth = availableWidth > 620 ? dp(620) : ScrollView.LayoutParams.MATCH_PARENT;
        scroll.addView(content, new ScrollView.LayoutParams(contentWidth,
                ScrollView.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.CENTER_HORIZONTAL));
        rootScroll=scroll;
        LinearLayout shell=new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setBackgroundColor(PAGE);
        shell.addView(scroll,new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,0,1f));
        shell.addView(BrandNav.create(this,"ホーム"),new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,LinearLayout.LayoutParams.WRAP_CONTENT));
        setContentView(shell);

        content.addView(BrandHeader.create(this),new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,LinearLayout.LayoutParams.WRAP_CONTENT));
        var hero = section(content, FOREST, false);
        hero.setBackgroundColor(FOREST);
        monitorStatus = label(hero, "", 15, ACCENT, true, 10);
        label(hero, "新しく条件に入った銘柄を無音で通知", 13, LIGHT_TEXT, false, 5);

        var communication = section(content, SURFACE, true);
        networkSwitch = optionSwitch(communication, "相場データの通信", MarketNetwork.requested());
        wifiSwitch = optionSwitch(communication, "Wi-Fi接続時のみ更新", MarketNetwork.wifiOnly());
        communicationStatus = label(communication, "", 13, MUTED, false, 5);
        networkSwitch.setOnClickListener(view -> applyMarketNetworkPreference(networkSwitch.isChecked()));
        wifiSwitch.setOnClickListener(view -> {
            communicationPreferenceSaved = MarketNetwork.setWifiOnly(this, wifiSwitch.isChecked());
            DiagnosticLog.record(this, DiagnosticLog.Area.NETWORK,
                    "Wi-Fi限定の設定" + (communicationPreferenceSaved ? "を変更" : "を保存できず")
                            + " · " + DiagnosticLog.route());
            // Replace saved jobs so their network constraint matches the selected mode.
            androidx.work.WorkManager.getInstance(this).cancelAllWork();
            scheduleMarketChecks();
            render();
        });
        button(communication, "SEC財務取得用の連絡先メールを設定", PAGE, 5)
                .setOnClickListener(view -> showSecContactSettings());
        label(communication, SecAccess.validEmail(SecAccess.contact(this))
                ? "SEC連絡先: 設定済み" : "SEC連絡先: 未設定（米国株財務の取得には設定が必要）",
                13, MUTED, false, 5);
        button(communication, "通信量について", PAGE, 5).setOnClickListener(view -> showCommunicationNotice(false));

        var notifications = section(content, SURFACE, true);
        notificationSection=notifications;
        label(notifications, "通知", 19, INK, true, 0);
        var notificationSwitch = optionSwitch(notifications, "無音通知", ScanWorker.notificationsRequested(this));
        notificationSwitch.setOnCheckedChangeListener((view, checked) -> {
            ScanWorker.setNotificationsRequested(state, checked);
            DiagnosticLog.record(this, DiagnosticLog.Area.ALERT, checked ? "設定で通知オン" : "設定で通知オフ");
        });
        var wakeScreen = optionSwitch(notifications, "通知時に画面を点灯",
                state.getBoolean(NotificationScreenWake.ENABLED, true));
        wakeScreen.setOnCheckedChangeListener((view, checked) -> {
            state.edit().putBoolean(NotificationScreenWake.ENABLED, checked).apply();
            DiagnosticLog.record(this, DiagnosticLog.Area.WAKE, checked ? "設定で点灯オン" : "設定で点灯オフ");
        });
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
        button(notifications, "当日＋過去3日の通知銘柄一覧", PAGE, 5)
                .setOnClickListener(view -> startActivity(new Intent(this, RecentAlertsActivity.class)));
        button(notifications, "通知履歴（" + NotificationHistory.DAYS + "日間）", PAGE, 5)
                .setOnClickListener(view -> showNotificationHistory());
        button(notifications, "米国株の通知成績（試験）", PAGE, 5)
                .setOnClickListener(view -> showAlertOutcomes(AlertOutcomes.Market.US));
        button(notifications, "東証株の通知成績（試験）", PAGE, 5)
                .setOnClickListener(view -> showAlertOutcomes(AlertOutcomes.Market.JPX));
        var useMeter = optionSwitch(notifications, "割安メーターで通知", state.getBoolean(ValueAlertPreview.LIVE, true));
        useMeter.setOnCheckedChangeListener((view, checked) -> {
            state.edit().putBoolean(ValueAlertPreview.LIVE, checked)
                    .putLong(ScanWorker.FINANCIAL_ALERT_GENERATION,
                            state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0) + 1).apply();
            DiagnosticLog.record(this, DiagnosticLog.Area.ALERT, checked ? "割安メーター通知オン" : "割安メーター通知オフ");
        });
        label(notifications, "オンで新規入り・昇格を3段階で通知。比較資料のある銘柄が対象。", 13, MUTED, false, 5);
        button(notifications, "割安アラートの境界", PAGE, 5)
                .setOnClickListener(view -> showValueAlertMeter());
        button(notifications, "デバッグ診断・エラー一覧", PAGE, 5)
                .setOnClickListener(view -> startActivity(new Intent(this, DebugDiagnosticsActivity.class)));

        button(notifications, "現在の米国株・割安候補一覧（通知なしでも確認）", PAGE, 5)
                .setOnClickListener(view -> startActivity(new Intent(this, CurrentCandidatesActivity.class)));

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
        usSection=unitedStates;
        label(unitedStates, "米国株  ·  NYSE / Nasdaq", 17, INK, true, 0);
        usCoverage = label(unitedStates, "", 13, MUTED, false, 5);
        usCoverageButton = button(unitedStates, "米国株の未判定の内訳", PAGE, 4);
        usCoverageButton.setOnClickListener(view -> showCoverage(MarketCoverage.US, "米国株"));
        button(unitedStates, "参考予算候補一覧（銘柄・購入額）", PAGE, 4)
                .setOnClickListener(view -> showUsBudgetCandidates());
        usDailyStatus = label(unitedStates, "", 13, MUTED, false, 4);

        var singapore = section(content, SURFACE, true);
        label(singapore, "シンガポール株  ·  SGX", 17, INK, true, 0);
        label(singapore, "終値の自動監視は準備中", 13, MUTED, false, 4);

        var result = section(content, SURFACE, true);
        label(result, "最新の確認", 19, INK, true, 0);
        jpxCoverage = label(result, "", 13, MUTED, false, 5);
        jpxCoverageButton = button(result, "東証の未判定の内訳", PAGE, 4);
        jpxCoverageButton.setOnClickListener(view -> showCoverage(MarketCoverage.JPX, "東証"));
        lastCheck = label(result, "", 14, MUTED, false, 5);
        showDetail = button(result, "終値と判定の詳細", PAGE, 10);
        detail = label(result, "", 14, INK, false, 8);
        detail.setTextIsSelectable(true);
        detail.setMovementMethod(LinkMovementMethod.getInstance());
        detail.setVisibility(View.GONE);
        showDetail.setOnClickListener(view -> checkDetails());

        render();
        scrollToFocus(getIntent().getStringExtra("focus"));
        String draft = saved == null ? null : saved.getString(METER_DRAFT);
        if (draft != null && !MarketNetwork.noticeRequired(this)) {
            showValueAlertMeter(ValueAlertMeter.Thresholds.read(draft));
        }
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        if (valueMeterDialog != null && valueMeterDialog.isShowing() && valueMeterDraft != null) {
            out.putString(METER_DRAFT, valueMeterDraft.encode());
        }
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        scrollToFocus(intent.getStringExtra("focus"));
    }
    private void scrollToFocus(String focus) {
        if(rootScroll==null || focus==null)return;
        View target="us".equals(focus)?usSection:"notifications".equals(focus)?notificationSection:null;
        rootScroll.post(()->rootScroll.smoothScrollTo(0,target==null?0:target.getTop()));
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
        DiagnosticLog.record(this, DiagnosticLog.Area.NETWORK,
                "相場通信の設定" + (communicationPreferenceSaved ? "を変更" : "を保存できず")
                        + " · " + DiagnosticLog.route());
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

    private void showSecContactSettings() {
        var field = new EditText(this);
        field.setSingleLine(true);
        field.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        field.setText(SecAccess.contact(this));
        field.setHint("contact@example.com");
        var dialog = new AlertDialog.Builder(this)
                .setTitle("SEC自動取得の連絡先")
                .setMessage("米国SECの公式データ取得には、利用者の連絡先メールが必要。設定したメールはSEC宛の通信ヘッダーだけに送信される。端末内に保存し、診断ログには表示しない。")
                .setView(field)
                .setNegativeButton("キャンセル", null)
                .setPositiveButton("保存して再取得", (d, button) -> {
                    var address = field.getText().toString().trim();
                    if (!SecAccess.validEmail(address)) {
                        Toast.makeText(this, "メールアドレスの形式を確認して", Toast.LENGTH_LONG).show();
                        return;
                    }
                    if (!state.edit().putString(SecAccess.CONTACT_KEY, address).commit()) {
                        Toast.makeText(this, "SEC連絡先を保存できなかった", Toast.LENGTH_LONG).show();
                        return;
                    }
                    DiagnosticLog.record(this, DiagnosticLog.Area.US_FINANCE, "SEC連絡先を端末に設定");
                    if (MarketNetwork.requested()) UsSecFinanceWorker.contactUpdated(this);
                    Toast.makeText(this, "保存した。米国株財務の再取得を予約", Toast.LENGTH_SHORT).show();
                    recreate();
                })
                .create();
        dialog.show();
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
        UsListingArchiveWorker.schedule(this);
        if (monitorSwitch.isChecked() || JpxWatchWorker.enabled(this)) {
            JpxWatchWorker.setEnabled(this, monitorSwitch.isChecked());
        }
    }

    @Override protected void onResume() {
        super.onResume();
        resumePendingAlerts();
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
        if (valueMeterDialog != null) valueMeterDialog.dismiss();
        testNotificationButton.removeCallbacks(sendTestNotification);
        super.onDestroy();
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 1) resumePendingAlerts();
        render();
    }

    private void resumePendingAlerts() {
        boolean blocked = !ScanWorker.systemAllowsAlerts(this);
        if (notificationWasBlocked && !blocked && ScanWorker.notificationsRequested(this) && MarketNetwork.allowed()) {
            JpxWatchWorker.checkNow(this);
            if (UsDailyWorker.hasPendingFinancialAlert(state)) UsSecFinanceWorker.ensureScheduled(this);
        }
        notificationWasBlocked = blocked;
    }

    private void render() {
        jpxCoverage.setText(MarketCoverage.JPX.summary(state));
        usCoverage.setText(MarketCoverage.US.summary(state));
        jpxCoverageButton.setEnabled(MarketCoverage.JPX.available(state));
        usCoverageButton.setEnabled(MarketCoverage.US.available(state));
        var usStatus = new StringBuilder(UsListingArchiveWorker.displayStatus(state, java.time.Instant.now()))
                .append('\n');
        appendUpdateStatus(usStatus, "終値", MarketUpdate.US_CLOSE.display(state));
        appendUpdateStatus(usStatus, "財務", MarketUpdate.US_FINANCE.display(state));
        usDailyStatus.setText(usStatus.append(UsDailyWorker.displayStatus(this, state)));
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
        if (active) report = JpxWatchWorker.displayFreshness(state) + (report.isEmpty() ? "" : "\n" + report);
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
                DiagnosticLog.recordError(this, DiagnosticLog.Area.JPX, "東証詳細 · 日報の取得", error);
                message = "東証日報の確認に失敗（診断ログに詳細を保存）";
            } catch (RuntimeException error) {
                DiagnosticLog.recordError(this, DiagnosticLog.Area.JPX, "東証詳細 · 解析", error);
                message = "東証日報のPDFを読み取れなかった（診断ログに詳細を保存）";
            } catch (LinkageError error) {
                // On Android 9 a library can call an API absent on the device.
                // Preserve the failing method in the on-device stack instead of
                // crashing the process from the detail worker thread.
                DiagnosticLog.recordError(this, DiagnosticLog.Area.JPX, "東証詳細 · Android互換性", error);
                message = "東証詳細の互換性エラー（診断ログに詳細を保存）";
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

    private void showUsBudgetCandidates() {
        var day = state.getString(UsSecFinanceWorker.BUDGET_RESULTS_DAY, "");
        var json = state.getString(UsSecFinanceWorker.BUDGET_RESULTS, "");
        var dialog = new AlertDialog.Builder(this).setTitle("米国株 · 参考予算候補一覧");
        if (day.isEmpty() || json.isEmpty()) {
            dialog.setMessage("このビルドで保存した候補一覧はまだない。次の財務・予算判定で自動保存される。\n"
                    + "以前の判定は米国株欄の「予算入り」で確認できる。")
                    .setPositiveButton("閉じる", null).show();
            return;
        }
        try {
            var values = new org.json.JSONArray(json);
            var detail = new StringBuilder("取引日 " + day + "（米東部）\n"
                    + "100株購入額・円換算・手数料別。株価による参考判定で、財務的な割安評価ではない。\n");
            if (values.length() == 0) detail.append("\n候補なし");
            for (int i = 0; i < values.length(); i++) {
                var row = values.getJSONObject(i);
                detail.append("\n").append(row.getString("code"))
                        .append("  ·  ").append(row.getString("yen"))
                        .append("円 / 100株\n    ").append(row.getString("source"));
            }
            dialog.setMessage(detail.toString()).setPositiveButton("閉じる", null).show();
        } catch (org.json.JSONException invalid) {
            dialog.setMessage("保存した候補一覧を読み取れなかった。診断ログを確認して。")
                    .setPositiveButton("閉じる", null).show();
        }
    }

    private void showCoverage(MarketCoverage market, String name) {
        var summary = market.summary(state);
        var dialog = new AlertDialog.Builder(this).setTitle(name + "の未判定").setNegativeButton("閉じる", null);
        try {
            var groups = market.groups(state);
            var reasons = java.util.Arrays.stream(MarketCoverage.Reason.values()).filter(groups::containsKey).toList();
            if (reasons.isEmpty()) {
                dialog.setMessage(summary + "\n\n未判定の銘柄なし").show();
                return;
            }
            var labels = reasons.stream().map(reason -> reason.label + " · " + groups.get(reason).size() + "銘柄")
                    .toArray(String[]::new);
            // Keep the cohort date and the counts visible while the user picks a reason.
            dialog.setTitle(name + "の未判定\n" + summary.split("\n", 2)[0]);
            dialog.setItems(labels, (list, index) -> {
                var reason = reasons.get(index);
                new AlertDialog.Builder(this).setTitle(reason.label + " · " + groups.get(reason).size() + "銘柄")
                        .setItems(groups.get(reason).toArray(String[]::new), null)
                        .setNeutralButton("内訳に戻る", (detail, which) -> showCoverage(market, name))
                        .setNegativeButton("閉じる", null).show();
            }).show();
        } catch (org.json.JSONException invalid) {
            dialog.setMessage("未判定の内訳を読み込めなかった").show();
        }
    }

    private void showValueAlertMeter() {
        showValueAlertMeter(ValueAlertMeter.Thresholds.read(state.getString(ValueAlertPreview.SETTINGS, "")));
    }

    private void showValueAlertMeter(ValueAlertMeter.Thresholds saved) {
        if (valueMeterDialog != null && valueMeterDialog.isShowing()) return;
        var jpx = ValueAlertPreview.history(state, ValueAlertPreview.Market.JPX);
        var us = ValueAlertPreview.history(state, ValueAlertPreview.Market.US);
        var scroll = new ScrollView(this);
        var controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.VERTICAL);
        controls.setPadding(dp(20), dp(8), dp(20), dp(12));
        scroll.addView(controls);
        label(controls, "0〜100点の境界を変更。下の件数は端末に保存された取引日の試算。", 14, INK, false, 0);
        label(controls, "利益の急減や資料不足があると段階を抑える。米国株はSECの利益・営業CFが確認できれば厳格なPER・PBR条件で超割安まで判定。", 13, MUTED, false, 5);
        var band = new LinearLayout(this);
        band.setOrientation(LinearLayout.HORIZONTAL);
        place(controls, band, 12);
        int[] colors = {OUTLINE, 0xffa2c59e, 0xff659c7d, FOREST};
        int[] values = {saved.first(), saved.second(), saved.third()};
        var captions = new TextView[3];
        var sliders = new SeekBar[3];
        for (int i = 0; i < values.length; i++) {
            captions[i] = label(controls, "", 14, INK, true, 10);
            sliders[i] = new SeekBar(this);
            sliders[i].setMin(1);
            sliders[i].setMax(100);
            sliders[i].setProgress(values[i]);
            sliders[i].setMinimumHeight(dp(44));
            place(controls, sliders[i], 0);
        }
        var preview = label(controls, "", 13, INK, false, 8);
        Runnable refresh = () -> {
            var thresholds = new ValueAlertMeter.Thresholds(values[0], values[1], values[2]);
            valueMeterDraft = thresholds;
            band.removeAllViews();
            int from = 0;
            for (int i = 0; i < colors.length; i++) {
                int to = i < values.length ? values[i] : 100;
                if (to > from) {
                    var color = new View(this);
                    color.setBackgroundColor(colors[i]);
                    band.addView(color, new LinearLayout.LayoutParams(0, dp(12), to - from));
                }
                from = to;
            }
            band.setContentDescription("割安度の境界 " + values[0] + "、" + values[1] + "、" + values[2] + " 点");
            for (int i = 0; i < values.length; i++) {
                String caption = ValueAlertMeter.LABELS.get(i + 1) + " · " + values[i] + "点以上";
                captions[i].setText(caption);
                sliders[i].setContentDescription("下限スライダー " + caption);
            }
            preview.setText("保存済みデータによる試算 · "
                    + (state.getBoolean(ValueAlertPreview.LIVE, true)
                    ? "通知は保存した境界で判定" : "割安メーター通知はオフ") + "\n\n"
                    + ValueAlertPreview.summary(ValueAlertPreview.Market.JPX, jpx, thresholds) + "\n\n"
                    + ValueAlertPreview.summary(ValueAlertPreview.Market.US, us, thresholds));
        };
        for (int i = 0; i < values.length; i++) {
            int index = i;
            sliders[i].setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
                @Override public void onProgressChanged(SeekBar bar, int value, boolean fromUser) {
                    if (!fromUser) return;
                    int min = index == 0 ? 1 : values[index - 1] + 1;
                    int max = index == 2 ? 100 : values[index + 1] - 1;
                    values[index] = Math.max(min, Math.min(max, value));
                    if (values[index] != value) bar.setProgress(values[index]);
                    refresh.run();
                }

                @Override public void onStartTrackingTouch(SeekBar bar) {}
                @Override public void onStopTrackingTouch(SeekBar bar) {}
            });
        }
        refresh.run();
        var dialog = new AlertDialog.Builder(this).setTitle("割安アラートの境界").setView(scroll)
                .setNeutralButton("初期値に戻す", null).setNegativeButton("キャンセル", null)
                .setPositiveButton("境界を保存", null).create();
        valueMeterDialog = dialog;
        dialog.setOnDismissListener(ignored -> {
            if (valueMeterDialog == dialog) {
                valueMeterDialog = null;
                valueMeterDraft = null;
            }
        });
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(view -> {
                var defaults = ValueAlertMeter.DEFAULT;
                values[0] = defaults.first();
                values[1] = defaults.second();
                values[2] = defaults.third();
                for (int i = 0; i < values.length; i++) sliders[i].setProgress(values[i]);
                refresh.run();
            });
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
                var thresholds = new ValueAlertMeter.Thresholds(values[0], values[1], values[2]);
                var edit = state.edit().putString(ValueAlertPreview.SETTINGS, thresholds.encode());
                if (state.getBoolean(ValueAlertPreview.LIVE, true)
                        && !thresholds.equals(ValueAlertMeter.Thresholds.read(state.getString(ValueAlertPreview.SETTINGS, "")))) {
                    edit.putLong(ScanWorker.FINANCIAL_ALERT_GENERATION,
                            state.getLong(ScanWorker.FINANCIAL_ALERT_GENERATION, 0) + 1);
                }
                if (edit.commit()) {
                    dialog.dismiss();
                } else {
                    Toast.makeText(this, "境界を保存できなかった", Toast.LENGTH_SHORT).show();
                }
            });
        });
        dialog.show();
    }

    private void showDiagnostics() {
        var report = DiagnosticLog.report(this);
        var scroll = new ScrollView(this);
        var text = new TextView(this);
        text.setPadding(dp(20), dp(10), dp(20), dp(12));
        text.setTextColor(INK);
        text.setTextSize(13);
        text.setTextIsSelectable(true);
        text.setText(report);
        scroll.addView(text);
        new AlertDialog.Builder(this).setTitle("診断ログ").setView(scroll)
                .setNegativeButton("閉じる", null)
                .setPositiveButton("診断ログをコピー", (dialog, which) -> {
                    var clipboard = getSystemService(ClipboardManager.class);
                    if (clipboard != null) {
                        clipboard.setPrimaryClip(ClipData.newPlainText(getString(R.string.app_name) + " 診断ログ", DiagnosticLog.report(this)));
                        Toast.makeText(this, "診断ログをコピーした", Toast.LENGTH_SHORT).show();
                    }
                }).show();
    }

    private void showAlertOutcomes(AlertOutcomes.Market market) {
        String report;
        try {
            report = AlertOutcomes.report(this, market);
        } catch (IOException | org.json.JSONException unavailable) {
            report = "試験記録を読み込めなかった";
        }
        var scroll = new ScrollView(this);
        var message = new TextView(this);
        message.setText(report);
        message.setTextColor(INK);
        message.setTextSize(14);
        message.setPadding(dp(22), dp(8), dp(22), dp(12));
        message.setTextIsSelectable(true);
        scroll.addView(message);
        new AlertDialog.Builder(this).setTitle(market.label + "の通知成績（試験）").setView(scroll)
                .setPositiveButton("閉じる", null).show();
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
        group.setPadding(dp(20), dp(19), dp(20), dp(19));
        group.setBackground(border ? shape(color, 17, true) : shape(color, 0, false));
        if (border) {
            var layout = new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,LinearLayout.LayoutParams.WRAP_CONTENT);
            layout.setMargins(dp(17),dp(12),dp(17),0);
            parent.addView(group,layout);
        } else {
            place(parent,group,0);
        }
        return group;
    }

    private TextView label(LinearLayout parent, String value, int size, int color, boolean bold, int margin) {
        var view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        if (bold) view.setTypeface(size >= 17 ? Typeface.create("serif", Typeface.BOLD) : Typeface.DEFAULT, Typeface.BOLD);
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
        view.setTextSize(15);
        view.setAllCaps(false);
        view.setTextColor(INK);
        view.setMinHeight(dp(54));
        view.setMinimumHeight(dp(54));
        view.setPadding(dp(12), dp(5), dp(12), dp(5));
        view.setBackgroundTintList(null);
        view.setBackground(new RippleDrawable(ColorStateList.valueOf(0x22173b33),
                shape(color, 19, color == PAGE), null));
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
