package jp.valuehunter.privatewatch;

import android.app.Application;
import android.content.Context;

public final class MarketWatchApplication extends Application {
    @Override protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
        MarketNetwork.initialize(base);
    }

    @Override public void onCreate() {
        super.onCreate();
        var previous = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, crash) -> {
            try {
                DiagnosticLog.recordError(this, DiagnosticLog.Area.ALERT,
                        "未処理のクラッシュ · " + thread.getName(), crash);
            } catch (RuntimeException ignored) {}
            if (previous != null) previous.uncaughtException(thread, crash);
            else android.os.Process.killProcess(android.os.Process.myPid());
        });
        MarketNetwork.startTracking(this);
        DiagnosticLog.record(this, DiagnosticLog.Area.NETWORK, "アプリ起動 · " + DiagnosticLog.route());
    }
}
