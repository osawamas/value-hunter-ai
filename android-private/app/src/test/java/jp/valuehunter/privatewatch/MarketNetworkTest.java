package jp.valuehunter.privatewatch;

import org.junit.Test;

import java.io.IOException;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLStreamHandler;
import java.security.cert.Certificate;
import java.util.List;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import javax.net.ssl.HttpsURLConnection;

import static org.junit.Assert.*;

public class MarketNetworkTest {
    private static final class Connection extends HttpsURLConnection {
        int closes;

        Connection(URL address) { super(address); }

        @Override public void connect() {}
        @Override public boolean usingProxy() { return false; }
        @Override public void disconnect() { closes++; }
        @Override public String getCipherSuite() { return ""; }
        @Override public Certificate[] getLocalCertificates() { return null; }
        @Override public Certificate[] getServerCertificates() { return null; }
    }

    private static URL example(AtomicInteger opened) throws IOException {
        return new URL(null, "https://market.invalid/", new URLStreamHandler() {
            @Override protected URLConnection openConnection(URL address) {
                opened.incrementAndGet();
                return new Connection(address);
            }
        });
    }

    @Test public void wifiOnlyRejectsCellularAmbiguousAndUnidentifiedRoutes() {
        assertTrue(MarketNetwork.wifiRoute(true, false, false, true));
        assertFalse(MarketNetwork.wifiRoute(false, true, false, true));
        assertFalse(MarketNetwork.wifiRoute(true, true, false, true));
        assertFalse(MarketNetwork.wifiRoute(true, false, true, true));
        assertFalse(MarketNetwork.wifiRoute(true, false, false, false));
        assertFalse(MarketNetwork.wifiRoute(false, false, false, true));
    }

    @Test public void disabledWifiRadioRejectsStaleWifiCapabilities() {
        assertFalse(MarketNetwork.radioWifiRoute(false, true, false, false, true));
        assertTrue(MarketNetwork.radioWifiRoute(true, true, false, false, true));
        assertFalse(MarketNetwork.radioWifiRoute(true, false, true, false, true));
        assertFalse(MarketNetwork.radioWifiRoute(true, true, false, true, true));
    }

    @Test public void appStartupRequiresAReviewedNoticeAndAnExplicitOnSetting() {
        assertFalse(MarketNetwork.atStartup(0, false));
        assertFalse(MarketNetwork.atStartup(0, true));
        assertFalse(MarketNetwork.atStartup(1, false));
        assertTrue(MarketNetwork.atStartup(1, true));
    }

    @Test public void disablePreventsNewRequestsAndInvalidatesOldConnectionsAfterResume() throws Exception {
        var gate = new MarketNetwork.Gate();
        var opened = new AtomicInteger();
        var address = example(opened);
        var inFlight = gate.open(address);
        gate.requireActive(inFlight);
        var stopping = gate.setAllowed(false);
        assertEquals(List.of(inFlight), stopping);
        assertFalse(gate.allowed());
        assertThrows(IOException.class, () -> gate.open(address));
        assertThrows(IOException.class, () -> gate.requireActive(inFlight));
        assertEquals(1, opened.get());
        stopping.forEach(HttpsURLConnection::disconnect);

        gate.setAllowed(true);
        assertThrows(IOException.class, () -> gate.requireActive(inFlight));
        var resumed = gate.open(address);
        gate.requireActive(resumed);
        gate.close(resumed);
        gate.close(inFlight);
        assertEquals(1, ((Connection) inFlight).closes);
        assertEquals(1, ((Connection) resumed).closes);
        assertEquals(2, opened.get());
    }

    @Test public void interruptedWorkDoesNotCreateANewConnection() throws Exception {
        var gate = new MarketNetwork.Gate();
        var opened = new AtomicInteger();
        var address = example(opened);
        var work = new FutureTask<>(() -> {
            Thread.currentThread().interrupt();
            assertThrows(IOException.class, () -> gate.open(address));
            return Thread.currentThread().isInterrupted();
        });
        new Thread(work, "canceled-market-test").start();
        assertTrue(work.get(5, TimeUnit.SECONDS));
        assertEquals(0, opened.get());
    }
}
