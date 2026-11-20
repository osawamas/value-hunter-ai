package jp.valuehunter.privatewatch;

import android.app.Application;
import android.content.Context;

public final class MarketWatchApplication extends Application {
    @Override protected void attachBaseContext(Context base) {
        super.attachBaseContext(base);
        MarketNetwork.initialize(base);
    }
}
