package jp.valuehunter.privatewatch;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import androidx.work.Constraints;
import androidx.work.ListenableWorker;
import androidx.work.NetworkType;

import java.io.FilterInputStream;
import java.io.FilterOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.Executors;

import javax.net.ssl.HttpsURLConnection;

/** Controls the lifetime of all connections used by market data requests. */
final class MarketNetwork {
    private static final String PREFERENCES = "market-network";
    static final String ALLOWED = "market_network_allowed";
    static final String WIFI_ONLY = "market_wifi_only";
    static final String NOTICE = "data_usage_notice";
    private static final int NOTICE_VERSION = 1;
    private static final Gate GATE = new Gate();

    private static final Set<Runnable> LISTENERS = new CopyOnWriteArraySet<>();
    private static volatile boolean requested = true;
    private static volatile boolean wifiOnly;
    private static ConnectivityManager connectivity;
    private static Context application;
    private static Handler events;

    private MarketNetwork() {}

    static synchronized void initialize(Context context) {
        var settings = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
        connectivity = context.getSystemService(ConnectivityManager.class);
        wifiOnly = settings.getBoolean(WIFI_ONLY, false);
        requested = atStartup(settings.getInt(NOTICE, 0), settings.getBoolean(ALLOWED, false));
        refreshRoute(false);
    }

    static synchronized void startTracking(Context context) {
        if (events != null) return;
        application = context;
        events = new Handler(Looper.getMainLooper());
        if (connectivity == null) return;
        try {
            connectivity.registerDefaultNetworkCallback(new ConnectivityManager.NetworkCallback() {
                @Override public void onAvailable(Network network) {
                    events.post(() -> refreshRoute(true));
                }

                @Override public void onLost(Network network) {
                    events.post(() -> refreshRoute(true));
                }

                @Override public void onCapabilitiesChanged(Network network, NetworkCapabilities capabilities) {
                    events.post(() -> refreshRoute(true));
                }
            });
        } catch (SecurityException unavailable) {
            android.util.Log.w("MarketNetwork", "Cannot observe network changes", unavailable);
        }
    }

    static void addListener(Runnable listener) {
        LISTENERS.add(listener);
    }

    static void removeListener(Runnable listener) {
        LISTENERS.remove(listener);
    }

    static boolean atStartup(int noticeVersion, boolean allowed) {
        return noticeVersion >= NOTICE_VERSION && allowed;
    }

    static boolean noticeRequired(Context context) {
        return context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
                .getInt(NOTICE, 0) < NOTICE_VERSION;
    }

    static boolean allowed() {
        return GATE.allowed();
    }

    static boolean requested() {
        return requested;
    }

    static boolean wifiOnly() {
        return wifiOnly;
    }

    static boolean waitingForWifi() {
        return requested && wifiOnly && !allowed();
    }

    static ListenableWorker.Result pausedWork() {
        // Leave interrupted acquisitions pending even when the app process is killed before Wi-Fi returns.
        return waitingForWifi() ? ListenableWorker.Result.retry() : ListenableWorker.Result.success();
    }

