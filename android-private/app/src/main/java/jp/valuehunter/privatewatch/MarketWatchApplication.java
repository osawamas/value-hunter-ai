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
        MarketNetwork.startTracking(this);
        DiagnosticLog.record(this, DiagnosticLog.Area.NETWORK, "アプリ起動 · " + DiagnosticLog.route());
    }
}
