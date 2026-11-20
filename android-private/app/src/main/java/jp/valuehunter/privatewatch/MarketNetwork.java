package jp.valuehunter.privatewatch;

import android.content.Context;

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
import java.util.Set;
import java.util.concurrent.Executors;

import javax.net.ssl.HttpsURLConnection;

/** Controls the lifetime of all connections used by market data requests. */
final class MarketNetwork {
    static final String ALLOWED = "market_network_allowed";
    private static final Gate GATE = new Gate();

    private MarketNetwork() {}

    static void initialize(Context context) {
        GATE.setAllowed(context.getSharedPreferences("market-network", Context.MODE_PRIVATE).getBoolean(ALLOWED, true));
    }

    static boolean allowed() {
        return GATE.allowed();
    }

    static boolean setAllowed(Context context, boolean allowed) {
        var active = GATE.setAllowed(allowed);
        for (var connection : active) {
            // A provider's disconnect can block. Do not make the switch wait on socket I/O.
            ExecutorsHolder.ABORT.execute(() -> {
                try {
                    connection.disconnect();
                } catch (RuntimeException unavailable) {
                    android.util.Log.w("MarketNetwork", "Could not close a market data connection", unavailable);
                }
            });
        }
        return context.getSharedPreferences("market-network", Context.MODE_PRIVATE)
                .edit().putBoolean(ALLOWED, allowed).commit();
    }

    private static final class ExecutorsHolder {
        private static final java.util.concurrent.Executor ABORT = Executors.newCachedThreadPool(runnable -> {
            var thread = new Thread(runnable, "market-network-stop");
            thread.setDaemon(true);
            return thread;
        });
    }

    static HttpsURLConnection open(URL address) throws IOException {
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

        synchronized boolean allowed() {
            return allowed;
        }

        synchronized List<HttpsURLConnection> setAllowed(boolean enabled) {
            allowed = enabled;
            if (enabled || connections.isEmpty()) return Collections.emptyList();
            var stopped = new ArrayList<>(connections);
            connections.clear();
            return stopped;
        }

        synchronized HttpsURLConnection open(URL address) throws IOException {
            if (!allowed || Thread.currentThread().isInterrupted()) throw new IOException("Market data communication stopped");
            var connection = (HttpsURLConnection) address.openConnection();
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