    static synchronized boolean setAllowed(Context context, boolean allowed) {
        if (!allowed) {
            requested = false;
            refreshRoute(false);
        }
        boolean saved = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE).edit()
                .putBoolean(ALLOWED, allowed).putInt(NOTICE, NOTICE_VERSION).commit();
        if (allowed && saved) {
            requested = true;
            refreshRoute(false);
        }
        return saved;
    }

    static synchronized boolean setWifiOnly(Context context, boolean enabled) {
        if (enabled) {
            wifiOnly = true;
            refreshRoute(false);
        }
        boolean saved = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE).edit()
                .putBoolean(WIFI_ONLY, enabled).commit();
        if (!enabled && saved) {
            wifiOnly = false;
            refreshRoute(false);
        }
        return saved;
    }

    static Constraints constraints(NetworkType base) {
        var builder = new Constraints.Builder().setRequiredNetworkType(base);
        if (wifiOnly && Build.VERSION.SDK_INT >= 28) {
            var request = new NetworkRequest.Builder()
                    .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
            if (base == NetworkType.UNMETERED) {
                request.addCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED);
            }
            builder.setRequiredNetworkRequest(request.build(), base);
        }
        return builder.build();
    }

    private static Network activeWifi() {
        if (connectivity == null) return null;
        try {
            var network = connectivity.getActiveNetwork();
            if (network == null) return null;
            var caps = connectivity.getNetworkCapabilities(network);
            if (caps != null && wifiRoute(caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI),
                    caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR),
                    caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN),
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET))) return network;
        } catch (SecurityException unavailable) {
            // An unidentified route must never be used in Wi-Fi-only mode.
        }
        return null;
    }

    static boolean wifiRoute(boolean wifi, boolean cellular, boolean vpn, boolean internet) {
        return wifi && !cellular && !vpn && internet;
    }

    private static synchronized void refreshRoute(boolean notify) {
        boolean wasAllowed = GATE.allowed();
        Network route = requested && wifiOnly ? activeWifi() : null;
        boolean allowed = requested && (!wifiOnly || route != null);
        for (var connection : GATE.setRoute(allowed, route)) {
            // A provider's disconnect can block. Do not make the switch wait on socket I/O.
            ExecutorsHolder.ABORT.execute(() -> {
                try {
                    connection.disconnect();
                } catch (RuntimeException unavailable) {
                    android.util.Log.w("MarketNetwork", "Could not close a market data connection", unavailable);
                }
            });
        }
        if (!notify || events == null || wasAllowed == allowed) return;
        events.post(() -> {
            LISTENERS.forEach(Runnable::run);
            if (allowed && wifiOnly && allowed()) {
                JpxWatchWorker.checkNow(application);
                UsDailyWorker.checkNow(application);
            }
        });
    }

    private static final class ExecutorsHolder {
        private static final java.util.concurrent.Executor ABORT = Executors.newCachedThreadPool(runnable -> {
            var thread = new Thread(runnable, "market-network-stop");
            thread.setDaemon(true);
            return thread;
        });
    }

    static synchronized HttpsURLConnection open(URL address) throws IOException {
        if (wifiOnly) refreshRoute(true);
        return GATE.open(address);
    }

    static int response(HttpsURLConnection connection) throws IOException {
        GATE.requireActive(connection);
        return connection.getResponseCode();
    }

    static String header(HttpsURLConnection connection, String field) throws IOException {
        GATE.requireActive(connection);
        return connection.getHeaderField(field);
    }

    static Map<String, List<String>> headers(HttpsURLConnection connection) throws IOException {
        GATE.requireActive(connection);
        return connection.getHeaderFields();
    }

    static long contentLength(HttpsURLConnection connection) throws IOException {
        GATE.requireActive(connection);
        return connection.getContentLengthLong();
    }

    static InputStream input(HttpsURLConnection connection) throws IOException {
        GATE.requireActive(connection);
        return new FilterInputStream(connection.getInputStream()) {
            @Override public int read() throws IOException {
                GATE.requireActive(connection);
                return in.read();
            }

            @Override public int read(byte[] buffer, int offset, int length) throws IOException {
                GATE.requireActive(connection);
                return in.read(buffer, offset, length);
            }
        };
    }

    static OutputStream output(HttpsURLConnection connection) throws IOException {
        GATE.requireActive(connection);
        return new FilterOutputStream(connection.getOutputStream()) {
            @Override public void write(int value) throws IOException {
                GATE.requireActive(connection);
                out.write(value);
            }

            @Override public void write(byte[] buffer, int offset, int length) throws IOException {
                GATE.requireActive(connection);
                out.write(buffer, offset, length);
            }
        };
    }

    static void close(HttpsURLConnection connection) {
        GATE.close(connection);
    }

    static final class Gate {
        private final Set<HttpsURLConnection> connections = Collections.newSetFromMap(new IdentityHashMap<>());
        private boolean allowed = true;
        private Network route;

        synchronized boolean allowed() {
            return allowed;
        }

        List<HttpsURLConnection> setAllowed(boolean enabled) {
            return setRoute(enabled, null);
        }

        synchronized List<HttpsURLConnection> setRoute(boolean enabled, Network wifi) {
            boolean changed = !Objects.equals(route, wifi);
            route = wifi;
            allowed = enabled;
            if ((enabled && !changed) || connections.isEmpty()) return Collections.emptyList();
            var stopped = new ArrayList<>(connections);
            connections.clear();
            return stopped;
        }

        synchronized HttpsURLConnection open(URL address) throws IOException {
            if (!allowed || Thread.currentThread().isInterrupted()) throw new IOException("Market data communication stopped");
            var connection = (HttpsURLConnection) (route == null ? address.openConnection() : route.openConnection(address));
            connections.add(connection);
            return connection;
        }

        synchronized void requireActive(HttpsURLConnection connection) throws IOException {
            if (!allowed || !connections.contains(connection) || Thread.currentThread().isInterrupted()) {
                throw new IOException("Market data communication stopped");
            }
        }

        void close(HttpsURLConnection connection) {
            boolean wasTracked;
            synchronized (this) {
                wasTracked = connections.remove(connection);
            }
            if (wasTracked) connection.disconnect();
        }
    }
}
